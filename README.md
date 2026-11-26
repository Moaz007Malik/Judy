# Judy — Executive AI Partner & Desktop Assistant (Windows)

**Judy** is a high-performance, local-first executive desktop assistant and autonomous partner for Windows, built with Python and PySide6.

---

## 🌟 Key Features

### 1. 🎙️ Continuous Voice & Wake-Word Listening ("Judy")
- **Listens on "Judy"**: Background voice listener continuously monitors your microphone for the wake word *"Judy"* or *"Hey Judy"*.
- **Push-to-Talk / 1-Click Speak**: Interactive glowing microphone button for instant speech recognition.
- **Local Text-to-Speech (TTS)**: Judy speaks her responses aloud using native Windows SAPI5 voices.
- Toggle wake-word listening and voice audio directly from the header bar or Settings.

### 2. 🎯 Lead Finder Studio (Client Prospecting Engine)
- **Automated Client Discovery**: Search for real business leads across any niche and location (e.g., *"Web Design in Miami"*, *"Real Estate in New York"*, *"Dentists in London"*).
- **Contact Extraction**: Automatically extracts business names, decision-makers, email addresses, phone numbers, and websites from live web results.
- **Lead Database**: Manages leads in a dedicated SQLite database (`leads.sqlite3`) with tracking statuses (*New*, *Contacted*, *Replied*, *Closed*).
- **1-Click Actions**: Draft cold outreach emails directly for any lead, add leads manually, or export the entire list to CSV.

### 3. ✉️ Outreach & Cold Email Studio
- **AI-Powered Pitch Generator**: Automatically drafts high-converting, personalized cold pitch emails tailored to your prospect's business and your service offering.
- **Battle-Tested Templates**: Built-in sequences for Web Design & Digital Upgrades, AI Automation & Chatbots, Client Acquisition, and Quick Follow-ups.
- **Dual Sending Modes**:
  - **Direct SMTP**: Send emails directly from Judy using your SMTP server (Gmail, Outlook, custom domains).
  - **Windows Mail Client**: Open your default Windows Mail, Outlook, or Thunderbird client with subject and body pre-filled with 1 click.

### 4. ⚡ Desktop & Power Automation ("Do whatever I ask")
- **System Diagnostics**: Live CPU usage, RAM utilization, disk drives, local IP address, and Windows OS metrics.
- **PowerShell Runner**: Execute shell commands and terminal tasks safely from the desktop GUI.
- **Instant App Launcher**: Open Chrome, Edge, VS Code, Spotify, Discord, Slack, File Explorer, Terminal, Calculator, Task Manager, or any custom executable.
- **Screen Capture**: Capture instant full-screen screenshots saved to temporary storage with immediate preview.
- **Real-Time Web Search**: Search the web and receive synthesized executive highlights.

### 5. 📁 File Intelligence
- Local SQLite FTS5 index extracting content from PDF, DOCX, TXT, Markdown, CSV, and log files.
- Instant keyword search with snippet highlighting and one-click file opening.

### 6. 🎨 Ultra-Modern Glassmorphism UI
- Cyber obsidian aesthetic with dynamic Judy hologram orb status indicator (Idle, Listening, Thinking, Speaking).
- Rich chat bubbles with avatars, suggestion chips, and quick action buttons.

---

## 🚀 Getting Started

### Run with Python:
```powershell
# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Launch Judy
python run_judy.py
```

Or run via the module entrypoint:
```powershell
python -m jarvis.main
```

---

## ⚙️ Configuration & Data Storage
- Settings and databases are stored locally in your Windows user profile:
  - Configuration: `%LOCALAPPDATA%\Judy\config.json`
  - Leads Database: `%LOCALAPPDATA%\Judy\leads.sqlite3`
  - File Index: `%LOCALAPPDATA%\Judy\files.sqlite3`
- Cloud API keys and SMTP passwords are saved securely in **Windows Credential Manager** via `keyring`.
