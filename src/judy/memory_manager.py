from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from .config import APP_DIR

DB_PATH = APP_DIR / "memory.sqlite3"

SEED_MEMORIES = [
    ("User Preference", "Theme & UI", "User prefers ultra-futuristic holographic HUD glassmorphism interfaces with neon cyan/indigo styling.", 0.98),
    ("Identity", "Assistant Persona", "Judy is the primary Executive AI Partner and Autonomous Commander.", 1.0),
    ("Capability", "Voice Speech", "Neural speech synthesis is configured using edge-tts JennyNeural voice for natural human cadence.", 0.95),
    ("Objective", "Client Prospecting", "Automated lead discovery engine targets Web Design, Marketing, and B2B services with cold outreach sequences.", 0.92),
    ("Technical", "Desktop Architecture", "PySide6 Qt6 GUI with multi-agent delegation, SQLite database persistence, and native Windows SAPI.", 0.96),
    ("Workspace", "Documents Directory", "Indexed file roots include local user documents with PDF, DOCX, and TXT extraction.", 0.90)
]

class MemoryManager:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key_topic TEXT,
                content TEXT,
                confidence REAL DEFAULT 0.95,
                source TEXT DEFAULT 'User Input',
                created_at TEXT
            )
        """)
        self.db.commit()

        count = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for cat, topic, content, conf in SEED_MEMORIES:
                self.db.execute("""
                    INSERT INTO memories (category, key_topic, content, confidence, source, created_at)
                    VALUES (?, ?, ?, ?, 'System Initialization', ?)
                """, (cat, topic, content, conf, now))
            self.db.commit()

    def add_memory(self, key_topic: str, content: str, category: str = "General", confidence: float = 0.95, source: str = "User Interaction") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO memories (category, key_topic, content, confidence, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category, key_topic, content, confidence, source, now))
        self.db.commit()
        return cursor.lastrowid

    def get_memories(self, category: str | None = None) -> list[dict]:
        cursor = self.db.cursor()
        if category:
            cursor.execute("SELECT id, category, key_topic, content, confidence, source, created_at FROM memories WHERE category = ? ORDER BY id DESC", (category,))
        else:
            cursor.execute("SELECT id, category, key_topic, content, confidence, source, created_at FROM memories ORDER BY id DESC")
        cols = ["id", "category", "key_topic", "content", "confidence", "source", "created_at"]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def search_memories(self, query: str) -> list[dict]:
        cursor = self.db.cursor()
        like = f"%{query}%"
        cursor.execute("""
            SELECT id, category, key_topic, content, confidence, source, created_at
            FROM memories
            WHERE key_topic LIKE ? OR content LIKE ? OR category LIKE ?
            ORDER BY id DESC
        """, (like, like, like))
        cols = ["id", "category", "key_topic", "content", "confidence", "source", "created_at"]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def delete_memory(self, memory_id: int):
        self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.commit()

    def update_memory(self, memory_id: int, key_topic: str, content: str, category: str = None):
        if category:
            self.db.execute("UPDATE memories SET key_topic = ?, content = ?, category = ? WHERE id = ?", (key_topic, content, category, memory_id))
        else:
            self.db.execute("UPDATE memories SET key_topic = ?, content = ? WHERE id = ?", (key_topic, content, memory_id))
        self.db.commit()

    def get_stats(self) -> dict:
        cursor = self.db.cursor()
        count = cursor.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        cats = [r[0] for r in cursor.execute("SELECT DISTINCT category FROM memories WHERE category IS NOT NULL").fetchall()]
        return {
            "total": count,
            "total_memories": count,
            "categories": cats,
            "session_turns": 0,
            "tool_calls": 0
        }


