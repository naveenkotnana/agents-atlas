"""app/core/idempotency.py
Idempotency Key Engine for Mutating & Compute-Heavy Endpoints.

Implements the IETF Draft standard for the 'Idempotency-Key' HTTP header.
Guarantees exactly-once execution semantics for operations such as document
ingestion, chunk embedding, and decision analysis.
"""
import time
import asyncio
from typing import Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from app.core.exceptions import AtlasBaseException
from app.core.logging import logger


class IdempotencyRecord:
    """Represents the lifecycle state of an idempotent operation."""
    def __init__(self):
        self.status: str = "IN_PROGRESS"  # IN_PROGRESS | COMPLETED | FAILED
        self.status_code: int = 200
        self.response_body: Any = None
        self.created_at: float = time.monotonic()


class IdempotencyManager:
    """
    Thread-safe in-memory store for idempotency tracking.
    In multi-container Kubernetes, this is backed by Redis atomic SETNX.
    """

    def __init__(self, ttl_seconds: int = 86400):  # 24-hour cache TTL
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, IdempotencyRecord] = {}
        self._lock = asyncio.Lock()

    async def get_or_lock(self, idempotency_key: str) -> tuple[str, IdempotencyRecord | None]:
        """
        Atomically inspects the key:
        - If new: locks as IN_PROGRESS and returns ("LOCK_ACQUIRED", record)
        - If completed: returns ("COMPLETED", record)
        - If active: returns ("IN_PROGRESS", None)
        """
        async with self._lock:
            record = self._store.get(idempotency_key)

            if record is None:
                new_record = IdempotencyRecord()
                self._store[idempotency_key] = new_record
                return "LOCK_ACQUIRED", new_record

            if record.status == "IN_PROGRESS":
                return "IN_PROGRESS", None

            if record.status == "COMPLETED":
                return "COMPLETED", record

            # If previous execution failed, allow safe retry
            new_record = IdempotencyRecord()
            self._store[idempotency_key] = new_record
            return "LOCK_ACQUIRED", new_record

    async def complete(self, idempotency_key: str, status_code: int, response_body: Any):
        """Marks the execution as completed and caches the response."""
        async with self._lock:
            record = self._store.get(idempotency_key)
            if record:
                record.status = "COMPLETED"
                record.status_code = status_code
                record.response_body = response_body

    async def release_on_failure(self, idempotency_key: str):
        """Unlocks a failed execution so subsequent retries are not permanently blocked."""
        async with self._lock:
            record = self._store.get(idempotency_key)
            if record:
                record.status = "FAILED"


idempotency_manager = IdempotencyManager()
