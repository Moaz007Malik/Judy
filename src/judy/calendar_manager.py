from __future__ import annotations
import sqlite3
from datetime import datetime, date
from pathlib import Path
from .config import APP_DIR

DB_PATH = APP_DIR / "calendar.sqlite3"

DEFAULT_EVENTS = [
    ("Daily Standup & AI Sync", "09:30 AM", "Briefing", "Sync with active agents on code tasks and client pipeline.", 1),
    ("Finalize HUD Panel Spacing", "12:00 PM", "Development", "Review glassmorphism margins and UI contrast.", 0),
    ("Deep-Work Block: Voice Pipeline", "02:00 PM", "Deep Work", "Test real-time wake word latency and neural voice.", 0),
    ("Design Review — Command Center V1", "04:30 PM", "Review", "Demonstrate Command Center features and agent task delegation.", 0)
]

class CalendarManager:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                event_date TEXT,
                event_time TEXT,
                category TEXT DEFAULT 'General',
                description TEXT,
                is_completed INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        self.db.commit()

        # Seed initial events for today if empty
        count = self.db.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
        if count == 0:
            today_str = date.today().isoformat()
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for title, time_str, cat, desc, done in DEFAULT_EVENTS:
                self.db.execute("""
                    INSERT INTO calendar_events (title, event_date, event_time, category, description, is_completed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, today_str, time_str, cat, desc, done, now))
            self.db.commit()

    def add_event(self, title: str, event_date: str, event_time: str = "12:00 PM", category: str = "General", description: str = "") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO calendar_events (title, event_date, event_time, category, description, is_completed, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        """, (title, event_date, event_time, category, description, now))
        self.db.commit()
        return cursor.lastrowid

    def get_events(self, target_date: str | None = None) -> list[dict]:
        cursor = self.db.cursor()
        if target_date:
            cursor.execute("SELECT id, title, event_date, event_time, category, description, is_completed, created_at FROM calendar_events WHERE event_date = ? ORDER BY event_time ASC", (target_date,))
        else:
            cursor.execute("SELECT id, title, event_date, event_time, category, description, is_completed, created_at FROM calendar_events ORDER BY event_date ASC, event_time ASC")
        cols = ["id", "title", "event_date", "event_time", "category", "description", "is_completed", "created_at"]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_today_timeline(self) -> list[dict]:
        today_str = date.today().isoformat()
        events = self.get_events(today_str)
        if not events:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for title, time_str, cat, desc, done in DEFAULT_EVENTS:
                self.db.execute("""
                    INSERT INTO calendar_events (title, event_date, event_time, category, description, is_completed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, today_str, time_str, cat, desc, done, now))
            self.db.commit()
            events = self.get_events(today_str)
        return events

    def toggle_completed(self, event_id: int):
        self.db.execute("UPDATE calendar_events SET is_completed = 1 - is_completed WHERE id = ?", (event_id,))
        self.db.commit()

    def delete_event(self, event_id: int):
        self.db.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        self.db.commit()
