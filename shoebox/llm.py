"""Minimal Ollama client. Refuses any host that is not loopback."""
from __future__ import annotations

import json
import urllib.request
from urllib.parse import urlparse

LOOPBACK = {"localhost", "127.0.0.1", "::1"}
DEFAULT_URL = "http://127.0.0.1:11434"


class LLMError(Exception):
    pass


class OllamaClient:
    def __init__(self, model: str = "llama3.2:3b", base_url: str = DEFAULT_URL, timeout: float = 120):
        host = urlparse(base_url).hostname
        if host not in LOOPBACK:
            raise LLMError(f"refusing non-local LLM host {host!r}: Shoebox never sends documents off this machine")
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "model": self.model,
            "stream": False,
            "format": schema,  # Ollama constrains decoding to this JSON schema
            "options": {"temperature": 0, "num_ctx": 4096},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                content = json.load(r)["message"]["content"]
            return json.loads(content)
        except (OSError, KeyError, json.JSONDecodeError) as e:
            raise LLMError(f"Ollama call failed ({e}). Is `ollama serve` running and `{self.model}` pulled?") from e
