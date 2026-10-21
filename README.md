# AI Mock Interview

A local English-only interview practice app. It reads CV text on your computer and sends that text, the job title, and accepted interview answers to Google Gemini. Use fake CVs for testing.

## Run locally

Check that Python is 3.11 or newer, then create and activate a virtual environment in Windows PowerShell:

```powershell
python --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Edit `.streamlit\secrets.toml` locally with your Google AI Studio key and model IDs. Never commit this file or share the key. Then run:

```powershell
python -m streamlit run app.py
```

Open http://localhost:8501. The MIT license is in `LICENSE`.
