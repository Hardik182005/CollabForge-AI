import httpx
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings
from .openai_client import OpenAIChatClient


class GeminiClient:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    MODEL = "gemini-2.0-flash"

    async def complete(self, system: str, user: str, max_tokens: int = 1500) -> str:
        # 1) Prefer OpenAI GPT-4o-mini for complex generation (highest quality).
        openai_result = await OpenAIChatClient().complete(system, user, max_tokens)
        if openai_result:
            return openai_result

        # 2) Fall back to Gemini 2.0 Flash (free).
        if settings.GEMINI_API_KEY:
            url = f"{self.BASE_URL}/models/{self.MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7,
                },
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(url, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        # No provider available: return empty so callers surface an honest
        # error/unavailable state instead of canned fake output.
        return ""

    async def complete_json(self, system: str, user: str, max_tokens: int = 1500) -> dict:
        result = await self.complete(
            system,
            user + "\n\nReturn ONLY valid JSON with no markdown code blocks.",
            max_tokens,
        )
        try:
            m = re.search(r"\{.*\}", result, re.DOTALL)
            if m:
                return json.loads(m.group())
        except (json.JSONDecodeError, TypeError):
            pass
        return {}


gemini_client = GeminiClient()
