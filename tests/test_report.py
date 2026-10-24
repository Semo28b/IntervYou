import json
import unittest
from contextlib import nullcontext
from unittest.mock import Mock, call, patch

from google.genai import errors

from gemini_service import (
    GeminiServiceError,
    GeminiSettings,
    generate_interview_report,
)
from report import InvalidReportError, parse_report_response, render_report


def valid_report_data():
    return {
        "candidate_name": None,
        "overall_score": 7.5,
        "overall_reason": "The examples were relevant and clearly structured.",
        "question_scores": [
            {
                "question_number": number,
                "score": 6 + number / 10,
                "reason": f"Question {number} included a relevant example.",
            }
            for number in range(1, 7)
        ],
        "strengths": ["Used a clear project example."],
        "areas_to_improve": ["Explain individual contributions in more detail."],
        "cv_job_fit": {
            "strengths": ["The CV shows relevant project experience."],
            "gaps": ["The CV does not mention formal team leadership."],
            "clear_mismatch": False,
        },
        "cv_suggestions": [
            "Add measurable results.",
            "Highlight relevant project ownership.",
            "Include role-specific tools.",
        ],
    }


class ReportValidationTests(unittest.TestCase):
    def test_parses_complete_report_and_uses_candidate_fallback(self):
        report = parse_report_response(json.dumps(valid_report_data()))

        self.assertEqual(report.candidate_name, "Candidate")
        self.assertEqual(report.overall_score, 7.5)
        self.assertEqual(
            [item.question_number for item in report.question_scores],
            [1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(len(report.cv_suggestions), 3)

    def test_rejects_missing_question_score(self):
        data = valid_report_data()
        data["question_scores"].pop()

        with self.assertRaisesRegex(InvalidReportError, "exactly six"):
            parse_report_response(json.dumps(data))

    def test_rejects_duplicate_question_numbers(self):
        data = valid_report_data()
        data["question_scores"][5]["question_number"] = 5

        with self.assertRaisesRegex(InvalidReportError, "each main question"):
            parse_report_response(json.dumps(data))

    def test_rejects_out_of_range_scores(self):
        data = valid_report_data()
        data["overall_score"] = 10.1

        with self.assertRaisesRegex(InvalidReportError, "from 0 to 10"):
            parse_report_response(json.dumps(data))

    def test_rejects_wrong_number_of_cv_suggestions(self):
        data = valid_report_data()
        data["cv_suggestions"].pop()

        with self.assertRaisesRegex(InvalidReportError, "exactly three"):
            parse_report_response(json.dumps(data))


class ReportPresentationTests(unittest.TestCase):
    @patch("report.st.container", return_value=nullcontext())
    @patch("report.st.markdown")
    def test_arabic_report_uses_rtl_layout_and_arabic_labels(
        self, markdown, _container
    ):
        data = valid_report_data()
        data["cv_job_fit"]["clear_mismatch"] = True
        data["cv_suggestions"][0] = "<add measurable results>"
        report = parse_report_response(json.dumps(data))

        render_report(report, "CES - C++", language="ar")

        markup = markdown.call_args.args[0]
        self.assertIn('<div dir="rtl" style="text-align:right;">', markup)
        self.assertIn("\u2068CES - C++\u2069", markup)
        self.assertIn("المرشح", markup)
        self.assertIn("مدى توافق السيرة الذاتية مع الوظيفة", markup)
        self.assertIn("نقاط القوة ذات الصلة", markup)
        self.assertIn("اقتراحات لتحسين السيرة الذاتية", markup)
        self.assertIn("dir=\"rtl\"", markup)
        self.assertIn("السؤال 6 من 6", markup)
        self.assertIn("<ul dir=\"rtl\"", markup)
        self.assertIn("<ol dir=\"rtl\"", markup)
        self.assertIn("background:#FFF1C4", markup)
        self.assertIn("&lt;\u2068add measurable results\u2069&gt;", markup)
        self.assertNotIn("<add measurable results>", markup)

    @patch("report.st.container", return_value=nullcontext())
    @patch("report.st.markdown")
    def test_arabic_report_render_preserves_raw_glyphs(self, markdown, _container):
        data = valid_report_data()
        original_text = "خ▯ة عملية"
        data["strengths"] = [original_text]
        report = parse_report_response(json.dumps(data, ensure_ascii=False))

        render_report(report, "مهندس برمجيات", language="ar")

        self.assertIn(original_text, markdown.call_args.args[0])

    @patch("report.st.container", return_value=nullcontext())
    @patch("report.st.markdown")
    @patch("report.st.title")
    def test_english_report_keeps_existing_presentation(
        self, title, _markdown, _container
    ):
        report = parse_report_response(json.dumps(valid_report_data()))

        render_report(report, "Marketing Specialist")

        title.assert_called_once_with("Interview Report")


class ReportGenerationTests(unittest.TestCase):
    @patch("gemini_service.genai.Client")
    def test_uses_report_model_and_sends_context(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value.text = json.dumps(
            valid_report_data()
        )
        settings = GeminiSettings("test-key", "interview-model", "report-model")
        messages = [
            {"role": "assistant", "text": "Tell me about your project."},
            {"role": "user", "text": "I led a useful project."},
        ]

        report = generate_interview_report(
            settings,
            "Test CV with project experience.",
            "Marketing Specialist",
            messages,
        )

        self.assertEqual(report.candidate_name, "Candidate")
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "report-model")
        score_schema = request["config"].response_schema.properties["question_scores"]
        self.assertEqual(score_schema.min_items, 6)
        self.assertEqual(score_schema.max_items, 6)
        self.assertIn("exactly six scores, numbered 1 through 6", request["contents"])
        self.assertIn("first CV detail", request["contents"])
        self.assertIn("career direction", request["contents"])
        self.assertEqual(len(report.question_scores), 6)
        self.assertEqual(
            request["config"].response_mime_type,
            "application/json",
        )
        self.assertIn("Test CV with project experience.", request["contents"])
        self.assertIn("I led a useful project.", request["contents"])

    @patch("gemini_service.time.sleep")
    @patch("gemini_service.genai.Client")
    def test_retries_report_request_after_temporary_outage(
        self, client_class, sleep
    ):
        client = client_class.return_value
        client.models.generate_content.side_effect = [
            errors.ServerError(
                code=503,
                response_json={"error": {"message": "Service unavailable"}},
            ),
            Mock(text=json.dumps(valid_report_data())),
        ]
        settings = GeminiSettings("test-key", "interview-model", "report-model")

        report = generate_interview_report(
            settings,
            "Test CV",
            "Marketing Specialist",
            [{"role": "user", "text": "I led a useful project."}],
        )

        self.assertEqual(report.candidate_name, "Candidate")
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(sleep.call_args_list, [call(2)])

    @patch("gemini_service.genai.Client")
    def test_invalid_model_response_is_not_returned_as_report(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value.text = '{"question_scores":[]}'
        settings = GeminiSettings("test-key", "interview-model", "report-model")

        with self.assertRaisesRegex(GeminiServiceError, "incomplete or invalid report"):
            generate_interview_report(
                settings,
                "Test CV",
                "Marketing Specialist",
                [{"role": "user", "text": "I led a useful project."}],
            )

    @patch("gemini_service.genai.Client")
    def test_arabic_report_requests_arabic_text_fields(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value.text = json.dumps(
            valid_report_data()
        )
        settings = GeminiSettings("test-key", "interview-model", "report-model")

        generate_interview_report(
            settings,
            "خبرة في تطوير التطبيقات",
            "Software Engineer",
            [{"role": "user", "text": "قدت مشروعاً ناجحاً"}],
            language="ar",
        )

        request = client.models.generate_content.call_args.kwargs
        self.assertIn(
            "simple, professional Modern Standard Arabic",
            request["config"].system_instruction,
        )
        self.assertIn("Modern Standard Arabic practice", request["contents"])

    @patch("gemini_service.genai.Client")
    def test_arabic_report_retries_text_with_another_script(self, client_class):
        client = client_class.return_value
        invalid_report = valid_report_data()
        invalid_report["strengths"] = ["خبرة 中文"]
        client.models.generate_content.side_effect = [
            Mock(text=json.dumps(invalid_report, ensure_ascii=False)),
            Mock(text=json.dumps(valid_report_data(), ensure_ascii=False)),
        ]
        settings = GeminiSettings("test-key", "interview-model", "report-model")

        report = generate_interview_report(
            settings,
            "خبرة في تطوير التطبيقات",
            "مهندس برمجيات",
            [{"role": "user", "text": "قدت مشروعاً ناجحاً"}],
            language="ar",
        )

        self.assertEqual(report.strengths, valid_report_data()["strengths"])
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertIn(
            "Rewrite your response in clear Modern Standard Arabic",
            client.models.generate_content.call_args_list[1].kwargs["contents"],
        )


if __name__ == "__main__":
    unittest.main()
