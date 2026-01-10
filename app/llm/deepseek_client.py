from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com", model: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置")
        self.base_url = base_url.rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        self._client = httpx.Client(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def chat(self, messages: List[Dict[str, str]], *, temperature: float = 0.4, max_tokens: int = 1800) -> str:
        # DeepSeek OpenAI兼容接口
        url = f"{self.base_url}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
