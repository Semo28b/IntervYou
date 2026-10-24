import json
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app import localize_cv_error, localize_interview_error
from report import parse_report_response


def complete_report():
    return parse_report_response(
        json.dumps(
            {
                "candidate_name": None,
                "overall_score": 7,
                "overall_reason": "Clear examples.",
                "question_scores": [
                    {
                        "question_number": number,
                        "score": 7,
                        "reason": "A clear example.",
                    }
                    for number in range(1, 6)
                ],
                "strengths": ["Clear communication."],
                "areas_to_improve": ["Add more detail."],
                "cv_job_fit": {
                    "strengths": ["Relevant skills."],
                    "gaps": ["Limited experience."],
                    "clear_mismatch": False,
                },
                "cv_suggestions": [
                    "Add measurable results.",
                    "Highlight projects.",
                    "List relevant tools.",
                ],
            }
        )
    )


class ArabicInterfaceTests(unittest.TestCase):
    def test_arabic_start_reports_invalid_title_after_cv_upload(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=20)

        sample_dir = Path(__file__).resolve().parents[1] / "sample_cvs"
        sample_pdf = next(sample_dir.glob("*.pdf"))
        app.selectbox[0].set_value("العربية")
        app.file_uploader[0].set_value(
            (sample_pdf.name, sample_pdf.read_bytes(), "application/pdf")
        )
        app.text_input[0].set_value("M")
        app.run(timeout=20)

        self.assertFalse(app.exception)
        start_button = next(
            button for button in app.button if button.label == "ابدأ المقابلة"
        )
        self.assertFalse(start_button.disabled)
        start_button.click().run(timeout=20)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["phase"], "start")
        self.assertTrue(any("مسمى وظيفي" in item.value for item in app.error))

    def test_arabic_chat_uses_localized_controls_and_finished_placeholder(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "interview"
        app.session_state["interview_language"] = "ar"
        app.session_state["interview_messages"] = [
            {"role": "assistant", "text": "مرحباً، أخبرني عن خبرتك."}
        ]
        app.session_state["interview_finished"] = True

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("مقابلة عمل تجريبية" in item.value for item in app.title)
        )
        self.assertTrue(any(item.label == "عرض تقريري" for item in app.button))
        self.assertFalse(any(item.label == "View my report" for item in app.button))
        self.assertEqual(app.chat_input[0].placeholder, "انتهت المقابلة")

    def test_report_shown_after_interview_renders_one_shot_scroll_to_top(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "report"
        app.session_state["interview_language"] = "en"
        app.session_state["job_title"] = "Software Engineer"
        app.session_state["report"] = complete_report()
        app.session_state["report_error"] = None
        app.session_state["scroll_to_top_pending"] = True

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.html), 1)
        self.assertIn("window.scrollTo", app.html[0].value)
        self.assertFalse(app.session_state["scroll_to_top_pending"])

    def test_report_scroll_hook_runs_in_arabic_and_start_after_restart(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "report"
        app.session_state["interview_language"] = "ar"
        app.session_state["job_title"] = "مهندس برمجيات"
        app.session_state["report"] = complete_report()
        app.session_state["report_error"] = None
        app.session_state["scroll_to_top_pending"] = True

        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.html), 1)
        self.assertFalse(app.session_state["scroll_to_top_pending"])

        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["phase"], "start")
        self.assertEqual(len(app.html), 1)
        self.assertFalse(app.session_state["scroll_to_top_pending"])

    def test_arabic_chat_retry_and_error_text_are_localized(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "interview"
        app.session_state["interview_language"] = "ar"
        app.session_state["interview_messages"] = [
            {"role": "assistant", "text": "مرحباً"}
        ]
        app.session_state["pending_answer"] = "قدت مشروعاً ناجحاً"
        app.session_state["interview_error"] = (
            "Gemini is temporarily unavailable. Please try again."
        )

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any(item.label == "حاول مرة أخرى" for item in app.button))
        self.assertTrue(any("خدمة Gemini" in item.value for item in app.error))

    def test_arabic_report_uses_localized_restart_control(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "report"
        app.session_state["interview_language"] = "ar"
        app.session_state["job_title"] = "Software Engineer"
        app.session_state["report"] = complete_report()
        app.session_state["report_error"] = None

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any(item.label == "ابدأ مقابلة جديدة" for item in app.button))
        self.assertFalse(
            any(item.label == "Start a new interview" for item in app.button)
        )

    def test_arabic_errors_are_localized_and_english_errors_unchanged(self):
        message = "Gemini is temporarily unavailable. Please try again."

        self.assertIn("خدمة Gemini", localize_interview_error(message, "ar"))
        self.assertEqual(localize_interview_error(message, "en"), message)

    def test_non_cv_errors_are_localized_without_gemini(self):
        message = "This doesn't look like a CV. Please upload your CV as a PDF."

        self.assertEqual(localize_cv_error(message, "en"), message)
        self.assertIn("لا يبدو سيرة ذاتية", localize_cv_error(message, "ar"))


if __name__ == "__main__":
    unittest.main()
