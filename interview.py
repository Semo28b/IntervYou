import re


ANSWER_VALIDATION_MESSAGE = (
    "Please use at least 3 words with English letters (A–Z)."
)


def validate_job_title(job_title: str) -> bool:
    return bool(job_title.strip())


def validate_answer(answer: str) -> bool:
    return len(answer.split()) >= 3 and re.search(r"[A-Za-z]", answer) is not None
