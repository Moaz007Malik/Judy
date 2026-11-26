from __future__ import annotations
import os, platform, re, shutil, subprocess, sys, tempfile, urllib.parse, webbrowser
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QMessageBox
from .file_index import FileIndex
from .lead_finder import LeadManager
from .email_client import EmailService

class ToolRunner:
    def __init__(self, parent, index: FileIndex, settings, confirm: bool = True):
        self.parent = parent
        self.index = index
        self.settings = settings
        self.confirm = confirm
        self.leads = LeadManager()
        self.email_svc = EmailService(settings)

    def _approve(self, title: str, detail: str) -> bool:
        if not self.confirm:
            return True
        btn = QMessageBox.question(
            self.parent,
            title,
            detail + "\n\nAllow Judy to execute this action?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return btn == QMessageBox.StandardButton.Yes

    def open_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("https://", "http://")):
            url = "https://" + url
        if not self._approve("Open website", f"Judy wants to open:\n{url}"):
            return "Cancelled by user."
        webbrowser.open(url)
        return f"Opened {url} in your browser."

    def open_app(self, app: str) -> str:
        key = app.strip().lower()
        # Rich dictionary of popular Windows programs and executables
        known = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "firefox": "firefox",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "files": "explorer.exe",
            "terminal": "wt.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "settings": "ms-settings:",
            "vs code": "code",
            "vscode": "code",
            "code": "code",
            "spotify": "spotify",
            "discord": "discord",
            "slack": "slack",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt"
        }

        command = known.get(key, key)
        if not self._approve("Launch Application", f"Judy wants to launch {key}."):
            return "Cancelled by user."

        try:
            if command.startswith("ms-"):
                os.system(f"start {command}")
            else:
                subprocess.Popen(command, shell=True)
            return f"Successfully launched {key.title()}."
        except OSError as e:
            return f"Could not launch {key}: {e}"

    def search_web(self, query: str) -> str:
        """Executes a real-time web search and returns key highlights."""
        import requests
        from bs4 import BeautifulSoup

        clean_query = query.strip()
        encoded = urllib.parse.quote_plus(clean_query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # Try search engines
        urls = [
            f"https://www.bing.com/search?q={encoded}",
            f"https://html.duckduckgo.com/html/?q={encoded}",
        ]

        results = []
        for u in urls:
            try:
                r = requests.get(u, headers=headers, timeout=6)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for item in soup.select("li.b_algo, .result")[:5]:
                        title = item.select_one("h2, .result__title")
                        snippet = item.select_one(".b_caption p, .result__snippet")
                        link = item.select_one("a[href]")
                        t_text = title.get_text(strip=True) if title else ""
                        s_text = snippet.get_text(strip=True) if snippet else ""
                        href = link["href"] if link else ""
                        if t_text and s_text:
                            results.append(f"• **{t_text}**\n  {s_text}\n  URL: {href}")
                    if results:
                        break
            except Exception:
                continue

        if not results:
            # Fallback direct search link in browser
            fallback_url = f"https://www.google.com/search?q={encoded}"
            return f"Searched the web for '{clean_query}'. View live results:\n{fallback_url}"

        return f"### Web Search Results for: *{clean_query}*\n\n" + "\n\n".join(results[:4])

    def find_leads(self, niche: str, location: str, count: int = 5, ai_client=None) -> str:
        """Finds targeted client leads, extracts info, and saves to database."""
        discovered = self.leads.search_and_save_leads(niche, location, count, ai_client)
        if not discovered:
            return f"No leads found for {niche} in {location}. Try expanding your niche or location keywords."

        lines = [f"### 🎯 Found {len(discovered)} Leads for {niche.title()} in {location.title()}:\n"]
        for i, lead in enumerate(discovered, 1):
            email = lead.get('email') or 'Not listed'
            phone = lead.get('phone') or 'Not listed'
            website = lead.get('website') or 'Not listed'
            lines.append(
                f"**{i}. {lead.get('company')}** — {lead.get('name')} ({lead.get('title', 'Owner')})\n"
                f"   📧 Email: `{email}` | 📞 Phone: `{phone}`\n"
                f"   🌐 Website: {website}\n"
                f"   💡 Notes: {lead.get('notes', '')}\n"
            )
        lines.append("\n*These leads have been saved to your Lead Finder Studio database. You can draft an outreach email directly from the Outreach tab.*")
        return "\n".join(lines)

    def draft_email_for_lead(self, company_or_email: str, service: str = "", ai_client=None) -> str:
        all_leads = self.leads.get_leads()
        match = None
        for l in all_leads:
            if company_or_email.lower() in (l.get("company", "").lower() + l.get("email", "").lower() + l.get("name", "").lower()):
                match = l
                break

        if not match:
            # Create ad-hoc prospect profile
            match = {
                "name": "Partner",
                "company": company_or_email,
                "email": company_or_email if "@" in company_or_email else "",
                "niche": "Business",
                "location": "Local"
            }

        service_offered = service or "Web Design & Digital Growth"
        subject, body = self.email_svc.generate_draft(
            template_key="Web Design & Digital Upgrade",
            lead=match,
            custom_offer=service_offered,
            ai_client=ai_client
        )

        return (
            f"### ✉️ Outreach Email Draft for {match.get('company')}\n\n"
            f"**To:** `{match.get('email') or 'Recipient Email'}`\n"
            f"**Subject:** {subject}\n\n"
            f"```text\n{body}\n```\n\n"
            f"*You can send this email directly via SMTP or open your mail app from the Outreach tab.*"
        )

    def get_system_info(self) -> str:
        """Retrieves real-time system performance, CPU, RAM, and disk stats."""
        import socket
        try:
            # CPU and RAM via Windows wmic or powershell
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory; "
                 "Get-CimInstance Win32_Processor | Select-Object LoadPercentage; "
                 "Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free"],
                capture_output=True, text=True, timeout=5
            )
            raw_out = res.stdout.strip()
        except Exception:
            raw_out = "System details query timed out."

        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "127.0.0.1"

        os_ver = f"{platform.system()} {platform.release()} ({platform.version()})"
        return (
            f"### 💻 System Performance & Diagnostics\n\n"
            f"• **Device Name:** `{hostname}`\n"
            f"• **Operating System:** `{os_ver}`\n"
            f"• **Local IP:** `{ip}`\n"
            f"• **Date & Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
            f"**Live Metrics:**\n```\n{raw_out[:600]}\n```"
        )

    def run_command(self, cmd: str) -> str:
        clean = cmd.strip()
        if not clean:
            return "No command provided."

        # Safety confirmation
        if not self._approve("Execute Shell Command", f"Judy wants to run this terminal command:\n\n{clean}"):
            return "Command execution cancelled by user for safety."

        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", clean],
                capture_output=True, text=True, timeout=20
            )
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            result = out if out else (err if err else "(Command executed with no output)")
            return f"### Command Output:\n```\n{result[:1500]}\n```"
        except subprocess.TimeoutExpired:
            return "Command timed out after 20 seconds."
        except Exception as e:
            return f"Failed to execute command: {e}"

    def take_screenshot(self) -> str:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return "Primary screen not detected."
        pix = screen.grabWindow(0)
        temp_path = Path(tempfile.gettempdir()) / f"judy_screenshot_{int(datetime.now().timestamp())}.png"
        pix.save(str(temp_path), "PNG")
        try:
            os.startfile(str(temp_path))
            return f"Captured full screen and saved to:\n`{temp_path}`"
        except Exception as e:
            return f"Captured screenshot to `{temp_path}`: {e}"

    def search_files(self, query: str) -> str:
        results = self.index.search(query)
        if not results:
            return "No indexed files matched. Run 'Scan Files' in File Intelligence or try different keywords."
        lines = ["### Closest Indexed Files:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['name']}** — `{r['path']}`\n   Match: {r['snippet'] or '(filename match)'}")
        return "\n".join(lines)

    def open_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return "That file does not exist."
        if not self._approve("Open File", f"Judy wants to open this file:\n{p}"):
            return "Cancelled by user."
        try:
            os.startfile(str(p))
            return f"Opened {p.name}."
        except Exception as e:
            return f"Could not open file: {e}"

    def create_file(self, path: str, content: str) -> str:
        p = Path(path)
        if not self._approve("Create File", f"Judy wants to write to:\n{p}"):
            return "Cancelled by user."
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Successfully created file: `{p}`"
        except Exception as e:
            return f"Failed to create file: {e}"

    def read_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"File `{path}` does not exist."
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            snippet = content[:1500]
            if len(content) > 1500:
                snippet += "\n... (truncated)"
            return f"### Contents of `{p.name}`:\n```\n{snippet}\n```"
        except Exception as e:
            return f"Could not read file: {e}"

    def set_theme(self, theme_query: str) -> str:
        from .themes import THEMES
        q = theme_query.lower().strip()
        matched_id = None
        for tid, t in THEMES.items():
            if tid in q or t.name.lower() in q:
                matched_id = tid
                break
        if not matched_id:
            keywords = {
                "gold": "obsidian_gold",
                "amber": "obsidian_gold",
                "obsidian": "obsidian_gold",
                "cyan": "cyberpunk",
                "cyber": "cyberpunk",
                "blue": "arctic_frost",
                "ice": "arctic_frost",
                "frost": "arctic_frost",
                "arctic": "arctic_frost",
                "pink": "synthwave",
                "magenta": "synthwave",
                "synthwave": "synthwave",
                "sunset": "synthwave",
                "green": "matrix",
                "matrix": "matrix",
                "emerald": "matrix",
                "red": "blood_moon",
                "blood": "blood_moon",
                "crimson": "blood_moon"
            }
            for kw, tid in keywords.items():
                if kw in q:
                    matched_id = tid
                    break
        if matched_id and hasattr(self.parent, "apply_theme"):
            self.parent.apply_theme(matched_id)
            theme = THEMES[matched_id]
            return f"Switched theme to **{theme.name}** {theme.icon}. Applied new palette across Command Center and 3D Core."
        available = "\n".join([f"• **{t.name}** {t.icon} — _{t.description}_" for t in THEMES.values()])
        return f"Available visual themes in Judy Command Center:\n{available}\n\nSay *'change theme to Obsidian Gold'* or select from the top header bar."
