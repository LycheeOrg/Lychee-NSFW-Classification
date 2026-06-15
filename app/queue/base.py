"""Abstract queue interface and Job dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Job:
    id: int
    job_type: str  # "detect"
    photo_id: str  # Lychee photo ID
    payload: str  # JSON-encoded job arguments


@runtime_checkable
class JobQueue(Protocol):
    async def enqueue(self, job_type: str, photo_id: str, payload: str) -> bool:
        """Add a job to the queue. Returns False when the queue is at capacity."""
        ...

    async def dequeue(self) -> Job | None:
        """Pop the next pending job and mark it as processing. None = queue empty."""
        ...

    async def complete(self, job_id: int) -> None:
        """Remove a job after it has been processed (success or failure)."""
        ...

    async def size(self) -> int:
        """Number of jobs currently pending (not counting in-flight jobs)."""
        ...

    async def purge(self) -> None:
        """Delete all pending jobs. In-flight jobs are not affected."""
        ...

    async def position(self, photo_id: str) -> int | None:
        """1-based rank of photo_id in the pending queue.

        Returns 0 if the job is currently being processed.
        Returns None if the photo_id is not present (absent = done).
        """
        ...

    async def close(self) -> None:
        """Release any held resources."""
        ...
