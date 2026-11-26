from __future__ import annotations
import requests
from .config import Settings, get_api_key

class AIError(RuntimeError): pass

class AIClient:
    def __init__(self, settings: Settings): self.settings = settings

    def reply(self, messages: list[dict]) -> str:
        mode = self.settings.provider_mode
        errors = []
        if mode in ("local", "hybrid"):
            try: return self._ollama(messages)
            except Exception as e: errors.append(f"Local model: {e}")
            if mode == "local": raise AIError("\n".join(errors))
        if mode in ("cloud", "hybrid"):
            try: return self._cloud(messages)
            except Exception as e: errors.append(f"Cloud model: {e}")
        raise AIError("No AI provider responded. " + " | ".join(errors))

    def _ollama(self, messages: list[dict]) -> str:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "options": {"num_ctx": 2048, "temperature": 0.6},
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip() or "The local model returned an empty response."

    def _cloud(self, messages: list[dict]) -> str:
        key = get_api_key(self.settings)
        if not key: raise AIError("No cloud API key saved. Open Settings to configure it.")
        url = self.settings.cloud_base_url.rstrip("/") + "/chat/completions"
        r = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"model": self.settings.cloud_model, "messages": messages, "temperature": 0.3}, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
