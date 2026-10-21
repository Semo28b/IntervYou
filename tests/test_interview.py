import unittest
from unittest.mock import Mock, patch

from google.genai import errors

from gemini_service import (
    GeminiConfigurationError,
    GeminiServiceError,
    GeminiSettings,
    generate_opening_message,
    settings_from_secrets,
)
from interview import ANSWER_VALIDATION_MESSAGE, validate_answer, validate_job_title
from pdf_utils import UnreadablePDFError, extract_pdf_text


class InterviewInputTests(unittest.TestCase):
    def test_job_title_must_contain_non_whitespace(self):
        self.assertFalse(validate_job_title("   "))
        self.assertTrue(validate_job_title("Marketing Specialist"))

    def test_answer_requires_three_words_and_an_english_letter(self):
        self.assertFalse(validate_answer("two words"))
        self.assertFalse(validate_answer("123 !? 456"))
        self.assertFalse(validate_answer("هذه ثلاث كلمات"))
        self.assertTrue(validate_answer("I led a project"))

    def test_invalid_answer_message_is_short_and_specific(self):
        self.assertIn("3 words", ANSWER_VALIDATION_MESSAGE)
        self.assertIn("A–Z", ANSWER_VALIDATION_MESSAGE)


class PdfExtractionTests(unittest.TestCase):
    @patch("pdf_utils.PdfReader")
    def test_extracts_and_joins_text_from_pages(self, pdf_reader):
        first = Mock()
        first.extract_text.return_value = "Candidate CV"
        second = Mock()
        second.extract_text.return_value = "Experience"
        pdf_reader.return_value.pages = [first, second]

        text = extract_pdf_text(b"test pdf bytes")

        self.assertEqual(text, "Candidate CV\nExperience")

    @patch("pdf_utils.PdfReader")
    def test_rejects_pdf_without_extractable_text(self, pdf_reader):
        page = Mock()
        page.extract_text.return_value = ""
        pdf_reader.return_value.pages = [page]

        with self.assertRaises(UnreadablePDFError):
            extract_pdf_text(b"test pdf bytes")

    def test_rejects_empty_upload(self):
        with self.assertRaises(UnreadablePDFError):
            extract_pdf_text(b"")


class GeminiSetupTests(unittest.TestCase):
    def test_requires_api_key_and_both_model_settings(self):
        with self.assertRaises(GeminiConfigurationError):
            settings_from_secrets({})

    def test_keeps_interview_and_report_models_separate(self):
        settings = settings_from_secrets(
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_INTERVIEW_MODEL": "interview-model",
                "GEMINI_REPORT_MODEL": "report-model",
            }
        )

        self.assertEqual(settings.interview_model, "interview-model")
        self.assertEqual(settings.report_model, "report-model")

    @patch("gemini_service.genai.Client")
    def test_opening_request_uses_interview_model_and_cv_context(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value.text = (
            "Welcome. What interests you about this marketing role?"
        )
        settings = GeminiSettings(
            api_key="test-key",
            interview_model="interview-model",
            report_model="report-model",
        )

        message = generate_opening_message(
            settings,
            "CV mentions community campaigns.",
            "Marketing Specialist",
        )

        self.assertIn("What interests you", message)
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "interview-model")
        self.assertIn("CV mentions community campaigns.", request["contents"])
        self.assertIn("Marketing Specialist", request["contents"])

    @patch("gemini_service.genai.Client")
    def test_reports_temporary_gemini_unavailability(self, client_class):
        client = client_class.return_value
        client.models.generate_content.side_effect = errors.ServerError(
            code=503,
            response_json={"error": {"message": "Service unavailable"}},
        )
        settings = GeminiSettings(
            api_key="test-key",
            interview_model="interview-model",
            report_model="report-model",
        )

        with self.assertRaisesRegex(
            GeminiServiceError, "temporarily unavailable or experiencing high demand"
        ):
            generate_opening_message(settings, "CV text", "Job title")


if __name__ == "__main__":
    unittest.main()
