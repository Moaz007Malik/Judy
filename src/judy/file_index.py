from __future__ import annotations
import os, sqlite3, re
from pathlib import Path
from .config import APP_DIR, Settings

DB_PATH = APP_DIR / "files.sqlite3"

class FileIndex:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, name TEXT, ext TEXT, modified REAL, size INTEGER, content TEXT)")
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(path UNINDEXED, name, content, tokenize='unicode61')")
        # Persistent checkpoint table to enable resuming interrupted indexing
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS index_checkpoint (
                path TEXT PRIMARY KEY,
                name TEXT,
                ext TEXT,
                mtime REAL,
                size INTEGER,
                status TEXT DEFAULT 'pending'
            )
        """)
        self.db.commit()

    def get_checkpoint_stats(self) -> tuple[int, int]:
        """Returns (completed_or_skipped_count, total_count)."""
        try:
            total = self.db.execute("SELECT COUNT(*) FROM index_checkpoint").fetchone()[0]
            done = self.db.execute("SELECT COUNT(*) FROM index_checkpoint WHERE status != 'pending'").fetchone()[0]
            return done, total
        except Exception:
            return 0, 0

    def clear_checkpoint(self):
        try:
            self.db.execute("DELETE FROM index_checkpoint")
            self.db.commit()
        except Exception:
            pass

    def _extract(self, p: Path, max_bytes: int) -> str:
        try:
            if p.stat().st_size > max_bytes:
                return ""
            ext = p.suffix.lower()
            if ext in (".txt", ".md", ".csv", ".log"):
                return p.read_text(encoding="utf-8", errors="ignore")[:200000]
            if ext == ".pdf":
                from pypdf import PdfReader
                return "\n".join((page.extract_text() or "") for page in PdfReader(str(p)).pages[:80])[:200000]
            if ext == ".docx":
                from docx import Document
                doc = Document(str(p))
                return "\n".join(x.text for x in doc.paragraphs)[:200000]
        except Exception:
            return ""
        return ""

    def scan(self, settings: Settings, progress=None, should_cancel=None) -> tuple[int, int, bool]:
        """
        Scans and indexes files with live percentage progress and automatic checkpoint resume.
        Returns: (indexed_count, error_count, was_interrupted)
        """
        indexed = 0
        errors = 0
        max_bytes = max(1, settings.max_file_mb) * 1024 * 1024
        excludes = [x.lower() for x in settings.excluded_paths]

        # Check if there is an existing pending checkpoint to resume from
        done_count, total_count = self.get_checkpoint_stats()
        has_pending = False
        if total_count > 0:
            pending_count = self.db.execute("SELECT COUNT(*) FROM index_checkpoint WHERE status = 'pending'").fetchone()[0]
            if pending_count > 0:
                has_pending = True

        # Phase 1: Fast file discovery if no active checkpoint exists
        if not has_pending:
            self.clear_checkpoint()
            roots = [Path(x) for x in settings.search_roots if Path(x).exists()]
            discovered = []
            for root in roots:
                for dirpath, dirs, names in os.walk(root, topdown=True, onerror=lambda e: None):
                    if should_cancel and should_cancel():
                        return 0, 0, True
                    dirs[:] = [d for d in dirs if d.lower() not in excludes and not any(str(Path(dirpath, d)).lower().startswith(e) for e in excludes)]
                    for name in names:
                        p = Path(dirpath, name)
                        ext = p.suffix.lower()
                        if ext not in settings.indexed_extensions:
                            continue
                        try:
                            st = p.stat()
                            discovered.append((str(p), p.name, ext, st.st_mtime, st.st_size, "pending"))
                        except Exception:
                            continue

            if not discovered:
                return 0, 0, False

            # Check existing files to skip unmodified ones
            existing_rows = dict(self.db.execute("SELECT path, modified FROM files").fetchall())
            to_insert = []
            for path_str, name, ext, mtime, size, status in discovered:
                if path_str in existing_rows and abs(existing_rows[path_str] - mtime) < 0.01:
                    to_insert.append((path_str, name, ext, mtime, size, "skipped"))
                else:
                    to_insert.append((path_str, name, ext, mtime, size, "pending"))

            self.db.executemany("""
                INSERT OR REPLACE INTO index_checkpoint (path, name, ext, mtime, size, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, to_insert)
            self.db.commit()

        # Phase 2: Index pending files with live progress
        done_count, total_count = self.get_checkpoint_stats()
        if total_count == 0:
            total_count = 1

        pending_rows = self.db.execute("""
            SELECT path, name, ext, mtime, size FROM index_checkpoint WHERE status = 'pending'
        """).fetchall()

        batch_count = 0
        for path_str, name, ext, mtime, size in pending_rows:
            if should_cancel and should_cancel():
                self.db.commit()
                return indexed, errors, True

            p = Path(path_str)
            try:
                if not p.exists():
                    self.db.execute("UPDATE index_checkpoint SET status = 'missing' WHERE path = ?", (path_str,))
                else:
                    content = self._extract(p, max_bytes)
                    self.db.execute("INSERT OR REPLACE INTO files(path, name, ext, modified, size, content) VALUES(?,?,?,?,?,?)",
                                    (path_str, name, ext, mtime, size, content))
                    self.db.execute("DELETE FROM files_fts WHERE path=?", (path_str,))
                    self.db.execute("INSERT INTO files_fts(path, name, content) VALUES(?,?,?)",
                                    (path_str, name, content))
                    self.db.execute("UPDATE index_checkpoint SET status = 'indexed' WHERE path = ?", (path_str,))
                    indexed += 1
            except Exception:
                self.db.execute("UPDATE index_checkpoint SET status = 'error' WHERE path = ?", (path_str,))
                errors += 1

            done_count += 1
            batch_count += 1
            percent = min(100.0, round((done_count / total_count) * 100.0, 1))

            if progress:
                progress(done_count, total_count, percent, name)

            if batch_count % 15 == 0:
                self.db.commit()

        self.db.commit()
        # Completed full scan: clear checkpoint
        self.clear_checkpoint()
        return indexed, errors, False

    def search(self, query: str, limit=12) -> list[dict]:
        terms = re.findall(r"[\w.-]+", query)
        if not terms:
            return []
        match = " OR ".join('"' + t.replace('"', '') + '"' for t in terms[:12])
        try:
            rows = self.db.execute("""
                SELECT f.path, f.name, f.ext, f.modified, f.size, snippet(files_fts, 2, '[', ']', '…', 12), bm25(files_fts)
                FROM files_fts JOIN files f ON f.path = files_fts.path
                WHERE files_fts MATCH ? ORDER BY bm25(files_fts) LIMIT ?
            """, (match, limit)).fetchall()
        except sqlite3.Error:
            return []
        return [{"path": r[0], "name": r[1], "ext": r[2], "modified": r[3], "size": r[4], "snippet": r[5]} for r in rows]

    def get_indexed_count(self) -> int:
        try:
            return self.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        except Exception:
            return 0

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

