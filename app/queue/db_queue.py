"""Database-backed job queue (SQLite and PostgreSQL).

Both backends share the same table schema and SQL semantics.  The key
difference is the locking strategy used during dequeue:

* SQLite  - ``BEGIN EXCLUSIVE`` serialises all writers at the DB level.
* PostgreSQL - ``SELECT ... FOR UPDATE SKIP LOCKED`` allows multiple workers
  to dequeue concurrently without blocking each other.

Jobs are deleted from the table when ``complete()`` is called, so
"absent from the table" naturally means "done" for ``position()`` queries.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from pathlib import Path
from typing import Any

from app.queue.base import Job

# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------


class SQLiteJobQueue:
    """Job queue backed by a SQLite database."""

    def __init__(self, storage_path: str, max_size: int) -> None:
        db_dir = Path(storage_path)
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_dir / "queue.db")
        self._max_size = max_size
        self._lock = threading.RLock()
        self._init_table()

    # ------------------------------------------------------------------
    # JobQueue protocol
    # ------------------------------------------------------------------

    async def enqueue(self, job_type: str, photo_id: str, payload: str) -> bool:
        return await asyncio.to_thread(self._enqueue_sync, job_type, photo_id, payload)

    async def dequeue(self) -> Job | None:
        return await asyncio.to_thread(self._dequeue_sync)

    async def complete(self, job_id: int) -> None:
        await asyncio.to_thread(self._complete_sync, job_id)

    async def size(self) -> int:
        return await asyncio.to_thread(self._size_sync)

    async def purge(self) -> None:
        await asyncio.to_thread(self._purge_sync)

    async def position(self, photo_id: str) -> int | None:
        return await asyncio.to_thread(self._position_sync, photo_id)

    async def close(self) -> None:
        pass  # SQLite connections are opened/closed per operation

    # ------------------------------------------------------------------
    # Sync helpers (run in a thread via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _connect(self) -> Any:
        import sqlite3

        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _init_table(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS job_queue (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_type   TEXT    NOT NULL,
                        photo_id   TEXT    NOT NULL,
                        payload    TEXT    NOT NULL,
                        status     TEXT    NOT NULL DEFAULT 'pending',
                        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS job_queue_status_idx ON job_queue(status, id)")
                # Recover jobs that were processing when the service last crashed.
                conn.execute("UPDATE job_queue SET status = 'pending' WHERE status = 'processing'")
                conn.commit()
            finally:
                conn.close()

    def _enqueue_sync(self, job_type: str, photo_id: str, payload: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT COUNT(*) FROM job_queue WHERE status = 'pending'").fetchone()
                if row and row[0] >= self._max_size and self._max_size > 0:
                    return False
                conn.execute(
                    "INSERT INTO job_queue (job_type, photo_id, payload) VALUES (?, ?, ?)",
                    [job_type, photo_id, payload],
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def _dequeue_sync(self) -> Job | None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN EXCLUSIVE")
                row = conn.execute(
                    "SELECT id, job_type, photo_id, payload FROM job_queue WHERE status = 'pending' ORDER BY id LIMIT 1"
                ).fetchone()
                if row is None:
                    conn.execute("ROLLBACK")
                    return None
                job_id, job_type, photo_id, payload = row
                conn.execute("UPDATE job_queue SET status = 'processing' WHERE id = ?", [job_id])
                conn.execute("COMMIT")
                return Job(id=job_id, job_type=job_type, photo_id=photo_id, payload=payload)
            except Exception:
                with contextlib.suppress(Exception):
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()

    def _complete_sync(self, job_id: int) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM job_queue WHERE id = ?", [job_id])
                conn.commit()
            finally:
                conn.close()

    def _size_sync(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM job_queue WHERE status = 'pending'").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    def _purge_sync(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM job_queue WHERE status = 'pending'")
                conn.commit()
            finally:
                conn.close()

    def _position_sync(self, photo_id: str) -> int | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, status FROM job_queue WHERE photo_id = ? "
                "AND status IN ('pending', 'processing') ORDER BY id LIMIT 1",
                [photo_id],
            ).fetchone()
            if row is None:
                return None
            job_id, status = row
            if status == "processing":
                return 0
            count = conn.execute(
                "SELECT COUNT(*) FROM job_queue WHERE status = 'pending' AND id <= ?",
                [job_id],
            ).fetchone()
            return int(count[0]) if count else 1
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# PostgreSQL backend
# ---------------------------------------------------------------------------


class PgJobQueue:
    """Job queue backed by a PostgreSQL database."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        max_size: int,
    ) -> None:
        self._dsn = f"host={host} port={port} dbname={database} user={user} password={password}"
        self._max_size = max_size
        self._lock = threading.RLock()
        self._conn: Any = None
        self._init_table()

    # ------------------------------------------------------------------
    # JobQueue protocol
    # ------------------------------------------------------------------

    async def enqueue(self, job_type: str, photo_id: str, payload: str) -> bool:
        return await asyncio.to_thread(self._enqueue_sync, job_type, photo_id, payload)

    async def dequeue(self) -> Job | None:
        return await asyncio.to_thread(self._dequeue_sync)

    async def complete(self, job_id: int) -> None:
        await asyncio.to_thread(self._complete_sync, job_id)

    async def size(self) -> int:
        return await asyncio.to_thread(self._size_sync)

    async def purge(self) -> None:
        await asyncio.to_thread(self._purge_sync)

    async def position(self, photo_id: str) -> int | None:
        return await asyncio.to_thread(self._position_sync, photo_id)

    async def close(self) -> None:
        with self._lock:
            if self._conn is not None and not self._conn.closed:
                self._conn.close()
                self._conn = None

    # ------------------------------------------------------------------
    # Sync helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> Any:
        import psycopg2

        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self._dsn)
        return self._conn

    def _init_table(self) -> None:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS job_queue (
                        id         SERIAL PRIMARY KEY,
                        job_type   TEXT   NOT NULL,
                        photo_id   TEXT   NOT NULL,
                        payload    TEXT   NOT NULL,
                        status     TEXT   NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS job_queue_status_idx ON job_queue(status, id)")
                cur.execute("UPDATE job_queue SET status = 'pending' WHERE status = 'processing'")
            conn.commit()

    def _enqueue_sync(self, job_type: str, photo_id: str, payload: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM job_queue WHERE status = 'pending'")
                row = cur.fetchone()
                if row and row[0] >= self._max_size and self._max_size > 0:
                    return False
                cur.execute(
                    "INSERT INTO job_queue (job_type, photo_id, payload) VALUES (%s, %s, %s)",
                    (job_type, photo_id, payload),
                )
            conn.commit()
            return True

    def _dequeue_sync(self) -> Job | None:
        with self._lock:
            conn = self._get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, job_type, photo_id, payload FROM job_queue "
                        "WHERE status = 'pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
                    )
                    row = cur.fetchone()
                    if row is None:
                        conn.rollback()
                        return None
                    job_id, job_type, photo_id, payload = row
                    cur.execute("UPDATE job_queue SET status = 'processing' WHERE id = %s", (job_id,))
                conn.commit()
                return Job(id=job_id, job_type=job_type, photo_id=photo_id, payload=payload)
            except Exception:
                conn.rollback()
                raise

    def _complete_sync(self, job_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM job_queue WHERE id = %s", (job_id,))
            conn.commit()

    def _size_sync(self) -> int:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM job_queue WHERE status = 'pending'")
                row = cur.fetchone()
            return int(row[0]) if row else 0

    def _purge_sync(self) -> None:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM job_queue WHERE status = 'pending'")
            conn.commit()

    def _position_sync(self, photo_id: str) -> int | None:
        with self._lock:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, status FROM job_queue WHERE photo_id = %s "
                    "AND status IN ('pending', 'processing') ORDER BY id LIMIT 1",
                    (photo_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                job_id, status = row
                if status == "processing":
                    return 0
                cur.execute(
                    "SELECT COUNT(*) FROM job_queue WHERE status = 'pending' AND id <= %s",
                    (job_id,),
                )
                count = cur.fetchone()
            return int(count[0]) if count else 1
