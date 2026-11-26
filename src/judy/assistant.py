from __future__ import annotations
import re
from .ai import AIClient, AIError
from .tools import ToolRunner

SYSTEM_PROMPT = """You are Judy, an elite executive AI partner and desktop assistant for Windows.
You are proactive, sharp, highly capable, and polished.
You have native access to:
- Lead Generation & Client Finding (finding real businesses, verified emails, phone numbers, and websites for any niche/city)
- Cold Outreach & Email Automation (writing high-converting personalized pitches and sending emails)
- Real-Time Web Search (retrieving the latest web information, news, and research)
- Desktop Automation & Control (launching apps, running PowerShell commands, checking system performance/CPU/RAM, taking screenshots)
- File Intelligence (searching, reading, and indexing local PC documents, PDFs, DOCXs)

Provide concise, high-value, executive-ready answers. When asked to perform an action, be direct and helpful."""

class Assistant:
    def __init__(self, settings, tools: ToolRunner):
        self.settings = settings
        self.tools = tools
        self.ai = AIClient(settings)
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def respond(self, text: str) -> str:
        raw = text.strip()
        low = raw.lower()

        # 0. Theme Switching Intent
        # Examples: "change theme to obsidian gold", "switch theme to synthwave", "set theme matrix", "list themes"
        theme_match = re.search(r"(?:change|switch|set|select|use)\s+(?:the\s+)?theme\s+(?:to\s+)?(.+)", low)
        if theme_match:
            return self.tools.set_theme(theme_match.group(1).strip())
        if "theme" in low and any(k in low for k in ("available", "list", "show", "what", "options")):
            return self.tools.set_theme("list")

        # 1. Lead Generation Intent
        # Examples: "find 3 leads for digital marketing in Austin", "find me clients in Miami", "get leads for dentists"
        lead_match = re.search(r"(?:find|search|get|look for)\s+(?:me\s+)?(?:(\d+)\s+)?(?:leads?|clients?|customers?|prospects?)(?:\s+(?:for|in)\s+([^,.]+?))?(?:\s+in\s+([^,.]+))?$", low, re.I)
        if lead_match:
            count = int(lead_match.group(1)) if lead_match.group(1) else 5
            niche = (lead_match.group(2) or "Local Businesses").strip()
            location = (lead_match.group(3) or "United States").strip()
            return self.tools.find_leads(niche=niche, location=location, count=count, ai_client=self.ai)

        if any(k in low for k in ["lead", "leads", "clients", "prospects"]):
            if any(k in low for k in ["find", "search", "get", "look"]):
                return self.tools.find_leads(niche="Local Businesses", location="United States", count=5, ai_client=self.ai)

        # 2. Email Drafting & Outreach Intent
        # Examples: "draft email to Alex at Apex Solutions", "email john@example.com about web design"
        email_match = re.search(r"(?:draft|write|send|prepare)\s+(?:an?\s+)?(?:outreach\s+)?(?:email|pitch|message)\s+(?:to\s+)?([^,.]+?)(?:\s+(?:about|regarding|offering)\s+([^,.]+))?$", low, re.I)
        if email_match:
            target = email_match.group(1).strip()
            service = (email_match.group(2) or "Digital Modernization & Growth").strip()
            return self.tools.draft_email_for_lead(company_or_email=target, service=service, ai_client=self.ai)

        # 3. Web Search Intent
        # Examples: "search web for latest AI news", "google quantum computing breakthroughs"
        search_match = re.search(r"^(?:search\s+(?:the\s+)?web\s+for|search\s+for|google|bing|browse\s+for)\s+(.+)", raw, re.I)
        if search_match:
            return self.tools.search_web(search_match.group(1).strip())

        # 4. System Diagnostics & Performance
        # Examples: "check cpu", "system performance", "how much ram", "system diagnostics", "specs"
        if any(x in low for x in ("cpu usage", "system info", "system performance", "ram usage", "system diagnostics", "check performance", "check system", "check memory")):
            return self.tools.get_system_info()

        # 5. Screenshot Intent
        if any(x in low for x in ("take a screenshot", "capture screen", "screenshot my desktop", "grab screen")):
            return self.tools.take_screenshot()

        # 6. Open Website / URL
        url_match = re.search(r"(?:open|go to|visit)\s+(https?://\S+|[\w.-]+\.(?:com|org|net|io|dev|gov|edu|ai|co)(?:/\S*)?)", raw, re.I)
        if url_match:
            return self.tools.open_url(url_match.group(1))

        # 7. Open Application
        app_match = re.search(r"(?:open|launch|start)\s+([a-zA-Z0-9\s]+)$", low)
        if app_match:
            candidate = app_match.group(1).strip()
            if candidate not in ("the", "a", "my", "this", "it", "leads", "settings", "files"):
                res = self.tools.open_app(candidate)
                if not res.startswith("Could not"):
                    return res

        # 8. Run Terminal / PowerShell Command
        cmd_match = re.search(r"^(?:run|execute|powershell|cmd|terminal)\s+(?:command\s+)?[:\-]?\s*(.+)", raw, re.I)
        if cmd_match:
            return self.tools.run_command(cmd_match.group(1))

        # 9. Local File Search
        if any(x in low for x in ("find file", "search file", "look for file", "find my pdf", "find document", "search documents")):
            query = re.sub(r"^(please\s+)?(find|search|look for)( me)?( the| a)?( file| document| pdf)?", "", raw, flags=re.I).strip(" .?!") or raw
            return self.tools.search_files(query)

        # 10. General Conversational AI Reasoning
        self.history.append({"role": "user", "content": raw})
        try:
            answer = self.ai.reply(self.history[-24:])
        except AIError as e:
            answer = f"I couldn't reach an AI model provider ({e}). You can configure your local Ollama or cloud API in Settings."

        self.history.append({"role": "assistant", "content": answer})
        return answer
