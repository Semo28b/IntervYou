---
doc: prd
status: approved
---

# AI Mock Interview — Product Requirements

A small English-only practice interview for a fresh graduate or job seeker (including co-op training): upload an English-language CV, enter a job title, sit a serious English-language HR-style chat, then see an honest English-language on-screen report.
Source: `scope.md > Who It's For`, `scope.md > The Unique Kernel`, `scope.md > The Core Loop`.

## The Core Journey

1. Open the app locally. See a calm start screen: centered card, upload a PDF CV, type a job title, **Start interview** (disabled until a CV is uploaded and the job title contains at least one English letter and only English letters and spaces). Note: "Your CV and answers are sent to Google Gemini. Not saved by this app."
2. A non-empty invalid job title shows a clear error under the field and keeps Start disabled. The job title may contain only English letters (A–Z) and spaces. An empty title stays disabled without an error. If the PDF text cannot be read, show a friendly error under the upload field. The interview does not begin in either case.
3. If both are valid, move to a full-page chat. The interviewer greets the candidate for this job, says it will ask a few questions, then asks question 1 immediately.
4. The candidate types and submits answers. If a submitted answer has fewer than three words or no English letter (A–Z), show a short message in the chat and do not send it to Gemini. Valid answers progress through questions that deepen: 1 is a light warm-up; 2–3 use specific CV details; 4–5 are deeper behavioral or challenging questions for this job. Vague or off-topic answers get at most two follow-ups, then the interviewer moves on. No scores or detailed feedback in the chat.
5. After the last answer, the interviewer says a short polite goodbye (thanks them and says the interview is finished). The text box is disabled with the placeholder **The interview has ended**. A **View my report** button appears in the chat.
6. The report screen shows name (or "Candidate"), job title, overall score with explanation, exactly five scores out of 10 (one per main question, considering that answer together with its follow-ups), strengths, areas to improve, CV–job fit (plain mismatch if needed), and three CV suggestions. Follow-up answers do not get separate scores.
7. **Start a new interview** returns to the start screen. Nothing from the previous CV or chat is kept.
Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`.

## Screens and Layout

Three surfaces only, same visual language.

### Start screen
A single centered card, top to bottom, lots of white space, no sidebar.
1. Small pill label **AI Mock Interview**, headline **Ready to practice your next interview?**, one short line: "Upload your CV, tell us the job you're aiming for, and we'll run a realistic interview, then show you how you did."
2. CV upload box labeled **Upload your CV (PDF)** — PDF only. After upload: file name + "PDF uploaded" + **Replace**.
3. Job title text box labeled **Job title you're applying for**, placeholder example **Marketing Specialist**. Rounded input, thin light border.
4. Prominent **Start interview** button, disabled until a CV is uploaded and the job title contains only English letters (A–Z) and spaces, with at least one letter.
5. Small note under the button: **Your CV and answers are sent to Google Gemini. Not saved by this app.**
6. Errors appear directly under the field that has the problem.

### Interview screen
Full-page chatbot, no card around it, no header, no progress bar, no question counter.
1. Conversation fills the window in a comfortable centered reading column. Interviewer bubbles on the left, candidate on the right; soft rounded bubbles; scrolls as the chat grows.
2. Text box + **Send** fixed at the bottom. Enter submits; Shift+Enter adds a new line. After submission, invalid answers show a short message and are not sent to Gemini.
3. Typing indicator while the interviewer is thinking; **Send** disabled then so a second message cannot be sent.
4. After the closing goodbye, the text box is disabled with placeholder **The interview has ended**. **View my report** appears in the chat.

### Report screen
Same colors and rounded layout as the other screens. The report is shown on screen only.
- Top: candidate name from the CV (or **Candidate** if none) and the job title.
- Then the report sections in the order below.
- Bottom: **Start a new interview**.

Source: `scope.md > What "Working" Looks Like`.

## Look and Feel

Light, calm, approachable, still professional.
- Warm off-white page background, white card on the start (and matching rounded report layout).
- Soft pastel accents: light yellow for the label pill and the upload box; light mint green **Start interview** button with dark green text.
- Dark green-gray text.
- Simple rounded fields, thin light borders.
- No blue, decorative emojis, bright or heavy colors, or clutter. Use a professional recruiter emoji and a person-silhouette candidate avatar.
- UI can feel a little friendly; the interviewer voice stays serious, polite, and professional like real HR.
- Interview and report keep the same colors, fonts, and simple layout (interview is full-page chat without a surrounding card). Candidate chat bubbles are soft light green; interviewer bubbles are soft light gray; the send and report buttons match the candidate-bubble green.

## Features and Behavior

Source: `scope.md > The Unique Kernel`, `scope.md > The POC Boundary`.

### Start interview
- PDF only. After a successful upload, show the file name and "PDF uploaded", with **Replace**.
- **Start interview** stays disabled until a CV file is present and the job title contains at least one English letter and only English letters (A–Z) and spaces.
- A non-empty invalid job title (including one with only spaces, digits, punctuation, or non-English letters) shows **Please use English letters (A-Z) and spaces only.** under the field while Start remains disabled. An empty field does not show this error.
- Unreadable PDF (no usable text): friendly error under the upload area; do not start.
- CVs are not saved. No extra name field on the start screen.

### Interviewer in character
- Professional, serious, polite, respectful. English only.
- Stay in the interviewer role until the interview is finished. No scores, praise, or coaching in the chat.
- Welcome, then five main questions:
  - **Q1** — light warm-up (e.g. about yourself and interest in this role).
  - **Q2–Q3** — based on specific experiences or skills in this CV, not generic public questions.
  - **Q4–Q5** — deeper behavioral or challenging questions matched to this job title and typical requirements (e.g. "Tell me about a time...").
- One question at a time. Tie later questions to earlier answers when relevant.
- Follow-ups: at most two per main question, then move on.
  - If the answer is too general: ask for a specific example or what their role was.
  - If the answer is off-topic, does not address the question, or is random text: politely say so and restate the question (this uses a follow-up slot). If it is still off-topic after the follow-up limit, move to the next question.
- After the last answer: short polite goodbye (thanks them; says the interview is finished). Text box disabled with placeholder **The interview has ended**. Then **View my report**.

### Sending answers
- When an answer is submitted, validate it has at least one English letter (A–Z) and at least **3 words**. If either condition fails, show the short message **Please use at least 3 words with English letters (A–Z).** and do not send the answer to Gemini or add it to the accepted interview transcript. The candidate can edit and submit again. Arabic answers are out of scope.
- While the interviewer is thinking: typing indicator; **Send** disabled.

### Report
Shown only after **View my report**. Tone: honest, specific, respectful; no generic praise. Practice estimate, not a prediction of a real interview.
1. Overall score: "Based on your interview, your score is X out of 10," judged on clarity, specific examples, relevance to the job, and structure of answers, plus a short explanation why.
2. Exactly five scores out of 10, one for each main question, with a short reason. Each score judges the main answer together with its follow-up answers; do not create separate follow-up scores. Off-topic or random answers get a low score with that reason stated.
3. Strengths — what they did well, with specific references to answers or CV.
4. Areas to improve — weak points in answers, each with a clear specific explanation.
5. CV–job fit — strengths and gaps. If the CV clearly does not match the job, say so plainly.
6. Three concrete suggestions to improve the CV.

If the CV has no name, the heading is **Candidate**. Never invent a name.

### Restart
**Start a new interview** returns to the start screen. Previous CV, chat, and report are gone.

### Failures during the interview
If an AI request fails, show a short friendly error in the chat with **Try again**. Do not freeze.

## States and Boundaries

- **First open** — start screen, empty upload, empty job title, Start disabled, note: "Your CV and answers are sent to Google Gemini. Not saved by this app."
- **Ready to start** — PDF uploaded (name shown) and job title contains at least one English letter and only English letters and spaces; Start enabled.
- **Start error** — unreadable PDF or non-empty job title containing digits, punctuation, non-English letters, or only spaces; show an error under the affected field and stay on start.
- **Interview in progress** — full-page chat; one unanswered interviewer question (or follow-up) at a time; Send rules as above.
- **Interviewer thinking** — typing indicator; Send disabled.
- **Interview failed request** — friendly error + Try again.
- **Interview finished** — goodbye in chat; text box disabled with placeholder "The interview has ended"; View my report visible; no scores in chat.
- **Report** — full report on screen as specified.
- **Nothing persists** — the app does not save CVs, answers, chat, or reports; closing the app or starting a new interview discards the session. CV text and answers are sent to Google Gemini as stated in the start-screen note. No accounts.
- **Name** — from the CV if present; otherwise the literal word Candidate.

## Product Decisions

- Project name / pill label **AI Mock Interview** — used on the start screen.
- Three screens: start card, full-page chat, on-screen report.
- Friendly, light UI; serious interviewer — so it feels approachable without breaking the HR kernel.
- Scores and detailed feedback only on the report, after View my report — stay in character during the chat.
- Five questions with a deepening shape (warm-up, CV-based, behavioral).
- At most two follow-ups per question, including restating when off-topic.
- Invalid submitted answers (fewer than 3 words or no English letter A–Z) show the short validation message and are not sent to Gemini.
- No name field; missing name → "Candidate".
- CVs not saved; no history.
- English only for the interface, interview, answers, and report; Arabic is out of scope.
- Local run is enough; deployment optional.

## What We're Building

The one local flow above: start → five-question English interview with limited follow-ups → on-screen report → restart. Clear start errors, chat send rules, typing/disable while thinking, Try again on AI failure, and a report that can say a CV does not match the job. A `sample_cvs` folder is planned for later fake PDFs; the build must not wait on those files.

## Deferred From the POC

- **Putting the app on the internet** — optional; local demo is enough (`scope.md > Later`).
- **Other languages** — English only for now (`scope.md > Later`).
- **Sample CV PDFs in `sample_cvs`** — add when ready; do not block the build (`scope.md > Later`).
- **PDF download of the report** — the report is on screen only for now (`scope.md > Later`).

## Possible Later Enhancements

- Arabic or mixed-language interview and UI.
- Deploy so others can open a link.
- Drop prepared sample CVs into `sample_cvs` for testing and the demo video.
- Download the report as a PDF.

## Non-Goals

- Accounts / login — not needed for one practice run.
- Voice or video — typing is enough.
- Saving CVs or interview history.
- A large public question bank — questions come from this CV and this job.
- Feedback or scores during the interview.
- Inventing a candidate name or adding a name field.
- Blue generic AI-app styling, decorative emojis, cluttered chrome, progress bars, or question counters.

## Open Questions

None. Accepted answers need at least 3 words and one English letter (A–Z); invalid submissions show the validation message and are not sent to Gemini.
