"""System observability, health status, and Prometheus metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.queue import get_job_queue

router = APIRouter(tags=["System"])

# Prometheus Metrics Definitions
JOB_DURATION_HISTOGRAM = Histogram(
    "patchlens_job_duration_seconds",
    "Time taken to execute binary diffing analysis jobs",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 180.0),
)
JOBS_TOTAL_COUNTER = Counter(
    "patchlens_jobs_total",
    "Total number of analysis jobs processed",
    ["status"],
)
QUEUE_DEPTH_GAUGE = Gauge(
    "patchlens_queue_depth",
    "Current number of waiting jobs in the analysis queue",
)


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str | int]:
    """Health check validating API availability, database connection, and worker queue."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    queue = get_job_queue()
    depth = queue.get_queue_depth()
    QUEUE_DEPTH_GAUGE.set(depth)

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.project_name,
        "version": settings.version,
        "database": db_status,
        "queue_depth": depth,
    }


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    queue = get_job_queue()
    QUEUE_DEPTH_GAUGE.set(queue.get_queue_depth())
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
