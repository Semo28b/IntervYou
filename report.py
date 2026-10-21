import json
import math
from dataclasses import dataclass
from typing import Any

import streamlit as st


class InvalidReportError(ValueError):
    pass


@dataclass(frozen=True)
class QuestionScore:
    question_number: int
    score: float
    reason: str


@dataclass(frozen=True)
class CVJobFit:
    strengths: list[str]
    gaps: list[str]
    clear_mismatch: bool


@dataclass(frozen=True)
class InterviewReport:
    candidate_name: str
    overall_score: float
    overall_reason: str
    question_scores: list[QuestionScore]
    strengths: list[str]
    areas_to_improve: list[str]
    cv_job_fit: CVJobFit
    cv_suggestions: list[str]


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidReportError(f"{field} must be non-empty text.")
    return value.strip()


def _text_list(value: Any, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise InvalidReportError(f"{field} must be a non-empty list of text.")
    return [
        _required_text(item, f"{field}[{index}]")
        for index, item in enumerate(value)
    ]


def _score(value: Any, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 10
    ):
        raise InvalidReportError(f"{field} must be a number from 0 to 10.")
    return float(value)


def parse_report_response(response_text: str) -> InterviewReport:
    try:
        data = json.loads(response_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidReportError("The report response is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise InvalidReportError("The report response must be an object.")

    if "candidate_name" not in data:
        raise InvalidReportError("candidate_name is required.")
    candidate_name = data["candidate_name"]
    if candidate_name is not None and not isinstance(candidate_name, str):
        raise InvalidReportError("candidate_name must be text or null.")
    candidate_name = candidate_name.strip() if candidate_name else "Candidate"
    if not candidate_name:
        candidate_name = "Candidate"

    overall_score = _score(data.get("overall_score"), "overall_score")
    overall_reason = _required_text(data.get("overall_reason"), "overall_reason")

    raw_scores = data.get("question_scores")
    if not isinstance(raw_scores, list) or len(raw_scores) != 5:
        raise InvalidReportError("question_scores must contain exactly five entries.")

    question_scores = []
    for item in raw_scores:
        if not isinstance(item, dict):
            raise InvalidReportError("Each question score must be an object.")
        question_number = item.get("question_number")
        if (
            isinstance(question_number, bool)
            or not isinstance(question_number, int)
            or question_number not in range(1, 6)
        ):
            raise InvalidReportError(
                "Each question score must have a question number from 1 to 5."
            )
        question_scores.append(
            QuestionScore(
                question_number=question_number,
                score=_score(item.get("score"), "question score"),
                reason=_required_text(item.get("reason"), "question reason"),
            )
        )

    if {item.question_number for item in question_scores} != {1, 2, 3, 4, 5}:
        raise InvalidReportError(
            "Question scores must include each main question exactly once."
        )
    question_scores.sort(key=lambda item: item.question_number)

    strengths = _text_list(data.get("strengths"), "strengths")
    areas_to_improve = _text_list(data.get("areas_to_improve"), "areas_to_improve")

    raw_fit = data.get("cv_job_fit")
    if not isinstance(raw_fit, dict):
        raise InvalidReportError("cv_job_fit must be an object.")
    clear_mismatch = raw_fit.get("clear_mismatch")
    if not isinstance(clear_mismatch, bool):
        raise InvalidReportError("cv_job_fit.clear_mismatch must be true or false.")
    cv_job_fit = CVJobFit(
        strengths=_text_list(
            raw_fit.get("strengths"),
            "cv_job_fit.strengths",
            allow_empty=True,
        ),
        gaps=_text_list(raw_fit.get("gaps"), "cv_job_fit.gaps", allow_empty=True),
        clear_mismatch=clear_mismatch,
    )

    cv_suggestions = _text_list(data.get("cv_suggestions"), "cv_suggestions")
    if len(cv_suggestions) != 3:
        raise InvalidReportError("cv_suggestions must contain exactly three entries.")

    return InterviewReport(
        candidate_name=candidate_name,
        overall_score=overall_score,
        overall_reason=overall_reason,
        question_scores=question_scores,
        strengths=strengths,
        areas_to_improve=areas_to_improve,
        cv_job_fit=cv_job_fit,
        cv_suggestions=cv_suggestions,
    )


def _render_text_list(items: list[str]) -> None:
    if not items:
        st.write("None identified.")
        return
    for item in items:
        st.markdown(f"- {item}")


def render_report(report: InterviewReport, job_title: str) -> None:
    with st.container(border=True):
        st.title("Interview Report")
        st.subheader(report.candidate_name)
        st.write(job_title)

        st.subheader("Overall score")
        st.metric("Score", f"{report.overall_score:g} / 10")
        st.write(
            f"Based on your interview, your score is "
            f"{report.overall_score:g} out of 10."
        )
        st.write(report.overall_reason)

        st.subheader("Question scores")
        for item in report.question_scores:
            st.markdown(f"**Question {item.question_number}: {item.score:g} / 10**")
            st.write(item.reason)

        st.subheader("Strengths")
        _render_text_list(report.strengths)

        st.subheader("Areas to improve")
        _render_text_list(report.areas_to_improve)

        st.subheader("CV–job fit")
        if report.cv_job_fit.clear_mismatch:
            st.warning("Your CV is a clear mismatch for this job.")
        st.markdown("**Relevant strengths**")
        _render_text_list(report.cv_job_fit.strengths)
        st.markdown("**Gaps**")
        _render_text_list(report.cv_job_fit.gaps)

        st.subheader("CV suggestions")
        for index, suggestion in enumerate(report.cv_suggestions, start=1):
            st.write(f"{index}. {suggestion}")
