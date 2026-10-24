---
doc: scope
status: approved
---

# AI Mock Interview

A small web app where a job seeker uploads a CV, enters a job title, and sits a serious AI interview — then gets an honest report on their answers and CV–job fit.

## The Unique Kernel
It stays in character as a professional, polite HR interviewer: one question at a time, questions drawn from **this CV and this job** (not generic), follow-ups when an answer is vague, links to what the candidate already said, and **no feedback until the end**. The payoff is an honest report — scores with reasons, strengths and gaps, and three concrete CV fixes — not praise. If the CV clearly does not match the job, the report says so plainly.

## Who It's For
A fresh graduate or job seeker preparing for a real interview or co-op training. Today they guess whether they fit the job and what to add to their CV. First user in mind: the learner, after university or when applying for co-op.

## The Core Loop
Open the app → upload a PDF CV and type a job title → Start interview → answer 5 questions one by one (with at most two follow-ups if an answer is too general) → read the report → Restart if they want to try another CV or job.

## Inspiration & Identity
Tone of a real-world HR interview: professional, serious, polite, and respectful. Honest and specific. No generic praise. The interface, interview, answers, and report are English-only for this proof of concept.

## Why This Matters to the Learner
They want to know how interviews will feel after university, whether they fit a job, and what to add to their CV to be a stronger candidate. They also want practice building with an AI coding agent.

## What "Working" Looks Like
Someone opens the app locally and sees a simple start screen: upload CV (PDF), type a job title with at least two English or Arabic letters, and click **Start interview**. Spaces and `- / + & . , ( ) '` are allowed; digits and other symbols are not. Extra spaces are trimmed, and a title with no letters or only repeated copies of one letter is rejected. An invalid non-empty title or unreadable PDF shows a clear error and the interview does not start; a blank title keeps Start disabled. The interview screen shows one question; they type and submit. Vague answers get a follow-up such as “Can you give me a specific example?” or “What exactly was your role?” — at most two follow-ups per question. After the last question, the interviewer clearly says the interview is finished. A **report screen** shows exactly five scores out of 10, one per main question with any follow-up answers considered together, CV–job fit (strengths and gaps), and 3 concrete CV suggestions. If the CV clearly does not match the job, the report says that plainly. That report is the demo-video moment. A **Restart** button returns to the start screen. The app sends CV text and answers to Google Gemini but does not save them. Deployment is optional.

## The POC Boundary
- One flow, English-only interface, interview, answers, and report; after submission, reject answers with fewer than three words or no English letter (A–Z), show a short message, and do not send them to Gemini
- PDF CV + job title on a start screen
- Clear error if the PDF text cannot be read or a non-empty job title has fewer than two English or Arabic letters, contains only repetitions of one letter, or uses anything beyond letters, spaces, and `- / + & . , ( ) '` — interview does not start; a blank title stays disabled
- 5 main questions, one at a time, stay in interviewer role until the end
- Follow-ups only when the answer is too general; at most two per question, then move on
- End report: exactly five scores /10 (one per main question, including its follow-up answers) + short reasons, CV–job strengths and gaps, 3 CV suggestions; say plainly if the CV clearly does not match the job; screen only, no PDF download
- Restart button
- The app does not save CVs, answers, chat, or reports; CV text and answers are sent to Google Gemini
- Runs locally
- Plan a `sample_cvs` folder for fake PDFs (different fields, experience levels, including a weak CV) for testing and the demo — do not block the build on those files

## Later
- Deploying to the internet
- Other languages (Arabic or mixed) for the interface and the interview
- Adding the prepared sample CV PDFs into `sample_cvs` when they are ready
- PDF download of the report

## Explicitly Cut
- **Accounts / login** — not needed to prove one interview
- **Voice or video interview** — would blow the time box; typing is enough
- **Saving CVs or interview history** — CVs are not saved; restart is enough for the demo
- **A large public question bank** — questions must come from the uploaded CV and this job
- **Feedback during the interview** — breaks the “stay in role” kernel

## Post-build changes
- Start checks extracted PDF text locally before validating the job title or calling Gemini. The offline keyword heuristic requires contact details plus at least two CV sections, or structured work-history and education sections; it is free and unaffected by Gemini outages, but may miss unusual CV formats or accept similar documents.
- The start card now has more top/bottom breathing room and a narrower centered width.
- The five main questions now follow a fixed interview shape: role-interest warm-up, two CV-specific questions, a company/team contribution question, and a deeper behavioral question.
- Gemini overloads (429, 503, or a high-demand response) are retried twice after short waits; the current model is reused, and no fallback model is configured.

## Arabic mode
- English remains the default. Candidates may optionally choose Arabic for the interview; interviewer messages and report text use simple, professional Modern Standard Arabic, and the interview/report areas use right-to-left layout.
- Arabic CVs and answers are supported. Answers still require at least three words and at least one English or Arabic letter; validation feedback uses the selected language.
- Extracted PDF text is Unicode-normalized before use so Arabic presentation forms work with the local CV check. Scanned PDFs remain unsupported without OCR.
