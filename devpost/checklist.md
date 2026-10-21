---
doc: checklist
status: approved
---

# Build Checklist

Build mode: learn

## Slices

- [x] **1. Start an interview from a CV**
  Becomes usable: The local app shows a simple functional start screen, validates the PDF and job title, extracts readable CV text, and asks a Gemini question grounded in that CV and job.
  Why now: Bootstrapping stays inside the first usable behavior, and this proves the central CV-specific interviewer plus the unfamiliar Gemini connection before building the longer flow.
  PRD ref: `prd.md > The Core Journey` (steps 1–3), `prd.md > Screens and Layout > Start screen`, `prd.md > Features and Behavior > Start interview`, `prd.md > Features and Behavior > Interviewer in character`
  Spec ref: `spec.md > Stack`, `spec.md > Where It Runs and How Someone Tries It`, `spec.md > Components > Streamlit app and screens`, `spec.md > Components > PDF text extraction`, `spec.md > Components > Gemini client and prompts`, `spec.md > Important Failure Modes`
  Build: Add the local Streamlit entry point, dependency list, and secrets example; add `.streamlit/secrets.toml` to `.gitignore` before any real key is used. Add the MIT `LICENSE` and concise run instructions. Build a simple, functional start screen with PDF/job validation, local text extraction, Gemini welcome/first question, and clear missing-key/unreadable-PDF messages. Keep both interview and report model settings in local secrets, initially pointing to a Flash model; defer visual theme and styling to slice 3.
  Verify (mechanical): Run `python --version` and confirm 3.11 or newer; install from `requirements.txt`; run `python -m unittest discover -s tests -v`; start with `python -m streamlit run app.py` and confirm the server starts. Unit tests use a mocked Gemini response so they need no API key.
  Learner check: Open the local app, try the empty start screen and a fake English CV with a job title, then see whether the first question feels specific to that CV and job. Add your API key only to the local secrets file; never share it in chat.
  Commit: `Build start screen and CV-grounded first question`

- [x] **2. Complete the five-question interview**
  Becomes usable: The candidate can answer in the chat, get relevant follow-ups (no more than two per main question), complete all five main questions, and reach the polite closing message.
  Why now: It extends the already-working CV-specific question through the product's unique kernel, while validating the conversation limits and failed-request behavior before building the final report.
  PRD ref: `prd.md > The Core Journey` (steps 4–5), `prd.md > Features and Behavior > Interviewer in character`, `prd.md > Features and Behavior > Sending answers`, `prd.md > Features and Behavior > Failures during the interview`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Components > Streamlit app and screens`, `spec.md > Components > Interview flow and limits`, `spec.md > Components > Gemini client and prompts`, `spec.md > Data Model`, `spec.md > Important Failure Modes`
  Build: Add the functional full-page chat and temporary conversation state without final visual styling. Validate submitted answers after submission; show the specified short message and do not send or accept invalid answers. Track five main questions and enforce the two-follow-up cap in Python. Keep the interviewer in role, preserve context on a failed Gemini request, support retry without duplicating an answer, and disable further submission while thinking or after completion.
  Verify (mechanical): Run `python -m unittest discover -s tests -v`; cover valid/invalid submissions, that invalid answers never reach the Gemini client, question/follow-up limits, and retry without duplicate transcript entries. Start the app and confirm it remains runnable.
  Learner check: Use a fake CV and job, try an answer with fewer than three words and one without an A–Z letter, then submit valid answers and confirm the interviewer stays in role and limits follow-ups.
  Commit: `Build five-question interview chat`

- [x] **3. Read the report and start again**
  Becomes usable: After the interview, the user can view the on-screen report with exactly five main-question scores (each considering its follow-ups), CV–job assessment and three suggestions, then restart with the previous session cleared.
  Why now: The report depends on the complete transcript; keeping it last makes the demo payoff a true end-to-end result and verifies the independently configurable report model.
  PRD ref: `prd.md > The Core Journey` (steps 5–7), `prd.md > Screens and Layout > Report screen`, `prd.md > Features and Behavior > Report`, `prd.md > Features and Behavior > Restart`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Components > Gemini client and prompts`, `spec.md > Components > Report presentation`, `spec.md > Data Model`, `spec.md > External Services and Dependencies`, `spec.md > Look and Feel`
  Build: First implement and test the structured report using `GEMINI_REPORT_MODEL` separately from `GEMINI_INTERVIEW_MODEL`, then add report retry and restart clearing session data. After all features work, apply the agreed visual theme and styling consistently across the start, interview, and report screens.
  Verify (mechanical): Run `python -m unittest discover -s tests -v`; test report shape, five score entries, score ranges, exactly three suggestions, and restart clearing state with mocked Gemini responses. Start the app and complete a smoke test of the full flow with a fake CV and configured test key.
  Learner check: Complete the flow with a fake CV, review whether the five question scores account for follow-ups, check the CV fit and suggestions, then restart and confirm the previous interview is gone.
  Commit: `Build report and restart flow`

## Hands-on Checkpoints

- [x] Early usable behavior explored — after slice 1, try the first CV-grounded question and share what feels right or needs adjustment.
- [x] Final kick-the-tires exploration and feedback completed — learner completed the fake-CV report/restart flow and reviewed the final chat styling.

## Final Review

- [x] Final review complete — feedback resolved; learner confirmed the final UI looks right and all tests pass.

## Code Tour and App Map

- [x] Learning activity complete — brief evidence-based recap connected a visible interview action to its code and tests
- [x] Optional edit and transfer reflection addressed — optional edit declined; transfer reflection answered and kept in the ignored learner profile
- [x] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: Slice 1 implemented; all 10 unit tests pass. Started the local Streamlit app and verified a fake-CV test produced the first question. A minimal Gemini request also succeeded with the selected interview model. Slice 2 passed 19 unit tests and the learner check for invalid-answer rejection, follow-ups, and end-of-interview input disabling. The learner noted that vague answers sometimes advance without a follow-up; retain this as future prompt-tuning feedback. A requested title-validation correction now allows only English letters and spaces; 19 tests pass and the learner confirmed the UI behavior. Slice 3 added report generation, report retry, and restart; all 27 unit tests pass. The learner completed a fake-CV report/restart check, then confirmed the final avatar and chat colors looked right. The local API key stays in the ignored secrets file.
Route and stops: Reference route only (not editor navigation): `app.py > render_interview_screen()` and `process_pending_answer()` → `interview.py > queue_candidate_answer()` and `record_interviewer_turn()` → `gemini_service.py > generate_interview_turn()`; report path: `gemini_service.py > generate_interview_report()` → `report.py > parse_report_response()` and `render_report()`.
Edit outcome: No wrap-up code edit made; learner declined the optional label change; preserve the approved visual design.
Reflection: Transfer reflection answered; personal wording is recorded only in the ignored learner profile.
Activity mode: Brief, evidence-based recap and static source route; learner already tested the running full flow. App map opened locally and read; it is a reference guide, not a claim of interactive editor navigation.

## Revisions
- Refined the final interview visuals from browser feedback: added a person-silhouette candidate avatar, soft gray interviewer bubbles, and a matching light-green report button. The learner confirmed the result; no behavior or stack changed.
