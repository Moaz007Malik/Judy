from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from .config import APP_DIR

DB_PATH = APP_DIR / "agents.sqlite3"

DEFAULT_AGENTS = [
    {
        "name": "Coding Agent",
        "role": "Software Engineering & Code Debugger",
        "avatar": "</>",
        "status": "Active",
        "description": "Writes, reviews, and debugs code across Python, JavaScript, and Windows automation scripts.",
        "skills": "Python, PySide6, Shell, Git, Debugging"
    },
    {
        "name": "Research & Lead Agent",
        "role": "Market Research & Client Prospecting",
        "avatar": "🔍",
        "status": "Active",
        "description": "Discovers real B2B client leads, analyzes competitor websites, and extracts contact info.",
        "skills": "Web Scraping, Lead Discovery, Verification, Outreach"
    },
    {
        "name": "Memory Agent",
        "role": "Knowledge & Context Indexer",
        "avatar": "💾",
        "status": "Standby",
        "description": "Stores user preferences, project facts, and maintains contextual memory graph.",
        "skills": "Context Tracking, Recall, Vector Indexing"
    },
    {
        "name": "Browser & Web Agent",
        "role": "Real-Time Web Intelligence",
        "avatar": "🌐",
        "status": "Standby",
        "description": "Navigates live websites, fetches articles, and summarizes breaking news.",
        "skills": "DuckDuckGo, Bing, HTTP Requests, Content Parsing"
    },
    {
        "name": "Task Agent",
        "role": "Workflow & Mission Scheduler",
        "avatar": "📋",
        "status": "Standby",
        "description": "Organizes daily objectives, tracks deadlines, and automates multi-step pipelines.",
        "skills": "Task Planning, Prioritization, Reminders"
    },
    {
        "name": "System Agent",
        "role": "PC Diagnostics & Security",
        "avatar": "🛡️",
        "status": "Standby",
        "description": "Monitors CPU, RAM, disk drives, network performance, and manages desktop apps.",
        "skills": "PowerShell, Hardware Vitals, Process Management"
    }
]

class AgentsManager:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                role TEXT,
                avatar TEXT,
                status TEXT DEFAULT 'Standby',
                description TEXT,
                skills TEXT,
                created_at TEXT
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                title TEXT,
                description TEXT,
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Pending',
                due_date TEXT,
                result TEXT,
                created_at TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
        self.db.commit()

        # Seed default agents if table is empty
        count = self.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for ag in DEFAULT_AGENTS:
                self.db.execute("""
                    INSERT OR IGNORE INTO agents (name, role, avatar, status, description, skills, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ag["name"], ag["role"], ag["avatar"], ag["status"], ag["description"], ag["skills"], now))
            self.db.commit()

            # Seed a few realistic mission tasks
            tasks_seed = [
                (1, "Finalize HUD panel spacing", "Refine glassmorphism CSS padding and neon glows for the main Command Center dashboard.", "High", "In Progress", "Today"),
                (2, "Discover 5 Web Design Leads in NY", "Find businesses in New York needing website modernization and save contact info.", "High", "Done", "Today"),
                (4, "Deep-work block: Voice pipeline", "Verify edge-tts natural speech playback and microphone energy thresholding.", "Medium", "Pending", "Today"),
                (5, "Design Review — Command Center V1", "Inspect multi-tab layout, system monitors, and mission timeline accuracy.", "Urgent", "Pending", "Tomorrow")
            ]
            for t in tasks_seed:
                self.db.execute("""
                    INSERT INTO agent_tasks (agent_id, title, description, priority, status, due_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (t[0], t[1], t[2], t[3], t[4], t[5], now))
            self.db.commit()

    def get_all_agents(self) -> list[dict]:
        cursor = self.db.cursor()
        cursor.execute("SELECT id, name, role, avatar, status, description, skills, created_at FROM agents ORDER BY id ASC")
        cols = ["id", "name", "role", "avatar", "status", "description", "skills", "created_at"]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def add_agent(self, name: str, role: str, avatar: str = "🤖", description: str = "", skills: str = "") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO agents (name, role, avatar, status, description, skills, created_at)
            VALUES (?, ?, ?, 'Standby', ?, ?, ?)
        """, (name, role, avatar, description, skills, now))
        self.db.commit()
        return cursor.lastrowid

    def delete_agent(self, agent_id: int):
        self.db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        self.db.execute("DELETE FROM agent_tasks WHERE agent_id = ?", (agent_id,))
        self.db.commit()

    def assign_task(self, agent_id: int, title: str, description: str = "", priority: str = "Medium", due_date: str = "Today") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO agent_tasks (agent_id, title, description, priority, status, due_date, created_at)
            VALUES (?, ?, ?, ?, 'Pending', ?, ?)
        """, (agent_id, title, description, priority, due_date, now))
        self.db.commit()
        return cursor.lastrowid

    def get_tasks(self, agent_id: int | None = None, status: str | None = None) -> list[dict]:
        cursor = self.db.cursor()
        query = """
            SELECT t.id, t.agent_id, a.name as agent_name, a.avatar as agent_avatar,
                   t.title, t.description, t.priority, t.status, t.due_date, t.result, t.created_at
            FROM agent_tasks t
            LEFT JOIN agents a ON a.id = t.agent_id
        """
        params = []
        conditions = []
        if agent_id:
            conditions.append("t.agent_id = ?")
            params.append(agent_id)
        if status:
            conditions.append("t.status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.id DESC"

        cursor.execute(query, tuple(params))
        cols = ["id", "agent_id", "agent_name", "agent_avatar", "title", "description", "priority", "status", "due_date", "result", "created_at"]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def update_task_status(self, task_id: int, status: str, result: str = ""):
        self.db.execute("UPDATE agent_tasks SET status = ?, result = ? WHERE id = ?", (status, result, task_id))
        self.db.commit()

    def delete_task(self, task_id: int):
        self.db.execute("DELETE FROM agent_tasks WHERE id = ?", (task_id,))
        self.db.commit()
