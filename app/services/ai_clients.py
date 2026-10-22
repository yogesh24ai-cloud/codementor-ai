import logging
import os
import time

import anthropic
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

log = logging.getLogger(__name__)


class AIConfigError(Exception):
    pass


class AIServiceError(Exception):
    pass


class ClaudeClient:
    def __init__(self, api_key, model):
        self.model_name = model
        self._client = anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=1)

    def generate(self, system, user):
        try:
            msg = self._client.messages.create(
                model=self.model_name, max_tokens=4000, system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError:
            log.exception("Claude API call failed")
            raise AIServiceError("The AI service had a problem. Please try again in a moment.")
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class GeminiClient:
    RETRY_CODES = (500, 503, 504)
    WAITS = (2, 5)  # seconds to wait before retry 2 and 3

    def __init__(self, api_key, model):
        self.model_name = model
        self._fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "").strip()
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=60000),
        )

    def _call(self, model, system, user):
        return self._client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=4000,
                response_mime_type="application/json",
            ),
        ).text or ""

    def generate(self, system, user):
        models = [self.model_name] + ([self._fallback] if self._fallback else [])
        last_code = None
        for model in models:
            for attempt in range(len(self.WAITS) + 1):
                try:
                    return self._call(model, system, user)
                except genai_errors.APIError as e:
                    last_code = getattr(e, "code", None)
                    log.warning("Gemini %s failed (code %s)", model, last_code)
                    if last_code==429:
                        break;
                    if last_code not in self.RETRY_CODES:
                        raise AIServiceError("The AI service had a problem. Please try again.")
                    if attempt < len(self.WAITS):
                        time.sleep(self.WAITS[attempt])
        if last_code == 429:
            raise AIServiceError("The free AI limit was reached. Wait a minute and try again.")
        raise AIServiceError("The free AI service is busy right now. Please try again in a moment.")


def _real_key(value):
    value = (value or "").strip()
    return value if value and not value.startswith("your-") else ""


def get_ai_client():
    provider = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
    if provider == "claude":
        key = _real_key(os.environ.get("ANTHROPIC_API_KEY"))
        if not key:
            raise AIConfigError("Claude is not configured. Add ANTHROPIC_API_KEY to .env.")
        return ClaudeClient(key, os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    if provider == "gemini":
        key = _real_key(os.environ.get("GEMINI_API_KEY"))
        if not key:
            raise AIConfigError("Gemini is not configured. Add GEMINI_API_KEY to .env.")
        return GeminiClient(key, os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"))
    raise AIConfigError("AI_PROVIDER must be 'gemini' or 'claude'.")