from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com", model: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置")
        self.base_url = base_url.rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        self._client = httpx.Client(
            # 生成《学术动态》这类长文本时，60s 可能不够；延长到 5 分钟
            timeout=300.0,
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
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                logger.info(f"[DeepSeek] 请求开始 attempt={attempt} model={self.model} max_tokens={max_tokens}")
                t0 = time.time()
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                dt = time.time() - t0
                logger.info(f"[DeepSeek] 请求成功耗时 {dt:.2f}s")
                return data["choices"][0]["message"]["content"]
            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_err = e
                logger.warning(f"[DeepSeek] 请求失败 attempt={attempt}: {e}")
                if attempt < 3:
                    time.sleep(2)
                    continue
                raise

        # 理论上不会走到这里
        if last_err:
            raise last_err
        raise RuntimeError("DeepSeek 请求失败：未知原因")

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
