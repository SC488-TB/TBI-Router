"""SQLite access for the cache and the cost log.

Python 3.9's sqlite build crashes if two threads use one connection, even
behind a lock. Each call opens its own connection. WAL lets a dashboard read
run next to a write.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class LockedConnection:
    """File path: one connection per call. Memory: one connection, tests only."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._memory = None
        if path == ":memory:":
            self._memory = sqlite3.connect(path, check_same_thread=False)
            self._memory.row_factory = sqlite3.Row
            self._memory.text_factory = _text

    def _open(self) -> sqlite3.Connection:
        if self._memory is not None:
            return self._memory
        conn = sqlite3.connect(self._path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.text_factory = _text
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def execute(self, sql: str, params: tuple = ()):
        own = self._memory is None
        conn = self._open()
        try:
            cursor = conn.execute(sql, params)
            if own:
                rows = cursor.fetchall()
                conn.commit()
                return _Rows(rows)
            return cursor
        finally:
            if own:
                conn.close()

    def executescript(self, sql: str) -> None:
        own = self._memory is None
        conn = self._open()
        try:
            conn.executescript(sql)
            if own:
                conn.commit()
        finally:
            if own:
                conn.close()

    def commit(self) -> None:
        if self._memory is not None:
            self._memory.commit()


class _Rows:
    """fetchall() already ran. Callers still call fetchall() or fetchone()."""

    def __init__(self, rows) -> None:
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


def connect(path: str) -> LockedConnection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return LockedConnection(path)


def _text(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")
