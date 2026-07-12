import httpx
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings

MODEL = "text-embedding-3-large"

async def get_embedding(text: str) -> list:
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.startswith("sk-"):
        return []
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": MODEL, "input": text[:8000]}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return data["data"][0]["embedding"]
    except Exception:
        return []
