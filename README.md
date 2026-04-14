# Deciora

A polished Streamlit decision engine that helps users judge whether a career or research opportunity is worth pursuing.

## What the app does

- Extracts job text from a URL when possible, then falls back to pasted job description text
- Parses PDF resumes with PyMuPDF
- Scores fit on skills, keywords, education, and experience
- Flags company and posting risk signals
- Produces a final recommendation: `Apply`, `Consider`, or `Skip`
- Works fully in deterministic demo mode without any paid API key
- Optionally upgrades the final JSON output with an OpenAI-compatible API if environment variables are configured

## Project structure

```text
.
├── app.py
├── sample_data.py
├── requirements.txt
├── README.md
├── .env.example
└── utils
    ├── __init__.py
    ├── decision.py
    ├── helpers.py
    ├── llm.py
    ├── parsing.py
    ├── risk.py
    └── scoring.py
```

## Local setup

Use Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

If your system uses `python3` for Python 3.11, this also works:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional LLM mode

The app runs end to end without any API credentials. To enable the optional LLM path:

1. Copy `.env.example` to `.env`
2. Fill in:
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_MODEL`
3. Restart Streamlit
4. Turn on `Use optional LLM enhancement` in the sidebar

If the LLM call fails, the app gracefully falls back to the built-in demo logic.

## Demo flow

1. Click `Load Demo Sample Data`
2. Leave the demo resume toggle on
3. Click `Analyze`

The sample URL is intentionally generic, so the demo shows the fallback path from URL scraping to pasted job description text.
