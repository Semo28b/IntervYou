import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from gemini_service import (
    GeminiConfigurationError,
    GeminiServiceError,
    generate_opening_message,
    generate_interview_turn,
    settings_from_secrets,
)
from interview import (
    ANSWER_VALIDATION_MESSAGE,
    InvalidInterviewTurnError,
    InterviewMessage,
    JOB_TITLE_VALIDATION_MESSAGE,
    queue_candidate_answer,
    record_interviewer_turn,
    validate_job_title,
)
from pdf_utils import UnreadablePDFError, extract_pdf_text


def clear_start_error() -> None:
    st.session_state.start_error_field = None
    st.session_state.start_error_message = None


def load_gemini_settings():
    try:
        return settings_from_secrets(st.secrets)
    except StreamlitSecretNotFoundError as exc:
        raise GeminiConfigurationError(
            "Create .streamlit/secrets.toml from the example and add the key "
            "and both model IDs."
        ) from exc


def set_start_error(field: str, message: str) -> None:
    st.session_state.start_error_field = field
    st.session_state.start_error_message = message


def render_start_screen() -> None:
    st.title("AI Mock Interview")
    st.header("Ready to practice your next interview?")
    st.write(
        "Upload your CV, tell us the job you're aiming for, and we'll run a "
        "realistic interview, then show you how you did."
    )

    uploaded_file = st.file_uploader(
        "Upload your CV (PDF)",
        type=["pdf"],
        key="cv_upload",
        on_change=clear_start_error,
    )
    if st.session_state.start_error_field == "cv":
        st.error(st.session_state.start_error_message)
    if uploaded_file is not None:
        st.write(f"{uploaded_file.name} — PDF uploaded")

    job_title = st.text_input(
        "Job title you're applying for",
        placeholder="Marketing Specialist",
        key="job_title_input",
        on_change=clear_start_error,
    )
    if st.session_state.start_error_field == "job_title":
        st.error(st.session_state.start_error_message)
    elif job_title and not validate_job_title(job_title):
        st.error(JOB_TITLE_VALIDATION_MESSAGE)

    st.caption("Your CV and answers are sent to Google Gemini. Not saved by this app.")
    start_clicked = st.button(
        "Start interview",
        disabled=uploaded_file is None or not validate_job_title(job_title),
    )

    if st.session_state.start_error_field == "setup":
        st.error(st.session_state.start_error_message)

    if not start_clicked:
        return

    if not validate_job_title(job_title):
        set_start_error("job_title", JOB_TITLE_VALIDATION_MESSAGE)
        st.rerun()

    try:
        cv_text = extract_pdf_text(uploaded_file.getvalue())
    except UnreadablePDFError:
        set_start_error(
            "cv",
            "We couldn't read text in this PDF. Please upload a text-based PDF CV.",
        )
        st.rerun()

    try:
        settings = load_gemini_settings()
        with st.spinner("The interviewer is preparing your first question..."):
            opening_message = generate_opening_message(
                settings,
                cv_text,
                job_title.strip(),
            )
    except GeminiConfigurationError as exc:
        set_start_error("setup", str(exc))
        st.rerun()
    except GeminiServiceError as exc:
        set_start_error("setup", str(exc))
        st.rerun()

    st.session_state.cv_text = cv_text
    st.session_state.cv_name = uploaded_file.name
    st.session_state.job_title = job_title.strip()
    st.session_state.opening_message = opening_message
    st.session_state.interview_messages = [
        {"role": "assistant", "text": opening_message}
    ]
    st.session_state.question_number = 1
    st.session_state.follow_up_count = 0
    st.session_state.pending_answer = None
    st.session_state.interview_error = None
    st.session_state.answer_error = None
    st.session_state.interview_finished = False
    st.session_state.phase = "interview"
    clear_start_error()
    st.rerun()


def process_pending_answer() -> None:
    try:
        settings = load_gemini_settings()
        turn = generate_interview_turn(
            settings,
            st.session_state.cv_text,
            st.session_state.job_title,
            st.session_state.interview_messages,
            st.session_state.question_number,
            st.session_state.follow_up_count,
        )
        progress = record_interviewer_turn(
            st.session_state.interview_messages,
            turn,
            st.session_state.question_number,
            st.session_state.follow_up_count,
        )
    except (
        GeminiConfigurationError,
        GeminiServiceError,
        InvalidInterviewTurnError,
    ) as exc:
        st.session_state.interview_error = str(exc)
        return

    st.session_state.question_number = progress.question_number
    st.session_state.follow_up_count = progress.follow_up_count
    st.session_state.interview_finished = progress.finished
    st.session_state.pending_answer = None
    st.session_state.interview_error = None


def render_interview_screen() -> None:
    st.title("AI Mock Interview")
    for message in st.session_state.interview_messages:
        with st.chat_message(message["role"]):
            st.write(message["text"])

    if st.session_state.answer_error:
        with st.chat_message("assistant"):
            st.error(st.session_state.answer_error)

    if st.session_state.pending_answer is not None:
        if st.session_state.interview_error:
            with st.chat_message("assistant"):
                st.error(st.session_state.interview_error)
            if st.button("Try again", key="retry_interview_request"):
                st.session_state.interview_error = None
                st.rerun()
        else:
            with st.spinner("The interviewer is thinking..."):
                process_pending_answer()
            if st.session_state.interview_error is None:
                st.rerun()

    placeholder = (
        "The interview has ended"
        if st.session_state.interview_finished
        else "Type your answer"
    )
    answer = st.chat_input(
        placeholder=placeholder,
        disabled=(
            st.session_state.interview_finished
            or st.session_state.pending_answer is not None
        ),
    )
    if answer is None:
        return

    if not queue_candidate_answer(answer, st.session_state.interview_messages):
        st.session_state.answer_error = ANSWER_VALIDATION_MESSAGE
        st.rerun()

    st.session_state.answer_error = None
    st.session_state.pending_answer = answer
    st.session_state.interview_error = None
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="AI Mock Interview")
    defaults = {
        "phase": "start",
        "start_error_field": None,
        "start_error_message": None,
        "interview_messages": None,
        "question_number": 1,
        "follow_up_count": 0,
        "pending_answer": None,
        "interview_error": None,
        "answer_error": None,
        "interview_finished": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.interview_messages is None:
        st.session_state.interview_messages = []
    if (
        st.session_state.phase == "interview"
        and not st.session_state.interview_messages
    ):
        st.session_state.interview_messages = [
            {"role": "assistant", "text": st.session_state.opening_message}
        ]

    if st.session_state.phase == "start":
        render_start_screen()
    else:
        render_interview_screen()


if __name__ == "__main__":
    main()
