import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from gemini_service import (
    GeminiConfigurationError,
    GeminiServiceError,
    generate_interview_report,
    generate_interview_turn,
    generate_opening_message,
    settings_from_secrets,
)
from interview import (
    InvalidInterviewTurnError,
    answer_validation_message,
    clear_session_state,
    job_title_validation_message,
    normalize_job_title,
    queue_candidate_answer,
    record_interviewer_turn,
    validate_job_title,
)
from pdf_utils import UnreadablePDFError, extract_pdf_text, looks_like_cv
from report import render_report
from rtl import isolate_latin_runs


def clear_start_error() -> None:
    st.session_state.start_error_field = None
    st.session_state.start_error_message = None


def normalize_job_title_input() -> None:
    st.session_state.job_title_input = normalize_job_title(
        st.session_state.get("job_title_input", "")
    )
    clear_start_error()


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


def localize_interview_error(message: str, language: str) -> str:
    if language != "ar":
        return message
    if "temporarily unavailable" in message:
        return "خدمة Gemini غير متاحة مؤقتاً. يرجى المحاولة بعد قليل."
    if "rate limit or quota" in message:
        return "تم بلوغ حد استخدام Gemini. يرجى المحاولة لاحقاً."
    if "rejected the API key" in message:
        return "تعذر التحقق من مفتاح Gemini. يرجى مراجعة الإعدادات."
    if "model was not found" in message:
        return "لم يتم العثور على نموذج Gemini المحدد. يرجى مراجعة الإعدادات."
    if "Gemini returned API error" in message:
        return "حدث خطأ في خدمة Gemini. يرجى التحقق من الإعدادات والمحاولة مجدداً."
    if "Add GEMINI_" in message or "Create .streamlit/secrets.toml" in message:
        return "يرجى إعداد مفتاح Gemini والنماذج في ملف الإعدادات المحلي."
    if "empty opening message" in message:
        return "لم يصل سؤال من المحاور. يرجى المحاولة مجدداً."
    if "unusable interview response" in message:
        return "تعذر معالجة رد المحاور. يرجى المحاولة مجدداً."
    if "invalid report" in message or "incomplete" in message:
        return "تعذر إعداد التقرير كاملاً. يرجى المحاولة مجدداً."
    if "unsupported characters" in message:
        return "أعاد Gemini نصاً يحتوي على أحرف غير متوقعة. يرجى المحاولة مجدداً."
    return "حدث خطأ أثناء معالجة المقابلة. يرجى المحاولة مجدداً."


def localize_cv_error(message: str, language: str) -> str:
    if language != "ar":
        return message
    if "doesn't look like a CV" in message:
        return "هذا الملف لا يبدو سيرة ذاتية. يرجى رفع سيرتك الذاتية بصيغة PDF."
    return "تعذر قراءة النص في هذا الملف. يرجى رفع سيرة ذاتية نصية بصيغة PDF."


def _display_text(text: str, language: str) -> str:
    return isolate_latin_runs(text) if language == "ar" else text


