import sqlite3
from pathlib import Path
from typing import List, Tuple


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  title_simhash TEXT NOT NULL,
  source TEXT NOT NULL,
  publish_time TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_title_simhash ON articles(title_simhash);
CREATE INDEX IF NOT EXISTS idx_articles_publish_time ON articles(publish_time);
"""


class ArticleDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def has_url(self, url: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM articles WHERE url=? LIMIT 1", (url,))
        return cur.fetchone() is not None

    def insert_article(self, *, url: str, title: str, title_simhash: str, source: str, publish_time: str, created_at: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO articles(url,title,title_simhash,source,publish_time,created_at) VALUES (?,?,?,?,?,?)",
            (url, title, title_simhash, source, publish_time, created_at),
        )
        self.conn.commit()

    def get_recent_urls(self, *, since_iso: str, limit: int = 200) -> List[str]:
        cur = self.conn.execute(
            "SELECT url FROM articles WHERE publish_time>=? ORDER BY publish_time DESC LIMIT ?",
            (since_iso, limit),
        )
        return [r[0] for r in cur.fetchall()]

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
