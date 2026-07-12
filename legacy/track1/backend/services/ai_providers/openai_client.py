import sys
import os
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings


class OpenAIChatClient:
    BASE_URL = "https://api.openai.com/v1"
    MODEL = "gpt-4o-mini"

    async def complete(self, system: str, user: str, max_tokens: int = 1500) -> str:
        if not settings.OPENAI_API_KEY:
            return ""

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            return ""

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """
        Generate an image with OpenAI and return it as base64 PNG (no data URI
        prefix), or '' on failure. Tries gpt-image-1 first (newest), then falls
        back to dall-e-3 — so it works whether or not the account is verified
        for gpt-image-1. gpt-image-1 always returns b64_json; dall-e-3 returns a
        URL, which we fetch and base64-encode so callers get one consistent type.
        """
        if not settings.OPENAI_API_KEY:
            return ""

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        attempts = [
            {"model": "gpt-image-1", "prompt": prompt[:1000], "size": size, "n": 1},
            {"model": "dall-e-3", "prompt": prompt[:1000], "size": "1024x1024", "n": 1},
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for payload in attempts:
                    try:
                        r = await client.post(
                            f"{self.BASE_URL}/images/generations",
                            headers=headers,
                            json=payload,
                        )
                        if r.status_code != 200:
                            continue
                        item = (r.json().get("data") or [{}])[0]
                        b64 = item.get("b64_json")
                        if b64:
                            return b64
                        # dall-e-3 returns a hosted URL — fetch it and encode.
                        url = item.get("url")
                        if url:
                            img = await client.get(url)
                            if img.status_code == 200:
                                import base64
                                return base64.b64encode(img.content).decode("utf-8")
                    except Exception:
                        continue
        except Exception:
            return ""
        return ""


openai_chat_client = OpenAIChatClient()