def inject_theme_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 62rem;
            padding-top: clamp(2.5rem, 7vh, 4.5rem);
            padding-bottom: clamp(2rem, 5vh, 3rem);
        }
        .st-key-start_card,
        .st-key-arabic_start_card {
            max-width: 46rem;
            margin-inline: auto;
        }
        .st-key-arabic_start_card [data-testid="stWidgetLabel"],
        .st-key-arabic_start_card [data-testid="stWidgetLabel"] p {
            direction: rtl;
            text-align: right;
        }
        .st-key-arabic_welcome {
            width: 100%;
            direction: rtl;
            text-align: right;
        }
        .st-key-arabic_welcome [data-testid="stMarkdownContainer"] {
            width: 100%;
            text-align: right;
        }
        .st-key-arabic_start_card [data-testid="stSegmentedControl"] {
            direction: rtl;
        }
        .st-key-arabic_start_card input {
            direction: rtl;
            text-align: right;
            unicode-bidi: plaintext;
        }
        .st-key-arabic_start_card [data-testid="stButton"] {
            direction: rtl;
        }
        .brand-pill {
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            background: #FFF1C4;
            color: #35433D;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.06em;
        }
        [data-testid="stFileUploaderDropzone"] {
            border: 1px dashed #D8CC91;
            border-radius: 12px;
            background: #FFF9E7;
        }
        button[kind="primary"] {
            border-color: #BFE4CF;
            background: #BFE4CF;
            color: #2D4036;
        }
        button[kind="primary"]:hover {
            border-color: #A9D9BD;
            background: #A9D9BD;
            color: #2D4036;
        }
        [data-testid="stChatMessageContent"][aria-label="Chat message from user"],
        [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"] {
            padding: 0.6rem 0.85rem;
            border-radius: 16px;
        }
        [data-testid="stChatMessageContent"][aria-label="Chat message from user"] {
            background: #DFF2E5;
        }
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) {
            background: transparent;
        }
        [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"] {
            background: #F0F0F0;
        }
        [data-testid="stChatInput"] button {
            border-color: #DFF2E5;
            background: #DFF2E5;
            color: #35433D;
        }
        [data-testid="stChatInput"] button:hover {
            border-color: #C9E8D4;
            background: #C9E8D4;
            color: #35433D;
        }
        .st-key-view_my_report_button button,
        .st-key-view_my_report_button button:hover {
            border-color: #DFF2E5;
            background: #DFF2E5;
            color: #35433D;
        }
        .st-key-arabic_interview,
        .st-key-arabic_report {
            direction: rtl;
            text-align: right;
        }
        .st-key-arabic_interview [data-testid="stChatMessageContent"],
        .st-key-arabic_interview [data-testid="stChatInput"] textarea,
        .stApp:has(.st-key-arabic_interview) [data-testid="stChatInput"] textarea {
            direction: rtl;
            text-align: right;
        }
        .st-key-arabic_interview [data-testid="stHorizontalBlock"] {
            direction: ltr;
        }
        [data-testid="stChatMessage"] {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_start_screen() -> None:
    language = "ar" if st.session_state.get("language_choice") == "العربية" else "en"
    container_key = "arabic_start_card" if language == "ar" else "start_card"
    with st.container(border=True, key=container_key):
        brand = "AI MOCK INTERVIEW"
        if language == "ar":
            brand = isolate_latin_runs(brand)
        st.markdown(
            f'<div class="brand-pill">{brand}</div>',
            unsafe_allow_html=True,
        )
        if language == "ar":
            with st.container(key="arabic_welcome"):
                st.markdown(
                    """
                    <div style="direction: rtl; text-align: right;">
                        <h1>هل أنت مستعد لمقابلتك القادمة؟</h1>
                        <p>ارفع سيرتك الذاتية وحدد الوظيفة لتبدأ مقابلة واقعية.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.title("Ready to practice your next interview?")
            st.write(
                "Upload your CV, tell us the job you're aiming for, and we'll run "
                "a realistic interview, then show you how you did."
            )

        language_choice = st.segmented_control(
            "لغة المقابلة" if language == "ar" else "Interview language",
            ("English", "العربية"),
            key="language_choice",
            default="English",
            on_change=clear_start_error,
        )
        language = "ar" if language_choice == "العربية" else "en"

        uploaded_file = st.file_uploader(
            isolate_latin_runs("ارفع سيرتك الذاتية (PDF)")
            if language == "ar"
            else "Upload your CV (PDF)",
            type=["pdf"],
            key="cv_upload",
            on_change=clear_start_error,
        )
        if st.session_state.start_error_field == "cv":
            st.error(
                isolate_latin_runs(
                    localize_cv_error(st.session_state.start_error_message, language)
                )
            )
        if uploaded_file is not None:
            st.write(
                isolate_latin_runs(f"{uploaded_file.name} — تم رفع ملف PDF")
                if language == "ar"
                else f"{uploaded_file.name} — PDF uploaded"
            )

        job_title = st.text_input(
            isolate_latin_runs("المسمى الوظيفي")
            if language == "ar"
            else "Job title you're applying for",
            placeholder="مهندس برمجيات" if language == "ar" else "Marketing Specialist",
            key="job_title_input",
            on_change=normalize_job_title_input,
        )
        title_error = job_title_validation_message(language)
        if st.session_state.start_error_field == "job_title":
            st.error(_display_text(st.session_state.start_error_message, language))
        elif job_title and not validate_job_title(job_title):
            st.error(_display_text(title_error, language))
        if st.session_state.start_error_field == "setup":
            st.error(_display_text(st.session_state.start_error_message, language))

        st.caption(
            isolate_latin_runs(
                "ستُرسل سيرتك الذاتية وإجاباتك إلى Google Gemini. لا يحفظها التطبيق."
            )
            if language == "ar"
            else "Your CV and answers are sent to Google Gemini. Not saved by this app."
        )
        start_clicked = st.button(
            isolate_latin_runs("ابدأ المقابلة")
            if language == "ar"
            else "Start interview",
            type="primary",
            disabled=uploaded_file is None,
        )

        if not start_clicked:
            return

        try:
            cv_text = extract_pdf_text(uploaded_file.getvalue())
        except UnreadablePDFError:
            set_start_error(
                "cv",
                "We couldn't read text in this PDF. Please upload a text-based PDF CV.",
            )
            st.rerun()

        if not looks_like_cv(cv_text):
            set_start_error(
                "cv",
                "This doesn't look like a CV. Please upload your CV as a PDF.",
            )
            st.rerun()

        if not validate_job_title(job_title):
            set_start_error("job_title", title_error)
            st.rerun()

        try:
            settings = load_gemini_settings()
            preparing_message = (
                "يُعد المحاور سؤاله الأول..."
                if language == "ar"
                else "The interviewer is preparing your first question..."
            )
            with st.spinner(preparing_message):
                opening_message = generate_opening_message(
                    settings,
                    cv_text,
                    job_title.strip(),
                    language=language,
                )
        except GeminiConfigurationError as exc:
            set_start_error(
                "setup",
                localize_interview_error(str(exc), language),
            )
            st.rerun()
        except GeminiServiceError as exc:
            set_start_error(
                "setup",
                localize_interview_error(str(exc), language),
            )
            st.rerun()

        st.session_state.cv_text = cv_text
        st.session_state.cv_name = uploaded_file.name
        st.session_state.job_title = normalize_job_title(job_title)
        st.session_state.interview_language = language
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
        st.session_state.chat_scroll_pending = True
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
            language=st.session_state.get("interview_language", "en"),
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
    st.session_state.chat_scroll_pending = True


def restart_interview() -> None:
    clear_session_state(st.session_state)
    st.session_state.scroll_to_top_pending = True


def scroll_to_top_if_pending() -> None:
    if not st.session_state.get("scroll_to_top_pending", False):
        return

    st.html(
        """
        <script>
        (() => {
          const scrollToTop = () => {
            window.scrollTo({ top: 0, left: 0, behavior: "instant" });
            for (const selector of [
              '[data-testid="stAppViewContainer"]',
              '[data-testid="stMain"]',
              "section.main"
            ]) {
              document.querySelector(selector)?.scrollTo({
                top: 0,
                left: 0,
                behavior: "instant"
              });
            }
          };
          scrollToTop();
          requestAnimationFrame(scrollToTop);
          setTimeout(scrollToTop, 50);
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
    st.session_state.scroll_to_top_pending = False


def scroll_to_latest_message_if_pending() -> None:
    if not st.session_state.get("chat_scroll_pending", False):
        return

    st.html(
        """
        <script>
        (() => {
          const scrollToLatestMessage = () => {
            const messages = document.querySelectorAll(
              '[data-testid="stChatMessage"]'
            );
            const latestMessage = messages[messages.length - 1];
            if (latestMessage) {
              latestMessage.scrollIntoView({
                block: "end",
                behavior: "smooth"
              });
            }
          };
          requestAnimationFrame(scrollToLatestMessage);
          setTimeout(scrollToLatestMessage, 50);
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
    st.session_state.chat_scroll_pending = False


def render_interview_screen() -> None:
    language = st.session_state.get("interview_language", "en")
    container_key = "arabic_interview" if language == "ar" else "interview_screen"
    answer = None
    if language == "ar":
        placeholder = (
            "انتهت المقابلة"
            if st.session_state.interview_finished
            else "اكتب إجابتك"
        )
        answer = st.chat_input(
            placeholder=placeholder,
            disabled=(
                st.session_state.interview_finished
                or st.session_state.pending_answer is not None
            ),
        )

    with st.container(key=container_key):
        st.title("مقابلة عمل تجريبية" if language == "ar" else "AI Mock Interview")
        question_label = (
            f"السؤال {st.session_state.question_number} من 6"
            if language == "ar"
            else f"Question {st.session_state.question_number} of 6"
        )
        st.caption(question_label)
        for message in st.session_state.interview_messages:
            left, right = st.columns(2)
            if language == "ar":
                message_column = (
                    right if message["role"] == "assistant" else left
                )
            else:
                message_column = (
                    left if message["role"] == "assistant" else right
                )
            with message_column:
                avatar = "🧑‍💼" if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar):
                    st.write(
                        isolate_latin_runs(message["text"])
                        if language == "ar"
                        else message["text"]
                    )

        if st.session_state.answer_error:
            with st.chat_message("assistant"):
                st.error(
                    isolate_latin_runs(st.session_state.answer_error)
                    if language == "ar"
                    else st.session_state.answer_error
                )

        if st.session_state.pending_answer is not None:
            if st.session_state.interview_error:
                with st.chat_message("assistant"):
                    st.error(
                        isolate_latin_runs(
                            localize_interview_error(
                                st.session_state.interview_error,
                                language,
                            )
                        )
                    )
                retry_label = "حاول مرة أخرى" if language == "ar" else "Try again"
                if st.button(retry_label, key="retry_interview_request"):
                    st.session_state.interview_error = None
                    st.rerun()
            else:
                thinking_message = (
                    "يفكر المحاور..."
                    if language == "ar"
                    else "The interviewer is thinking..."
                )
                with st.spinner(thinking_message):
                    process_pending_answer()
                if st.session_state.interview_error is None:
                    st.rerun()

        report_button_label = (
            "عرض تقريري" if language == "ar" else "View my report"
        )
        if st.session_state.interview_finished and st.button(
            report_button_label,
            key="view_my_report_button",
        ):
            st.session_state.phase = "report"
            st.session_state.report = None
            st.session_state.report_error = None
            st.session_state.scroll_to_top_pending = True
            st.rerun()

        if language != "ar":
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
        scroll_to_latest_message_if_pending()
        return

    if not queue_candidate_answer(
        answer,
        st.session_state.interview_messages,
        language,
    ):
        st.session_state.answer_error = answer_validation_message(language)
        st.rerun()

    st.session_state.answer_error = None
    st.session_state.chat_scroll_pending = True
    st.session_state.pending_answer = answer
    st.session_state.interview_error = None
    st.rerun()


def render_report_screen() -> None:
    language = st.session_state.get("interview_language", "en")
    container_key = "arabic_report" if language == "ar" else "report_screen"
    with st.container(key=container_key):
        if st.session_state.report is None and st.session_state.report_error is None:
            try:
                settings = load_gemini_settings()
                spinner_message = (
                    "جارٍ إعداد تقرير المقابلة..."
                    if language == "ar"
                    else "Preparing your interview report..."
                )
                with st.spinner(spinner_message):
                    report = generate_interview_report(
                        settings,
                        st.session_state.cv_text,
                        st.session_state.job_title,
                        st.session_state.interview_messages,
                        language=language,
                    )
            except (GeminiConfigurationError, GeminiServiceError) as exc:
                st.session_state.report_error = str(exc)
            else:
                st.session_state.report = report

        if st.session_state.report_error is not None:
            st.error(
                _display_text(
                    localize_interview_error(
                        st.session_state.report_error,
                        language,
                    ),
                    language,
                )
            )
            retry_label = "حاول مرة أخرى" if language == "ar" else "Try again"
            if st.button(retry_label, key="retry_report_request"):
                st.session_state.report_error = None
                st.rerun()
        else:
            render_report(
                st.session_state.report,
                st.session_state.job_title,
                language=language,
            )

        new_interview_label = (
            "ابدأ مقابلة جديدة" if language == "ar" else "Start a new interview"
        )
        st.button(
            new_interview_label,
            on_click=restart_interview,
            key="start_new_interview",
        )


def main() -> None:
    selected_language = st.session_state.get("interview_language")
    if selected_language is None:
        selected_language = (
            "ar" if st.session_state.get("language_choice") == "العربية" else "en"
        )
    page_title = (
        "مقابلة عمل تجريبية"
        if selected_language == "ar"
        else "AI Mock Interview"
    )
    st.set_page_config(page_title=page_title, layout="centered")
    inject_theme_styles()
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
        "report": None,
        "report_error": None,
        "chat_scroll_pending": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "scroll_to_top_pending" not in st.session_state:
        st.session_state.scroll_to_top_pending = False

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
    elif st.session_state.phase == "interview":
        render_interview_screen()
    else:
        render_report_screen()
    scroll_to_top_if_pending()


if __name__ == "__main__":
    main()
