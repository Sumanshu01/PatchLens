"""Endpoints listing pre-computed sample CVE cases for instant demo exploration."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import AnalysisJob, AnalysisResultRecord, BinaryRecord
from api.schemas import SampleCaseSchema

router = APIRouter(tags=["Samples"])


@router.get("/samples", response_model=list[SampleCaseSchema])
def list_sample_cases(db: Session = Depends(get_db)) -> list[SampleCaseSchema]:
    """Return available pre-seeded CVE sample analyses with their result IDs."""
    samples = [
        {
            "id": "zlib-cve-2018-25032",
            "title": "zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)",
            "description": "Out-of-bounds write in deflate.c patched across deflate functions",
            "cve": "CVE-2018-25032",
            "binary_a_name": "libz-1.2.11-gcc-O2-stripped.so",
            "binary_b_name": "libz-1.2.12-gcc-O2-stripped.so",
            "job_id": "sample-zlib-cve-2018-25032",
        },
        {
            "id": "cjson-cve-2019-1010239",
            "title": "cJSON 1.7.11 -> 1.7.12 (CVE-2019-1010239)",
            "description": "Buffer over-read and infinite loop fix localized to cJSON_Minify",
            "cve": "CVE-2019-1010239",
            "binary_a_name": "libcjson-1.7.11-gcc-O2-stripped.so",
            "binary_b_name": "libcjson-1.7.12-gcc-O2-stripped.so",
            "job_id": "sample-cjson-cve-2019-1010239",
        },
    ]

    results: list[SampleCaseSchema] = []
    for s in samples:
        res_id = None
        pair_hash = ""
        job = db.query(AnalysisJob).filter(AnalysisJob.id == s["job_id"]).first()
        if job and job.status == "completed":
            bin_a = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_a_id).first()
            bin_b = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_b_id).first()
            if bin_a and bin_b:
                pair_hash = f"{bin_a.sha256}_{bin_b.sha256}"
                r_rec = (
                    db.query(AnalysisResultRecord)
                    .filter(AnalysisResultRecord.pair_hash == pair_hash)
                    .first()
                )
                if r_rec:
                    res_id = r_rec.id

        results.append(
            SampleCaseSchema(
                id=s["id"],
                title=s["title"],
                description=s["description"],
                cve=s["cve"],
                binary_a_name=s["binary_a_name"],
                binary_b_name=s["binary_b_name"],
                pair_hash=pair_hash,
                result_id=res_id,
            )
        )

    return results
