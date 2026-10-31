"""Endpoints for uploading ELF binaries, starting analysis jobs, and streaming progress."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from elftools.elf.elffile import ELFFile
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.models import AnalysisJob, AnalysisResultRecord, BinaryRecord
from api.queue import get_job_queue, register_subscriber, unregister_subscriber
from api.schemas import BinaryUploadResponse, JobStatusResponse, StartAnalysisRequest

logger = logging.getLogger("patchlens.api.analysis")
router = APIRouter(tags=["Analysis"])


@router.post(
    "/binaries/upload", response_model=BinaryUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_binary(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BinaryUploadResponse:
    """Upload and validate an ELF binary.

    Validates:
    1. Maximum file size limit (default 50MB)
    2. ELF magic header (0x7f 'E' 'L' 'F')
    3. Architecture and symbol table existence
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Binary exceeds maximum allowed size of {settings.max_upload_size_mb} MB",
        )

    # Magic bytes check
    if len(content) < 4 or content[:4] != b"\x7fELF":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid binary file: missing ELF magic header (\\x7fELF). "
                "Only ELF binaries are accepted."
            ),
        )

    sha256 = hashlib.sha256(content).hexdigest()

    # Check if duplicate binary already exists
    existing = db.query(BinaryRecord).filter(BinaryRecord.sha256 == sha256).first()
    if existing and Path(existing.file_path).is_file():
        return BinaryUploadResponse.model_validate(existing)

    # Save to disk under unique name
    clean_filename = Path(file.filename or "binary.so").name
    dest_path = settings.upload_dir / f"{uuid.uuid4().hex}_{clean_filename}"
    dest_path.write_bytes(content)

    # Parse metadata with pyelftools
    arch = "x86_64"
    is_stripped = True
    entry_point = 0
    try:
        with open(dest_path, "rb") as f:
            elf = ELFFile(f)
            machine = elf.header.get("e_machine", "")
            if "AARCH64" in machine or "ARM64" in machine:
                arch = "aarch64"
            elif "X86_64" in machine or "AMD64" in machine:
                arch = "x86_64"
            else:
                arch = str(machine)

            entry_point = elf.header.get("e_entry", 0)
            symtab = elf.get_section_by_name(".symtab")
            if symtab is not None and symtab.num_symbols() > 0:
                is_stripped = False
    except Exception as exc:
        logger.warning("Failed parsing ELF header details: %s", exc)

    record = BinaryRecord(
        sha256=sha256,
        filename=clean_filename,
        file_size=len(content),
        file_path=str(dest_path),
        arch=arch,
        is_stripped=is_stripped,
        entry_point=entry_point,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return BinaryUploadResponse.model_validate(record)


@router.post("/analyses/start", response_model=JobStatusResponse)
def start_analysis(
    req: StartAnalysisRequest,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """Initiate an asynchronous diffing and security patch analysis job."""
    bin_a = db.query(BinaryRecord).filter(BinaryRecord.id == req.binary_a_id).first()
    bin_b = db.query(BinaryRecord).filter(BinaryRecord.id == req.binary_b_id).first()
    if not bin_a or not bin_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both binary records not found",
        )

    pair_hash = f"{bin_a.sha256}_{bin_b.sha256}"
    existing_result = (
        db.query(AnalysisResultRecord).filter(AnalysisResultRecord.pair_hash == pair_hash).first()
    )

    job_id = f"job-{uuid.uuid4().hex[:12]}"

    if existing_result:
        # Instant return from cached analysis
        job = AnalysisJob(
            id=job_id,
            status="completed",
            progress=100,
            current_stage="completed",
            stage_details="Instant retrieval from hash pair cache",
            binary_a_id=bin_a.id,
            binary_b_id=bin_b.id,
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            current_stage=job.current_stage,
            stage_details=job.stage_details,
            error_message=job.error_message,
            binary_a_id=job.binary_a_id,
            binary_b_id=job.binary_b_id,
            result_id=existing_result.id,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )

    # Create new pending job and enqueue
    job = AnalysisJob(
        id=job_id,
        status="pending",
        progress=0,
        current_stage="queued",
        stage_details="Waiting for worker process",
        binary_a_id=bin_a.id,
        binary_b_id=bin_b.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    queue = get_job_queue()
    queue.enqueue(job_id)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        stage_details=job.stage_details,
        error_message=job.error_message,
        binary_a_id=job.binary_a_id,
        binary_b_id=job.binary_b_id,
        result_id=None,
        created_at=job.created_at.isoformat(),
        completed_at=None,
    )


@router.get("/analyses/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    """Fetch current status and progress of an analysis job."""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {job_id} not found",
        )

    result_id = None
    if job.status == "completed":
        bin_a = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_a_id).first()
        bin_b = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_b_id).first()
        if bin_a and bin_b:
            pair_hash = f"{bin_a.sha256}_{bin_b.sha256}"
            res = (
                db.query(AnalysisResultRecord)
                .filter(AnalysisResultRecord.pair_hash == pair_hash)
                .first()
            )
            if res:
                result_id = res.id

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        stage_details=job.stage_details,
        error_message=job.error_message,
        binary_a_id=job.binary_a_id,
        binary_b_id=job.binary_b_id,
        result_id=result_id,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("/analyses/{job_id}/stream")
async def stream_job_progress(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """Server-Sent Events (SSE) endpoint streaming stage-by-stage analysis progress."""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        queue: asyncio.Queue[dict[str, str | int]] = asyncio.Queue()
        register_subscriber(job_id, queue)
        try:
            # Yield initial state
            initial_data = {
                "job_id": job.id,
                "stage": job.current_stage,
                "progress": job.progress,
                "details": job.stage_details or "",
                "status": job.status,
            }
            yield f"data: {json.dumps(initial_data)}\n\n"

            if job.status in ("completed", "failed"):
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if (
                        event.get("stage") in ("completed", "failed")
                        or event.get("progress") == 100
                    ):
                        break
                except TimeoutError:
                    # Heartbeat
                    yield ": ping\n\n"

                # Check DB directly in case event was missed
                db.expire(job)
                if job.status in ("completed", "failed"):
                    final_data = {
                        "job_id": job.id,
                        "stage": job.current_stage,
                        "progress": job.progress,
                        "details": job.stage_details or "",
                        "status": job.status,
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break
        finally:
            unregister_subscriber(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/analyses/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str, db: Session = Depends(get_db)):
    """WebSocket endpoint streaming real-time stage updates to clients."""
    await websocket.accept()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    queue: asyncio.Queue[dict[str, str | int]] = asyncio.Queue()
    register_subscriber(job_id, queue)
    try:
        await websocket.send_json(
            {
                "job_id": job.id,
                "stage": job.current_stage,
                "progress": job.progress,
                "details": job.stage_details or "",
                "status": job.status,
            }
        )

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(event)
                if event.get("stage") in ("completed", "failed"):
                    break
            except TimeoutError:
                await websocket.send_json({"type": "ping"})

            db.expire(job)
            if job.status in ("completed", "failed"):
                await websocket.send_json(
                    {
                        "job_id": job.id,
                        "stage": job.current_stage,
                        "progress": job.progress,
                        "status": job.status,
                    }
                )
                break
    except WebSocketDisconnect:
        pass
    finally:
        unregister_subscriber(job_id, queue)
