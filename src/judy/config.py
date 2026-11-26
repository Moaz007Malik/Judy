from __future__ import annotations
import json, os, shutil
from pathlib import Path
from dataclasses import dataclass, asdict, field
from platformdirs import user_data_dir

# Primary app directory for Judy
APP_DIR = Path(user_data_dir("Judy", "Judy"))
OLD_APP_DIR = Path(user_data_dir("Jarvis", "Jarvis"))

# Auto-migrate legacy Jarvis directory if Judy directory doesn't have config yet
if not (APP_DIR / "config.json").exists() and OLD_APP_DIR.exists():
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        for item in OLD_APP_DIR.iterdir():
            target = APP_DIR / item.name
            if not target.exists():
                if item.is_file():
                    shutil.copy2(item, target)
                elif item.is_dir():
                    shutil.copytree(item, target)
    except Exception:
        pass

CONFIG_PATH = APP_DIR / "config.json"

@dataclass
class Settings:
    setup_complete: bool = False
    assistant_name: str = "Judy"
    wake_word: str = "hey judy"
    provider_mode: str = "hybrid"  # local, cloud, hybrid
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_autostart: bool = False
    ollama_start_command: str = "ollama"
    cloud_base_url: str = "https://api.openai.com/v1"
    cloud_model: str = "gpt-4.1-mini"
    cloud_api_key_name: str = "judy_cloud_api_key"
    voice_mode: str = "both"  # wake, push, both, text
    wake_word_enabled: bool = True
    voice_output_enabled: bool = True
    neural_voice: str = "en-US-AvaNeural"
    tts_rate: int = 185
    launch_at_login: bool = False
    minimize_to_tray: bool = True
    start_minimized: bool = False
    confirm_risky_actions: bool = True
    auto_execute_safe_tools: bool = True
    search_roots: list[str] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=lambda: ["$RECYCLE.BIN", "System Volume Information", "Windows", "Program Files", "Program Files (x86)"])
    indexed_extensions: list[str] = field(default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".csv", ".log"])
    max_file_mb: int = 40
    theme: str = "dark"
    # Email and lead outreach settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password_name: str = "judy_smtp_password"
    sender_email: str = ""
    sender_name: str = "Executive Outreach"

    @classmethod
    def load(cls) -> "Settings":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            allowed = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**allowed)
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(CONFIG_PATH)


def get_api_key(settings: Settings) -> str:
    try:
        import keyring
        key = keyring.get_password("Judy", settings.cloud_api_key_name)
        if not key:
            # Check legacy keyring key
            key = keyring.get_password("Jarvis", "jarvis_cloud_api_key")
        return key or ""
    except Exception:
        return ""


def set_api_key(settings: Settings, value: str) -> None:
    try:
        import keyring
        if value:
            keyring.set_password("Judy", settings.cloud_api_key_name, value)
        else:
            try:
                keyring.delete_password("Judy", settings.cloud_api_key_name)
            except Exception:
                pass
    except Exception as exc:
        raise RuntimeError("Could not save API key to Windows Credential Manager.") from exc


def get_smtp_password(settings: Settings) -> str:
    try:
        import keyring
        return keyring.get_password("Judy", settings.smtp_password_name) or ""
    except Exception:
        return ""


def set_smtp_password(settings: Settings, value: str) -> None:
    try:
        import keyring
        if value:
            keyring.set_password("Judy", settings.smtp_password_name, value)
        else:
            try:
                keyring.delete_password("Judy", settings.smtp_password_name)
            except Exception:
                pass
    except Exception as exc:
        raise RuntimeError("Could not save SMTP password to Windows Credential Manager.") from exc


def get_provider_key(provider: str) -> str:
    """Retrieve API key for a specified LLM provider from env or Windows Credential Locker."""
    env_map = {
        "openai": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY",
    }
    var_name = env_map.get(provider.lower())
    if var_name and os.environ.get(var_name):
        return os.environ[var_name]
    try:
        import keyring
        key = keyring.get_password("Judy_LLM", provider.lower())
        if not key and provider.lower() == "openai":
            key = keyring.get_password("Judy", "judy_cloud_api_key")
        return key or ""
    except Exception:
        return ""


def set_provider_key(provider: str, value: str) -> None:
    """Save or delete API key for a specified LLM provider in Windows Credential Locker."""
    try:
        import keyring
        val = value.strip() if value else ""
        if val:
            keyring.set_password("Judy_LLM", provider.lower(), val)
        else:
            try:
                keyring.delete_password("Judy_LLM", provider.lower())
            except Exception:
                pass
    except Exception:
        pass


def get_ollama_status(base_url: str = "http://127.0.0.1:11434") -> tuple[str, str, list[str]]:
    """Query local Ollama instance. Returns (status_text, color_hex, list_of_models)."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", headers={"User-Agent": "Judy"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            if models:
                return (f"Connected ({models[0]})", "#00E676", models)
            return ("No Models", "#FFB300", [])
    except Exception:
        return ("Offline", "#7E9BB8", [])

