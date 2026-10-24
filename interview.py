import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, MutableMapping, TypedDict


ANSWER_VALIDATION_MESSAGE = (
    "Please use at least 3 words with English letters (A–Z)."
)
ARABIC_ANSWER_VALIDATION_MESSAGE = (
    "يرجى كتابة ثلاث كلمات على الأقل باستخدام حروف عربية أو إنجليزية."
)
JOB_TITLE_VALIDATION_MESSAGE = (
    "Please use English letters (A-Z) and spaces only."
)
MAX_MAIN_QUESTIONS = 5
MAX_FOLLOW_UPS = 2


class InterviewMessage(TypedDict):
    role: Literal["assistant", "user"]
    text: str


@dataclass(frozen=True)
class InterviewTurn:
    action: str
    text: str


@dataclass(frozen=True)
class InterviewProgress:
    question_number: int
    follow_up_count: int
    finished: bool = False


class InvalidInterviewTurnError(ValueError):
    pass


def validate_job_title(job_title: str) -> bool:
    return (
        bool(job_title.strip())
        and re.fullmatch(r"[A-Za-z ]+", job_title) is not None
    )


def validate_answer(answer: str, language: str = "en") -> bool:
    has_english_letter = re.search(r"[A-Za-z]", answer) is not None
    has_arabic_letter = language == "ar" and any(
        unicodedata.category(character).startswith("L")
        and "ARABIC" in unicodedata.name(character, "")
        for character in answer
    )
    return len(answer.split()) >= 3 and (has_english_letter or has_arabic_letter)


def answer_validation_message(language: str = "en") -> str:
    return (
        ARABIC_ANSWER_VALIDATION_MESSAGE
        if language == "ar"
        else ANSWER_VALIDATION_MESSAGE
    )


def allowed_interviewer_actions(
    question_number: int,
    follow_up_count: int,
) -> tuple[str, ...]:
    if not 1 <= question_number <= MAX_MAIN_QUESTIONS:
        raise ValueError("The main question number must be between 1 and 5.")
    if not 0 <= follow_up_count <= MAX_FOLLOW_UPS:
        raise ValueError("The follow-up count must be between 0 and 2.")

    actions = []
    if follow_up_count < MAX_FOLLOW_UPS:
        actions.append("follow_up")
    if question_number < MAX_MAIN_QUESTIONS:
        actions.append("question")
    else:
        actions.append("finish")
    return tuple(actions)


def parse_interview_turn(response_text: str) -> InterviewTurn:
    try:
        result = json.loads(response_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidInterviewTurnError(
            "The interviewer returned invalid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise InvalidInterviewTurnError("The interviewer response must be an object.")

    action = result.get("action")
    text = result.get("text")
    if not isinstance(action, str) or not isinstance(text, str) or not text.strip():
        raise InvalidInterviewTurnError(
            "The interviewer response needs an action and non-empty text."
        )
    return InterviewTurn(action=action, text=text.strip())


def queue_candidate_answer(
    answer: str,
    messages: list[InterviewMessage],
    language: str = "en",
) -> bool:
    if not validate_answer(answer, language):
        return False
    messages.append({"role": "user", "text": answer})
    return True


def record_interviewer_turn(
    messages: list[InterviewMessage],
    turn: InterviewTurn,
    question_number: int,
    follow_up_count: int,
) -> InterviewProgress:
    allowed_actions = allowed_interviewer_actions(
        question_number,
        follow_up_count,
    )
    if turn.action not in allowed_actions:
        raise InvalidInterviewTurnError(
            "The interviewer returned an action that is not allowed at this point."
        )

    if turn.action == "follow_up":
        progress = InterviewProgress(question_number, follow_up_count + 1)
    elif turn.action == "question":
        progress = InterviewProgress(question_number + 1, 0)
    else:
        progress = InterviewProgress(question_number, follow_up_count, finished=True)

    messages.append({"role": "assistant", "text": turn.text})
    return progress


def clear_session_state(state: MutableMapping[str, object]) -> None:
    for key in list(state.keys()):
        del state[key]
