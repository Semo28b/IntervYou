import unittest
from unittest.mock import Mock, patch

from google.genai import errors

from gemini_service import (
    GeminiConfigurationError,
    GeminiServiceError,
    GeminiSettings,
    generate_opening_message,
    generate_interview_turn,
    settings_from_secrets,
)
from interview import (
    ANSWER_VALIDATION_MESSAGE,
    InterviewTurn,
    InvalidInterviewTurnError,
    allowed_interviewer_actions,
    queue_candidate_answer,
    record_interviewer_turn,
    validate_answer,
    validate_job_title,
)
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

    def test_invalid_answer_is_not_added_to_interview_messages(self):
        messages = [{"role": "assistant", "text": "Tell me about yourself."}]

        accepted = queue_candidate_answer("two words", messages)

        self.assertFalse(accepted)
        self.assertEqual(len(messages), 1)

    def test_valid_answer_is_queued_once(self):
        messages = [{"role": "assistant", "text": "Tell me about yourself."}]

        accepted = queue_candidate_answer("I led a useful project", messages)

        self.assertTrue(accepted)
        self.assertEqual(
            messages[-1],
            {"role": "user", "text": "I led a useful project"},
        )


class InterviewProgressTests(unittest.TestCase):
    def test_follow_up_increments_count_without_advancing_question(self):
        messages = []

        progress = record_interviewer_turn(
            messages,
            InterviewTurn("follow_up", "What was your specific role?"),
            question_number=2,
            follow_up_count=0,
        )

        self.assertEqual(progress.question_number, 2)
        self.assertEqual(progress.follow_up_count, 1)
        self.assertFalse(progress.finished)

    def test_next_question_resets_follow_up_count(self):
        messages = []

        progress = record_interviewer_turn(
            messages,
            InterviewTurn("question", "How did you measure the result?"),
            question_number=2,
            follow_up_count=2,
        )

        self.assertEqual(progress.question_number, 3)
        self.assertEqual(progress.follow_up_count, 0)

    def test_follow_up_cap_and_final_question_are_enforced(self):
        self.assertEqual(
            allowed_interviewer_actions(question_number=3, follow_up_count=2),
            ("question",),
        )
        self.assertEqual(
            allowed_interviewer_actions(question_number=5, follow_up_count=2),
            ("finish",),
        )
        with self.assertRaises(InvalidInterviewTurnError):
            record_interviewer_turn(
                [],
                InterviewTurn("follow_up", "One more detail?"),
                question_number=4,
                follow_up_count=2,
            )
        with self.assertRaises(InvalidInterviewTurnError):
            record_interviewer_turn(
                [],
                InterviewTurn("question", "Another main question?"),
                question_number=5,
                follow_up_count=0,
            )

    def test_finish_is_only_allowed_after_question_five(self):
        with self.assertRaises(InvalidInterviewTurnError):
            record_interviewer_turn(
                [],
                InterviewTurn("finish", "Thank you for your time."),
                question_number=4,
                follow_up_count=0,
            )
        progress = record_interviewer_turn(
            [],
            InterviewTurn("finish", "Thank you for your time."),
            question_number=5,
            follow_up_count=0,
        )
        self.assertTrue(progress.finished)

    def test_retry_response_does_not_duplicate_candidate_answer(self):
        messages = [{"role": "assistant", "text": "Tell me about yourself."}]
        queue_candidate_answer("I led a useful project", messages)
        pending_messages = list(messages)

        progress = record_interviewer_turn(
            messages,
            InterviewTurn("follow_up", "What was your specific role?"),
            question_number=1,
            follow_up_count=0,
        )

        self.assertEqual(messages.count(pending_messages[-1]), 1)
        self.assertEqual(progress.follow_up_count, 1)


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

    @patch("gemini_service.genai.Client")
    def test_interview_request_uses_json_and_enforces_current_action_choices(
        self, client_class
    ):
        client = client_class.return_value
        client.models.generate_content.return_value.text = (
            '{"action": "question", "text": "How did you approach that project?"}'
        )
        settings = GeminiSettings("test-key", "interview-model", "report-model")
        messages = [
            {"role": "assistant", "text": "Tell me about yourself."},
            {"role": "user", "text": "I led a useful project."},
        ]

        turn = generate_interview_turn(
            settings,
            "CV mentions project leadership.",
            "Marketing Specialist",
            messages,
            question_number=1,
            follow_up_count=2,
        )

        self.assertEqual(turn.action, "question")
        self.assertEqual(turn.text, "How did you approach that project?")
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "interview-model")
        self.assertEqual(
            request["config"].response_schema.properties["action"].enum,
            ["question"],
        )
        self.assertIn("CV mentions project leadership.", request["contents"])
        self.assertIn("I led a useful project.", request["contents"])

    @patch("gemini_service.genai.Client")
    def test_rejects_unusable_interview_response(self, client_class):
        client = client_class.return_value
        client.models.generate_content.return_value.text = "not json"
        settings = GeminiSettings("test-key", "interview-model", "report-model")

        with self.assertRaisesRegex(GeminiServiceError, "unusable interview response"):
            generate_interview_turn(
                settings,
                "CV text",
                "Job title",
                [{"role": "user", "text": "I led a useful project."}],
                question_number=1,
                follow_up_count=0,
            )


if __name__ == "__main__":
    unittest.main()
