import json
import unittest
from contextlib import nullcontext
from unittest.mock import patch

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
            for number in range(1, 6)
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
            [1, 2, 3, 4, 5],
        )
        self.assertEqual(len(report.cv_suggestions), 3)

    def test_rejects_missing_question_score(self):
        data = valid_report_data()
        data["question_scores"].pop()

        with self.assertRaisesRegex(InvalidReportError, "exactly five"):
            parse_report_response(json.dumps(data))

    def test_rejects_duplicate_question_numbers(self):
        data = valid_report_data()
        data["question_scores"][4]["question_number"] = 4

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
    @patch("report.st.warning")
    @patch("report.st.markdown")
    @patch("report.st.metric")
    @patch("report.st.write")
    @patch("report.st.subheader")
    @patch("report.st.title")
    @patch("report.st.container", return_value=nullcontext())
    def test_arabic_report_uses_arabic_labels_and_candidate_fallback(
        self,
        _container,
        title,
        subheader,
        _write,
        metric,
        _markdown,
        warning,
    ):
        data = valid_report_data()
        data["cv_job_fit"]["clear_mismatch"] = True
        report = parse_report_response(json.dumps(data))

        render_report(report, "مهندس برمجيات", language="ar")

        title.assert_called_once_with("تقرير المقابلة")
        self.assertIn("المرشح", [call.args[0] for call in subheader.call_args_list])
        metric.assert_called_once_with("النتيجة", "7.5 / 10")
        warning.assert_called_once_with(
            "السيرة الذاتية لا تتوافق بوضوح مع هذه الوظيفة."
        )


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
        self.assertEqual(
            request["config"].response_mime_type,
            "application/json",
        )
        self.assertIn("Test CV with project experience.", request["contents"])
        self.assertIn("I led a useful project.", request["contents"])

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


if __name__ == "__main__":
    unittest.main()
