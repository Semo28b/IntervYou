import json
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import localize_cv_error, localize_interview_error
from gemini_service import GeminiServiceError
from report import parse_report_response
from rtl import isolate_latin_runs


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
                    for number in range(1, 7)
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
    def test_arabic_start_screen_localizes_and_scopes_rtl_styles(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["language_choice"] = "العربية"

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("مقابلتك القادمة" in item.value for item in app.markdown)
        )
        self.assertEqual(app.segmented_control[0].label, "لغة المقابلة")
        self.assertEqual(app.segmented_control[0].options, ["English", "العربية"])
        self.assertEqual(
            app.file_uploader[0].label,
            "ارفع سيرتك الذاتية \u2068(PDF)\u2069",
        )
        self.assertEqual(app.text_input[0].label, "المسمى الوظيفي")
        self.assertEqual(app.text_input[0].placeholder, "مهندس برمجيات")
        self.assertTrue(any("Google Gemini" in item.value for item in app.caption))
        self.assertTrue(
            any(
                "إلى \u2068Google Gemini\u2069. لا يحفظها التطبيق."
                in item.value
                for item in app.caption
            )
        )
        self.assertTrue(any(item.label == "ابدأ المقابلة" for item in app.button))

        styles = app.markdown[0].value
        self.assertIn(
            ".st-key-arabic_start_card .st-key-language_choice,\n"
            ".st-key-arabic_start_card .st-key-language_choice > div {\n"
            "    width: 100%;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card .stButtonGroup {\n"
            "    display: block;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card [role=\"radiogroup\"] {\n"
            "    display: flex;\n"
            "    width: max-content !important;\n"
            "    max-width: 100%;\n"
            "    margin-left: auto !important;\n"
            "    margin-right: 0 !important;\n"
            "    align-self: flex-end;\n"
            "    direction: rtl;\n"
            "}",
            styles,
        )
        self.assertIn(
            ".st-key-start_card [role=\"radiogroup\"] button[aria-checked=\"true\"] {\n"
            "    background-color: #BFE4CF !important;\n"
            "    color: #2D4036 !important;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card .stElementContainer:has(\n"
            "    > [data-testid=\"stButton\"]\n"
            ") {\n"
            "    width: 100%;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card [data-testid=\"stButton\"] {\n"
            "    width: 100%;\n"
            "    display: flex;\n"
            "    justify-content: flex-end;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card [data-testid=\"stButton\"] button {\n"
            "    width: auto;\n"
            "    margin-left: auto;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_welcome {\n"
            "    width: 100%;\n"
            "    direction: rtl;\n"
            "    text-align: right;",
            styles,
        )
        self.assertIn(
            ".st-key-arabic_start_card input {\n"
            "    direction: rtl;\n"
            "    text-align: right;\n"
            "    unicode-bidi: plaintext;",
            styles,
        )
        self.assertNotIn(
            ".st-key-arabic_start_card {\n    direction: rtl;",
            styles
        )
        self.assertTrue(
            any(
                '<div style="direction: rtl; text-align: right;">' in item.value
                for item in app.markdown
            )
        )

    def test_english_start_screen_remains_english(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any("Ready to practice" in item.value for item in app.title))
        self.assertEqual(app.segmented_control[0].label, "Interview language")
        self.assertEqual(
            app.segmented_control[0].options, ["English", "العربية"]
        )
        self.assertEqual(app.segmented_control[0].value, "English")
        self.assertEqual(app.file_uploader[0].label, "Upload your CV (PDF)")
        self.assertEqual(app.text_input[0].label, "Job title you're applying for")
        self.assertTrue(any(item.label == "Start interview" for item in app.button))

    def test_latin_runs_are_isolated_inside_arabic_text(self):
        self.assertEqual(
            isolate_latin_runs("المسمى CES - C++ مناسب"),
            "المسمى \u2068CES - C++\u2069 مناسب",
        )
        self.assertEqual(
            isolate_latin_runs("راجع R&D Manager وPDF"),
            "راجع \u2068R&D Manager\u2069 و\u2068PDF\u2069",
        )
        self.assertEqual(
            isolate_latin_runs(".(Data-driven)"),
            "\u2068.(Data-driven)\u2069",
        )
        self.assertEqual(
            isolate_latin_runs("مرحباً،Dar Anwar"),
            "مرحباً\u2068،Dar Anwar\u2069",
        )

    def test_arabic_start_reports_invalid_title_after_cv_upload(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=20)

        sample_dir = Path(__file__).resolve().parents[1] / "sample_cvs"
        sample_pdf = next(sample_dir.glob("*.pdf"))
        app.segmented_control[0].set_value("العربية")
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
        app.session_state["question_number"] = 6
        app.session_state["interview_messages"] = [
            {
                "role": "assistant",
                "text": "مرحباً، أخبرني عن وظيفة CES - C++.",
            }
        ]
        app.session_state["interview_finished"] = True
        app.session_state["chat_scroll_pending"] = True

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("مقابلة عمل تجريبية" in item.value for item in app.title)
        )
        self.assertTrue(any(item.label == "عرض تقريري" for item in app.button))
        self.assertFalse(any(item.label == "View my report" for item in app.button))
        self.assertEqual(app.chat_input[0].placeholder, "انتهت المقابلة")
        self.assertTrue(any("السؤال 6 من 6" in item.value for item in app.caption))
        self.assertTrue(
            any("\u2068CES - C++.\u2069" in item.value for item in app.markdown)
        )
        self.assertEqual(len(app.html), 1)
        self.assertIn("scrollIntoView", app.html[0].value)
        self.assertIn('block: "start"', app.html[0].value)
        self.assertIn("focus({ preventScroll: true })", app.html[0].value)
        self.assertFalse(app.session_state["chat_scroll_pending"])

    def test_arabic_chat_input_queues_reply_from_main_area(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "interview"
        app.session_state["interview_language"] = "ar"
        app.session_state["interview_messages"] = [
            {"role": "assistant", "text": "حدثني عن مشروع عملت عليه."}
        ]
        app.session_state["cv_text"] = "Candidate CV"
        app.session_state["job_title"] = "مهندس برمجيات"
        answer = "قدت فريقاً من خمسة أشخاص لإنجاز المشروع في موعده."

        app.run(timeout=20)
        with patch(
            "gemini_service.generate_interview_turn",
            side_effect=GeminiServiceError("Gemini is temporarily unavailable."),
        ):
            app.chat_input[0].set_value(answer).run(timeout=20)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pending_answer"], answer)
        self.assertEqual(app.session_state["interview_messages"][-1]["role"], "user")
        self.assertEqual(app.session_state["interview_messages"][-1]["text"], answer)

    def test_english_chat_shows_question_counter_out_of_six(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "interview"
        app.session_state["interview_language"] = "en"
        app.session_state["question_number"] = 4
        app.session_state["chat_scroll_pending"] = True
        app.session_state["interview_messages"] = [
            {"role": "assistant", "text": "Scenario question"}
        ]

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any("Question 4 of 6" in item.value for item in app.caption))
        self.assertEqual(app.chat_input[0].placeholder, "Type your answer")
        self.assertEqual(len(app.html), 1)
        self.assertIn("scrollIntoView", app.html[0].value)
        self.assertIn('block: "start"', app.html[0].value)
        first_update_id = app.session_state["chat_scroll_update_id"]
        first_focus_script = app.html[0].value

        app.session_state["chat_scroll_pending"] = True
        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["chat_scroll_update_id"], first_update_id + 1)
        self.assertNotEqual(app.html[0].value, first_focus_script)
        self.assertIn("focusChatInput, 500", app.html[0].value)

    def test_english_chat_input_queues_reply(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["phase"] = "interview"
        app.session_state["interview_language"] = "en"
        app.session_state["interview_messages"] = [
            {"role": "assistant", "text": "Tell me about your recent work."}
        ]
        app.session_state["cv_text"] = "Candidate CV"
        app.session_state["job_title"] = "Software Engineer"
        answer = "I led a team of five to deliver the project on time."

        app.run(timeout=20)
        with patch(
            "gemini_service.generate_interview_turn",
            side_effect=GeminiServiceError("Gemini is temporarily unavailable."),
        ):
            app.chat_input[0].set_value(answer).run(timeout=20)

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pending_answer"], answer)
        self.assertEqual(app.session_state["interview_messages"][-1]["role"], "user")
        self.assertEqual(app.session_state["interview_messages"][-1]["text"], answer)

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
        self.assertTrue(
            any("خدمة \u2068Gemini\u2069" in item.value for item in app.error)
        )

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
