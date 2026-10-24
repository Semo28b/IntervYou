---
doc: spec
status: approved
---

# AI Mock Interview — Technical Spec

## How This Works, In Plain Language

Streamlit runs the app on your computer and shows its screens in a browser. When you upload a CV, Python reads the text from the PDF on your computer. The app does not upload the PDF file itself, but it sends the readable CV text to Google Gemini along with the job title and interview conversation when it needs a question, follow-up, or report. That text can include a candidate's name and contact details if they are on the CV. The interface, interviewer, answers, and report are English-only; answers must contain at least one English letter from A to Z.

The app keeps the CV text and conversation in temporary memory while the interview is open. It does not write them to a file or keep interview history. The Gemini key goes in a private local settings file, not in the code or public repository. There is no database, account, or separate server to set up.

This keeps the proof of concept to one local app and one AI service. The tradeoff is that Gemini is an outside service receiving interview data, and the app needs an internet connection and an API key to work. Use test CVs for the prototype.

## The Core Journey Through the System

PRD ref: `prd.md > The Core Journey`.

1. **Start:** `app.py` shows the PDF uploader and job-title field and the note **Your CV and answers are sent to Google Gemini. Not saved by this app.** Start stays disabled until a PDF is present. Job titles are NFKC-normalized, trimmed, and extra spaces collapse; the localized field-level error appears for an invalid non-empty title and after Start is clicked with an empty title.
2. **Read and check the CV:** `pdf_utils.py` extracts readable text locally with `pypdf`, then applies an offline CV heuristic before checking the job title or making any Gemini request. The heuristic requires contact details plus at least two CV sections, or structured work-history and education sections. Unreadable or non-CV documents show a localized error under the uploader and stay on the start screen. The local check is free and unaffected by Gemini outages, but may miss unusual CV formats or accept similar documents.
3. **Begin the interview:** `interview.py` stores the job title and extracted CV text in the active Streamlit session. `gemini_service.py` sends the text, title, and interviewer instructions to Gemini to get the welcome and first question. `app.py` shows the exchange in the chat.
4. **Answer and continue:** When the candidate submits an answer, `interview.py` checks it has at least three words and one English letter (A–Z). If invalid, `app.py` shows **Please use at least 3 words with English letters (A–Z).** and does not send or add the answer to the interview. Otherwise, the answer and conversation context go to Gemini, which proposes a follow-up or the next main question. Python tracks the five main questions and enforces no more than two follow-ups per question. While waiting for Gemini, the chat shows a thinking indicator and prevents another submission.
5. **Finish:** After question five, the interviewer gives a short goodbye. The input is disabled and **View my report** appears. When clicked, the app sends the CV text, job title, and full interview transcript to Gemini for the report.
6. **Report and restart:** `report.py` displays the returned report on screen. **Start a new interview** clears the current session data and returns to the start screen.

Transient Gemini overloads (429, 503, or high-demand responses) are retried twice after 2 and 5 seconds using the same configured model. If an interview request still fails, the app keeps the pending answer and context, shows a friendly localized message and **Try again**, and retries that same request rather than adding the answer twice. Report and opening requests also keep their inputs available for a manual retry. No fallback model is configured.

## Stack

