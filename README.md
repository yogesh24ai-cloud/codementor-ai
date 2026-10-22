# CodeMentor AI

A beginner-friendly Python debugging helper. Paste code, see real syntax and Ruff
findings, then get an AI-suggested fix with simple explanations.

## What it does
- Checks Python code with the `ast` parser and Ruff for syntax errors, undefined names, and common risky/bug-prone patterns. The AI also reviews likely behavior and edge cases; sharing what the code is supposed to do makes logic analysis more useful. Code is never executed.
- Sends the findings to an AI model (Gemini or Claude, set in `.env`).
- Validates the AI's JSON answer, then re-checks the corrected code.
- Shows original and corrected code side by side. Copy or download the fix.

## Honest limits
- A fix labelled "Statically verified" only passed syntax and Ruff. It may still be wrong.
- Tests and sandbox execution are not implemented, so there is no "test-verified" label.
- Only Python is supported. Accounts and saved analysis history are available; signed-in users can compare issue counts across their recent reviews. Saved history includes submitted code.
- Static checks can identify common mistakes, but they cannot prove a program's logic is correct or replace tests written for the program.
- Logic analysis is an AI-assisted review, not a formal proof. Include the expected behavior and verify suggestions with tests.
- The editor and sample snippets work without an external editor service.
- Free AI tiers can be busy or rate limited.

## Run locally (Windows)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env
    python wsgi.py

Edit `.env` with your own key. Never commit `.env`. Open http://127.0.0.1:5000

## Test
    python -m pytest -v

## Security
- API keys stay on the server in `.env`.
- Request size, code length and AI output format are validated.
- Rate limits are applied. Submitted code is treated as untrusted data.