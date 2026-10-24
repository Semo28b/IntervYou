from html import escape
import json
import math
from dataclasses import dataclass
from textwrap import dedent
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


def _render_text_list(items: list[str], empty_message: str) -> None:
    if not items:
        st.write(empty_message)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_report(
    report: InterviewReport,
    job_title: str,
    language: str = "en",
) -> None:
    if language == "ar":
        _render_arabic_report(report, job_title)
        return

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
        _render_text_list(report.strengths, "None identified.")

        st.subheader("Areas to improve")
        _render_text_list(report.areas_to_improve, "None identified.")

        st.subheader("CV–job fit")
        if report.cv_job_fit.clear_mismatch:
            st.warning("Your CV is a clear mismatch for this job.")
        st.markdown("**Relevant strengths**")
        _render_text_list(report.cv_job_fit.strengths, "None identified.")
        st.markdown("**Gaps**")
        _render_text_list(report.cv_job_fit.gaps, "None identified.")

        st.subheader("CV suggestions")
        for index, suggestion in enumerate(report.cv_suggestions, start=1):
            st.write(f"{index}. {suggestion}")


def _render_arabic_report(report: InterviewReport, job_title: str) -> None:
    candidate_name = (
        "المرشح" if report.candidate_name == "Candidate" else report.candidate_name
    )
    question_scores = "".join(
        "<li>"
        f"<strong>السؤال {item.question_number}: {item.score:g} / 10</strong>"
        f"<p>{escape(item.reason)}</p>"
        "</li>"
        for item in report.question_scores
    )
    mismatch_notice = (
        '<div role="alert" style="background:#FFF1C4; padding:0.8rem 1rem; '
        'border-radius:0.75rem; margin:0.5rem 0 1rem;">'
        "السيرة الذاتية لا تتوافق بوضوح مع هذه الوظيفة."
        "</div>"
        if report.cv_job_fit.clear_mismatch
        else ""
    )

    with st.container(border=True):
        st.markdown(
            dedent(
                f"""
        <div dir="rtl" style="text-align:right;">
          <h1>تقرير المقابلة</h1>
          <h3>{escape(candidate_name)}</h3>
          <p>{escape(job_title)}</p>

          <h2>النتيجة الإجمالية</h2>
          <p><strong>النتيجة: {report.overall_score:g} / 10</strong></p>
          <p>بناءً على المقابلة، نتيجتك هي {report.overall_score:g} من 10.</p>
          <p>{escape(report.overall_reason)}</p>

          <h2>نتائج الأسئلة</h2>
          <ol dir="rtl" style="text-align:right; padding-right:1.5rem; padding-left:0;">
            {question_scores}
          </ol>

          <h2>نقاط القوة</h2>
          {_render_html_list(report.strengths, "لا توجد نقاط محددة.")}

          <h2>مجالات التحسين</h2>
          {_render_html_list(report.areas_to_improve, "لا توجد نقاط محددة.")}

          <h2>مدى توافق السيرة الذاتية مع الوظيفة</h2>
          {mismatch_notice}
          <h3>نقاط القوة ذات الصلة</h3>
          {_render_html_list(report.cv_job_fit.strengths, "لا توجد نقاط محددة.")}
          <h3>الفجوات</h3>
          {_render_html_list(report.cv_job_fit.gaps, "لا توجد فجوات محددة.")}

          <h2>اقتراحات لتحسين السيرة الذاتية</h2>
          {_render_html_list(
              report.cv_suggestions,
              "لا توجد اقتراحات محددة.",
              ordered=True,
          )}
        </div>
                """
            ),
            unsafe_allow_html=True,
        )


def _render_html_list(
    items: list[str],
    empty_message: str,
    ordered: bool = False,
) -> str:
    if not items:
        return f"<p>{escape(empty_message)}</p>"
    tag = "ol" if ordered else "ul"
    rows = "".join(f"<li>{escape(item)}</li>" for item in items)
    return (
        f'<{tag} dir="rtl" style="text-align:right; '
        f'padding-right:1.5rem; padding-left:0;">'
        f"{rows}</{tag}>"
    )