- **Python 3.11 or newer** — the language for the app and PDF text extraction. Check the installed version during setup.
- **Streamlit** — runs the local browser app and provides upload, chat, button, and temporary per-session memory features. See [Streamlit documentation](https://docs.streamlit.io/).
- **Google Gen AI Python SDK (`google-genai`)** — calls the Gemini Developer API using a key from Google AI Studio. The interview and report use separate model settings so report quality can be upgraded independently. See the [SDK documentation](https://googleapis.github.io/python-genai/) and [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/get-started?lang=python).
- **pypdf** — extracts selectable text from uploaded PDFs locally. It does not add OCR for scanned/image-only documents. See [pypdf documentation](https://pypdf.readthedocs.io/en/stable/).
- **Python standard library `unittest`** — tests local interview rules without needing a live Gemini key.

Use a Gemini **Flash** model for responsive interview turns. Confirm the exact available model ID, Python SDK versions, current pricing, and account rate limits before wiring the live call; these details can change. No database or deployment platform is part of this POC.

## Where It Runs and How Someone Tries It

Run locally on a computer with Python 3.11 or newer, internet access, and a Gemini Developer API key from [Google AI Studio](https://aistudio.google.com/apikey). Run `python --version` and confirm it reports 3.11 or newer; the key and two model IDs are read from `.streamlit/secrets.toml`. `GEMINI_INTERVIEW_MODEL` selects the interview model and `GEMINI_REPORT_MODEL` independently selects the report model. They can initially use the same Flash model; change the report setting alone later if a stronger model is needed. Never paste the key into source code or commit it. The build must add `.streamlit/secrets.toml` to the existing `.gitignore` before a real key is created.

From the project folder in Windows PowerShell:

```powershell
python --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
# Add GEMINI_API_KEY, GEMINI_INTERVIEW_MODEL, and GEMINI_REPORT_MODEL to .streamlit\secrets.toml
python -m streamlit run app.py
```

Open **http://localhost:8501** in the browser. For the demo, use a fake/test CV, complete the five-question interview, show the report and its CV-fit assessment, then demonstrate **Start a new interview**. Record this local flow for the required short demo video. Submission also requires a public GitHub repository; deployment is optional and does not replace either deliverable.

## Look and Feel

Carry forward `prd.md > Look and Feel` and `scope.md > Inspiration & Identity`: calm, light, approachable, and professional; warm off-white page, white start/report surfaces, soft yellow label and upload accents, mint-green primary action, and dark green-gray text. Keep the start screen centered and uncluttered, and use a wide, readable chat column with interviewer and candidate messages on opposite sides. Use a professional recruiter emoji for the interviewer and a person-silhouette avatar for the candidate. Give candidate bubbles a soft light-green background and interviewer bubbles a soft light-gray background; the chat send and View my report buttons use the same light green as candidate bubbles. The interviewer remains serious, polite, and English-only. Use Streamlit's theme settings plus only small CSS adjustments if needed; no extra UI framework, blue palette, decorative emojis, progress bar, or question counter.

## Components

### Streamlit app and screens — `app.py`

Owns the start, interview, and report screens; input validation feedback; chat display; thinking/disabled states; and transitions between screens. Since Streamlit's chat input cannot be enabled or disabled based on the text being typed, validate after submission; show the short validation message and do not send or accept invalid text. Prevent new submissions while Gemini is processing and after the interview ends. Applies the visual direction using Streamlit theme settings and minimal CSS. Does not contain Gemini prompt construction or PDF parsing.

Implements `prd.md > The Core Journey`, `prd.md > Screens and Layout`, `prd.md > Start interview`, `prd.md > Sending answers`, `prd.md > Restart`, and `prd.md > States and Boundaries`.

### PDF text extraction — `pdf_utils.py`

Reads the uploaded PDF in local memory with `pypdf`, extracts and trims page text, and reports when no usable text is found. It does not save the uploaded file, send the PDF to Gemini, or perform OCR.

Implements `prd.md > Start interview` and `prd.md > Failures during the interview`.

### Interview flow and limits — `interview.py`

Checks answer eligibility, tracks the current main question and per-question follow-up count, creates the request context, and controls when the interview finishes. The Python code enforces five main questions and a hard maximum of two follow-ups per question even if Gemini suggests otherwise. Keeps a failed request retryable without duplicating the candidate's answer.

Implements `prd.md > Interviewer in character`, `prd.md > Sending answers`, `prd.md > Failures during the interview`, and `prd.md > States and Boundaries`.

### Gemini client and prompts — `gemini_service.py`

Creates the `google-genai` client from Streamlit's local secret and makes text-generation requests to the Gemini Developer API. Reads `GEMINI_INTERVIEW_MODEL` for interview turns and `GEMINI_REPORT_MODEL` for report generation, so the report can use a different model without changing interview behavior. Prompts maintain the HR role, keep all user-facing generated text in English, use CV/job-specific details, refer to earlier answers when useful, withhold feedback during the interview, and request the specified report fields at the end. Return clear errors to the app; do not silently substitute generic questions or a fabricated report.

Implements `prd.md > Interviewer in character`, `prd.md > Report`, and `prd.md > Failures during the interview`.

### Report presentation — `report.py`

Displays the candidate name (or the literal **Candidate**), job title, overall score and explanation, exactly five scores out of 10 (one per main question), strengths, areas to improve, CV–job fit, and three concrete CV suggestions. Each main-question score considers that answer together with its follow-up answers; follow-ups do not receive separate scores. The report is an on-screen practice estimate, not a prediction; do not invent a candidate name. If the model response is incomplete or invalid, show an error and allow retry rather than presenting a success-shaped partial report.

Implements `prd.md > Report` and `prd.md > States and Boundaries`.

### Local behavior tests — `tests/test_interview.py`

Uses `unittest` to cover deterministic rules such as normalized English/Arabic job titles with at least two letters and only the permitted punctuation, rejection of digits/disallowed symbols/repeated-letter titles, post-submit rejection of answers with fewer than three words or no A–Z letter (including that rejected answers are not sent to Gemini or accepted into the transcript), the five-question sequence, and the follow-up cap. Tests must not require a live API key; Gemini calls can be mocked for retry and response-handling checks.

Implements the verifiable rules in `prd.md > Start interview`, `prd.md > Sending answers`, and `prd.md > Interviewer in character`.

## Data Model

All app data stays in the active Streamlit session; there is no database or app-managed file storage.

| Data | Where it lives and how it changes | What happens on restart or when the session ends |
|---|---|---|
| Uploaded PDF and displayed filename | The upload widget holds the uploaded file in memory. `pdf_utils.py` reads it on Start; keep only the extracted text needed for the interview. | Not written to disk; clear it when starting a new interview or losing the active session. |
| Job title and extracted CV text | `st.session_state`, set after successful local validation. The extracted text is sent to Gemini with requests that need CV context. | Cleared by restart; no interview history is restored. |
| Chat messages | `st.session_state` list of `{role, text}` entries, appended as the interviewer and candidate speak. Provide the relevant/full transcript to Gemini so it can refer to earlier answers. | Cleared by restart/session end. |
| Progress | `st.session_state`: screen/phase, main question number (1–5), and follow-up count for the current question. Updated after each accepted response. | Cleared by restart/session end. |
| Pending request/error | `st.session_state` stores enough request context to retry after a Gemini failure without duplicating a submitted answer. | Cleared after success, restart, or session end. |
| Report | In-memory structured result, created when **View my report** is selected and then rendered by `report.py`. | Cleared by restart/session end; not downloaded or saved. |
| API key | Local `.streamlit/secrets.toml`, read when the app runs; ignored by Git. | Not part of interview state; do not expose it in the UI, logs, or requests as prompt content. |
| Model IDs | `GEMINI_INTERVIEW_MODEL` and `GEMINI_REPORT_MODEL` in `.streamlit/secrets.toml`, read by `gemini_service.py` for their respective calls. | Configuration only; the two settings can be changed independently without altering session data. |

The uploaded PDF is parsed locally. Gemini receives the readable extracted CV text (including any readable name/contact details), job title, and interviewer instructions on the first question request; later interview requests include the answer and conversation context needed to continue; the report request includes CV text, job title, and transcript. The raw PDF file is not sent. This data leaves the computer for processing by Google's API, so use test CVs and consult the current API data-use terms before using personal CVs.

## File Structure

```text
interview-simulator/
├── app.py                         # Streamlit entry point and three screens
├── interview.py                   # Interview progression, limits, and retry context
├── gemini_service.py              # Gemini client and prompt/request handling
├── pdf_utils.py                   # Local PDF text extraction
├── report.py                      # On-screen report rendering
├── requirements.txt               # Streamlit, google-genai, and pypdf
├── README.md                      # Setup, run, test, and demo instructions
├── LICENSE                        # MIT license for the public repository
├── .gitignore                     # Add .streamlit/secrets.toml to existing ignores
├── .streamlit/
│   ├── config.toml                # Light app theme
│   ├── secrets.toml.example       # Safe placeholder; no real key
│   └── secrets.toml               # Local API key; ignored and never committed
├── tests/
│   └── test_interview.py          # Offline tests for flow rules and failures
├── sample_cvs/                    # Fake PDFs for later testing/demo; not a build blocker
└── devpost/                       # Scope, PRD, spec, and later build/ship documents
```

## External Services and Dependencies

### Google Gemini Developer API

- **Purpose:** Generate the next interviewer utterance using CV/job/chat context, and generate the structured end report. No Vertex AI, Google Cloud project, or remote file upload is planned.
- **Python call:** `google-genai` client initialized with `GEMINI_API_KEY`, then `client.models.generate_content(model=MODEL_ID, contents=...)`. Use a Flash model and verify its exact current ID in the [model list](https://ai.google.dev/gemini-api/docs/models).
- **Interview request/response:** Send interviewer instructions, job title, extracted CV text, current main-question/follow-up counts, prior chat, and the latest answer when there is one. Request JSON with an `action` (`question`, `follow_up`, or `finish`) and `text` for the next utterance. Python validates the response and enforces the question/follow-up limits.
- **Report request/response:** Send the job title, extracted CV text, and full transcript. Request JSON fields for candidate name (nullable), overall score/reason, exactly five indexed score/reason entries (one per main question, considering its main answer and follow-ups together), strengths, areas to improve, CV–job fit and gaps, clear-mismatch flag, and exactly three CV suggestions. Validate required fields, five score entries, and score ranges before rendering. See [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output).
- **Underlying operation:** Gemini `generateContent` text generation (documented REST form: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`); the SDK sends the equivalent structured request and reads the generated response text. Do not send the raw PDF.
- **Authentication:** Google AI Studio API key from [Get an API key](https://aistudio.google.com/apikey), loaded from `.streamlit/secrets.toml` and passed through the SDK. Do not commit or expose it.
- **Limits and price:** Depend on the selected model and account. Check the current [pricing](https://ai.google.dev/gemini-api/docs/pricing) and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) before build/demo; no fixed allowance or cost is assumed here.
- **Data handling:** CV text and interview responses are sent to Google for each needed generation. The app does not persist them locally. Google API data handling is governed by current Google terms/settings, not this app; use synthetic or fake CVs for the POC.

### Python packages

- [Streamlit](https://docs.streamlit.io/) — local UI, upload/chat widgets, and per-session memory. See [Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state), [file uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), and [chat elements](https://docs.streamlit.io/develop/api-reference/chat).
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) — supported Python interface for the Gemini Developer API; see the [text generation guide](https://ai.google.dev/gemini-api/docs/text-generation).
- [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) — local PDF text extraction.

Versions should be pinned in `requirements.txt` after checking compatible current releases during setup. `unittest` comes with Python and needs no package installation.

## Important Failure Modes

- **PDF has no extractable text (for example, a scanned image):** stay on the start screen and show the friendly unreadable-PDF error. No OCR fallback is in scope.
- **Gemini request times out, is rate-limited, or returns an unusable response:** preserve the current conversation and pending action; show a friendly error and retry control. Do not add the answer twice, invent a question/report, or display an incomplete report as complete.
- **API key is missing or invalid:** show a clear setup error that points to `.streamlit/secrets.toml` without printing the key; do not start a Gemini request.

## What Was Simplified and Why

- **One local Streamlit process and temporary session memory** instead of accounts, a database, or saved interview history — enough to demonstrate one complete interview and report.
- **Local text extraction with `pypdf`** instead of sending a PDF to Gemini or adding OCR — fewer services and less handling of the original file; scanned CVs are clearly unsupported in the POC.
- **One Gemini text-generation integration** instead of a question bank, second model, or separate evaluation service — questions and report are grounded in this CV and job; output quality remains a practice estimate.
- **On-screen report only** instead of PDF export, and local run instead of deployment — preserves the demo's core moment without adding a document or hosting workflow.
- **Fake sample PDFs can be added later**; their absence does not block implementing or testing the flow.

## Decisions and Open Issues

- **Learner choice:** Python + Streamlit and Google Gemini, with the Gemini Developer API through Google AI Studio rather than Vertex AI/Google Cloud.
- **Learner choice:** Gemini Flash is the right class of model for responsive turns; verify the exact available model ID, pricing, and rate limits during setup.
- **Learner choice:** Gemini may receive extracted CV text and interview answers for this prototype, using test CVs rather than sensitive real CVs. The app itself will not save the CV, chat, or report; the start-screen notice says: “Your CV and answers are sent to Google Gemini. Not saved by this app.”
- **Learner choice:** Keep the Gemini API key in the local Streamlit secrets file, excluded from Git.
- **Learner choice:** Keep the app, interviewer, answers, and report in English. After submission, reject answers with fewer than three words or no English letter A–Z, show the validation message, and do not send them to Gemini; Arabic is out of scope.
- **Learner choice:** Show exactly five report scores, one per main question, each considering its follow-up answers together. Do not show separate follow-up scores or offer a PDF download.
- **Implementation derived from the approved PRD:** keep progress and content in Streamlit's temporary session memory; use one local UI; extract PDF text before calling Gemini; enforce five main questions and no more than two follow-ups in Python; make report available only after the interview.
- **Clarified uncertainty:** The learner asked what Gemini receives, when it receives it, and how the app remembers the chat. Clarified that Python extracts readable text locally; Gemini gets that text (potentially including name/contact details), the job title, and relevant conversation context for generation; Streamlit holds the app's copy in temporary session memory only. Use fake CVs during the POC.
- **Verify early in the build:** compatible Python/package versions; current Flash model ID, rate limits, pricing, and API data-use terms; whether `pypdf` extracts enough text from the selected test CVs.
- **No other unresolved product or architecture choices.** Deployment remains optional and out of scope for this local POC.

## Post-build changes
- `pdf_utils.py` uses an offline lexical heuristic after text extraction: two or more distinct CV section/contact signal groups are required. It avoids an additional Gemini request, cost, latency, and dependency on API availability; the tradeoff is possible false positives/negatives for unusual CV formats or documents containing similar terms.
- `app.py` gives the start card responsive top/bottom spacing and a narrower centered width while leaving page height natural so smaller windows can scroll instead of clipping.
- `gemini_service.py` now specifies the five-question sequence: role-interest warm-up, two distinct CV-specific details, contribution to the company/team, and a deeper behavioral question.

## Arabic mode
- English remains the default. The start-screen language choice is stored in session state and passed to Gemini prompts for opening, interview turns, and report generation. Arabic generation requests simple, professional Modern Standard Arabic while retaining the fixed JSON schema.
- `pdf_utils.py` applies Unicode NFKC normalization to extracted text and maps Persian yeh/kaf variants to Arabic equivalents before keyword checks and use. Arabic CV headings are included in the local CV heuristic. This handles presentation-form text mappings observed in a local PDF probe; scanned/image-only PDFs still need OCR, which is out of scope.
- Arabic answer validation keeps the three-word minimum and accepts English or Arabic-script letters. RTL is scoped to keyed interview and report containers so English/default styling and colors remain unchanged.
- Latin text runs are wrapped in Unicode directional isolates wherever mixed Arabic/English text is displayed in the chat, report, or Arabic start screen.
- The Arabic start card has scoped right-to-left text, labels, controls, and input styling; English mode keeps its existing layout. Streamlit's built-in upload-box English helper text remains unchanged.
- Arabic Gemini replies are checked for scripts outside Arabic and Latin before display; an invalid reply is regenerated once with the same transient-overload retry behavior.
