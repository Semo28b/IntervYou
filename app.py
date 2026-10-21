import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from gemini_service import (
    GeminiConfigurationError,
    GeminiServiceError,
    generate_opening_message,
    settings_from_secrets,
)
from interview import validate_job_title
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

    st.caption("Your CV and answers are sent to Google Gemini. Not saved by this app.")
    start_clicked = st.button(
        "Start interview",
        disabled=uploaded_file is None or not job_title,
    )

    if st.session_state.start_error_field == "setup":
        st.error(st.session_state.start_error_message)

    if not start_clicked:
        return

    if not validate_job_title(job_title):
        set_start_error("job_title", "Please enter a job title.")
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
    st.session_state.phase = "interview"
    clear_start_error()
    st.rerun()


def render_interview_screen() -> None:
    st.title("AI Mock Interview")
    st.chat_message("assistant").write(st.session_state.opening_message)


def main() -> None:
    st.set_page_config(page_title="AI Mock Interview")
    defaults = {
        "phase": "start",
        "start_error_field": None,
        "start_error_message": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.phase == "start":
        render_start_screen()
    else:
        render_interview_screen()


if __name__ == "__main__":
    main()
