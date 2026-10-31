"""Pre-populates database with sample analyses for instant demo loading."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from api.models import AnalysisJob, AnalysisResultRecord, BinaryRecord
from api.worker_task import execute_analysis_job

logger = logging.getLogger("patchlens.seed")

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def _calc_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def seed_sample_analyses(db: Session) -> None:
    """Ensure standard CVE sample cases exist in the database."""
    # Sample 1: zlib CVE-2018-25032
    z_a = CORPUS_DIR / "binaries" / "libz-1.2.11-gcc-O2-stripped.so"
    z_b = CORPUS_DIR / "binaries" / "libz-1.2.12-gcc-O2-stripped.so"

    if z_a.is_file() and z_b.is_file():
        sha_za = _calc_sha256(z_a)
        sha_zb = _calc_sha256(z_b)
        pair_hash = f"{sha_za}_{sha_zb}"

        existing_res = (
            db.query(AnalysisResultRecord)
            .filter(AnalysisResultRecord.pair_hash == pair_hash)
            .first()
        )
        if not existing_res:
            logger.info("Seeding sample analysis: zlib CVE-2018-25032...")
            rec_a = db.query(BinaryRecord).filter(BinaryRecord.sha256 == sha_za).first()
            if not rec_a:
                rec_a = BinaryRecord(
                    sha256=sha_za,
                    filename=z_a.name,
                    file_size=z_a.stat().st_size,
                    file_path=str(z_a),
                    arch="x86_64",
                    is_stripped=True,
                )
                db.add(rec_a)
                db.flush()

            rec_b = db.query(BinaryRecord).filter(BinaryRecord.sha256 == sha_zb).first()
            if not rec_b:
                rec_b = BinaryRecord(
                    sha256=sha_zb,
                    filename=z_b.name,
                    file_size=z_b.stat().st_size,
                    file_path=str(z_b),
                    arch="x86_64",
                    is_stripped=True,
                )
                db.add(rec_b)
                db.flush()

            job_id = "sample-zlib-cve-2018-25032"
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                job = AnalysisJob(
                    id=job_id,
                    status="pending",
                    progress=0,
                    current_stage="queued",
                    binary_a_id=rec_a.id,
                    binary_b_id=rec_b.id,
                )
                db.add(job)
                db.commit()

            execute_analysis_job(job_id)
            logger.info("Seeded sample analysis: zlib CVE-2018-25032 successfully")

    # Sample 2: cJSON CVE-2019-1010239
    c_a = CORPUS_DIR / "cjson" / "binaries" / "libcjson-1.7.11-gcc-O2-stripped.so"
    c_b = CORPUS_DIR / "cjson" / "binaries" / "libcjson-1.7.12-gcc-O2-stripped.so"

    if c_a.is_file() and c_b.is_file():
        sha_ca = _calc_sha256(c_a)
        sha_cb = _calc_sha256(c_b)
        pair_hash_c = f"{sha_ca}_{sha_cb}"

        existing_c = (
            db.query(AnalysisResultRecord)
            .filter(AnalysisResultRecord.pair_hash == pair_hash_c)
            .first()
        )
        if not existing_c:
            logger.info("Seeding sample analysis: cJSON CVE-2019-1010239...")
            rec_ca = db.query(BinaryRecord).filter(BinaryRecord.sha256 == sha_ca).first()
            if not rec_ca:
                rec_ca = BinaryRecord(
                    sha256=sha_ca,
                    filename=c_a.name,
                    file_size=c_a.stat().st_size,
                    file_path=str(c_a),
                    arch="x86_64",
                    is_stripped=True,
                )
                db.add(rec_ca)
                db.flush()

            rec_cb = db.query(BinaryRecord).filter(BinaryRecord.sha256 == sha_cb).first()
            if not rec_cb:
                rec_cb = BinaryRecord(
                    sha256=sha_cb,
                    filename=c_b.name,
                    file_size=c_b.stat().st_size,
                    file_path=str(c_b),
                    arch="x86_64",
                    is_stripped=True,
                )
                db.add(rec_cb)
                db.flush()

            job_id_c = "sample-cjson-cve-2019-1010239"
            job_c = db.query(AnalysisJob).filter(AnalysisJob.id == job_id_c).first()
            if not job_c:
                job_c = AnalysisJob(
                    id=job_id_c,
                    status="pending",
                    progress=0,
                    current_stage="queued",
                    binary_a_id=rec_ca.id,
                    binary_b_id=rec_cb.id,
                )
                db.add(job_c)
                db.commit()

            execute_analysis_job(job_id_c)
            logger.info("Seeded sample analysis: cJSON CVE-2019-1010239 successfully")


if __name__ == "__main__":
    from api.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    seed_sample_analyses(session)
    session.close()
