"""Asynchronous job execution layer supporting Redis+RQ and in-process execution."""

from __future__ import annotations

import abc
import asyncio
import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor

from api.config import settings
from api.worker_task import execute_analysis_job

logger = logging.getLogger("patchlens.queue")

# Global subscriber registry for SSE / WebSocket real-time progress events:
# job_id -> list of async queue or callback
_subscribers: dict[str, list[asyncio.Queue[dict[str, str | int]]]] = {}


def register_subscriber(job_id: str, queue: asyncio.Queue[dict[str, str | int]]) -> None:
    """Register an async queue to receive live stage progress events for a job."""
    if job_id not in _subscribers:
        _subscribers[job_id] = []
    _subscribers[job_id].append(queue)


def unregister_subscriber(job_id: str, queue: asyncio.Queue[dict[str, str | int]]) -> None:
    """Unregister an async queue when a client disconnects."""
    if job_id in _subscribers:
        if queue in _subscribers[job_id]:
            _subscribers[job_id].remove(queue)
        if not _subscribers[job_id]:
            del _subscribers[job_id]


def broadcast_progress(job_id: str, stage: str, progress: int, details: str = "") -> None:
    """Broadcast a progress event to all active SSE/WebSocket subscribers for a job."""
    if job_id in _subscribers:
        event_payload = {
            "job_id": job_id,
            "stage": stage,
            "progress": progress,
            "details": details,
        }
        for q in _subscribers[job_id]:
            with contextlib.suppress(Exception):
                q.put_nowait(event_payload)


class JobQueue(abc.ABC):
    """Abstract interface for background task dispatchers."""

    @abc.abstractmethod
    def enqueue(self, job_id: str) -> None:
        """Enqueue an analysis job for execution."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_queue_depth(self) -> int:
        """Return the number of waiting jobs in the queue."""
        raise NotImplementedError


class ProcessPoolQueue(JobQueue):
    """In-process asynchronous job queue using thread/process workers."""

    def __init__(self, max_workers: int = 4) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending_count = 0

    def enqueue(self, job_id: str) -> None:
        self.pending_count += 1

        def _task_wrapper() -> None:
            self.pending_count = max(0, self.pending_count - 1)

            def _callback(stage: str, progress: int, details: str) -> None:
                broadcast_progress(job_id, stage, progress, details)

            execute_analysis_job(job_id, progress_callback=_callback)

        self.executor.submit(_task_wrapper)
        logger.info("Enqueued job %s in ProcessPoolQueue", job_id)

    def get_queue_depth(self) -> int:
        return self.pending_count


class RedisRQQueue(JobQueue):
    """Redis-backed job queue using python-rq for production container deployments."""

    def __init__(self, redis_url: str) -> None:
        import redis
        from rq import Queue

        self.redis_conn = redis.Redis.from_url(redis_url)
        self.rq_queue = Queue("patchlens_jobs", connection=self.redis_conn)

    def enqueue(self, job_id: str) -> None:
        self.rq_queue.enqueue(
            execute_analysis_job,
            job_id,
            job_timeout=settings.analysis_timeout_seconds,
        )
        logger.info("Enqueued job %s in RedisRQQueue", job_id)

    def get_queue_depth(self) -> int:
        return len(self.rq_queue)


_GLOBAL_QUEUE: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Return the configured global job queue instance."""
    global _GLOBAL_QUEUE
    if _GLOBAL_QUEUE is None:
        if settings.use_redis:
            try:
                _GLOBAL_QUEUE = RedisRQQueue(settings.redis_url)
                logger.info("Initialized RedisRQQueue at %s", settings.redis_url)
            except Exception as exc:
                logger.warning(
                    "Failed to connect to Redis (%s), falling back to ProcessPoolQueue", exc
                )
                _GLOBAL_QUEUE = ProcessPoolQueue()
        else:
            _GLOBAL_QUEUE = ProcessPoolQueue()
            logger.info("Initialized default ProcessPoolQueue")
    return _GLOBAL_QUEUE
