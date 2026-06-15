"""Factory for creating the appropriate JobQueue backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import AppSettings
    from app.queue.base import JobQueue


def create_queue(settings: AppSettings) -> JobQueue:
    """Return a configured :class:`JobQueue` for the given settings.

    Raises:
        ValueError: If ``queue_backend`` is not ``"database"`` or ``"redis"``.
        ImportError: If the ``redis`` package is not installed and ``"redis"``
            is selected.
    """
    backend = settings.queue_backend.lower()

    if backend == "database":
        from app.queue.db_queue import SQLiteJobQueue

        return SQLiteJobQueue(
            storage_path=settings.storage_path,
            max_size=settings.queue_max_size,
        )

    if backend == "redis":
        try:
            from app.queue.redis_queue import RedisJobQueue
        except ImportError as exc:
            raise ImportError(
                "The 'redis' package is required for the Redis queue backend. Install it with: pip install redis"
            ) from exc

        return RedisJobQueue(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            max_size=settings.queue_max_size,
        )

    raise ValueError(f"Unknown queue_backend {backend!r}. Expected 'database' or 'redis'.")
