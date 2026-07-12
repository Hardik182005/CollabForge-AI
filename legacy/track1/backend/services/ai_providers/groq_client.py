import sys
import os
import httpx
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings
from .openai_client import OpenAIChatClient


class GroqClient:
    BASE_URL = "https://api.groq.com/openai/v1"

    async def complete(self, system: str, user: str, max_tokens: int = 1000) -> str:
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_..."):
            return await OpenAIChatClient().complete(system, user, max_tokens)

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            return await OpenAIChatClient().complete(system, user, max_tokens)


groq_client = GroqClient()
