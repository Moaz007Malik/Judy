from pathlib import Path
from judy.config import Settings
from judy.file_index import FileIndex

def test_index_and_search(tmp_path, monkeypatch):
    monkeypatch.setattr("judy.file_index.DB_PATH", tmp_path / "files.sqlite3")
    monkeypatch.setattr("judy.file_index.APP_DIR", tmp_path)
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "university-notes.txt").write_text("attestation university documents", encoding="utf-8")
    idx = FileIndex()
    s = Settings(search_roots=[str(folder)], excluded_paths=[], indexed_extensions=[".txt"])
    n, e = idx.scan(s)
    assert n == 1 and e == 0
    assert idx.search("attestation")
    idx.close()
