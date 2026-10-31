"""Comprehensive test suite for PatchLens FastAPI endpoints and background worker."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from api.config import settings
from api.database import SessionLocal, init_db
from api.main import app
from api.seed import seed_sample_analyses
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db() -> None:
    """Ensure database is initialized and samples are seeded before running API tests."""
    init_db()
    db = SessionLocal()
    seed_sample_analyses(db)
    db.close()


def test_health_check_endpoint() -> None:
    """Validate /health endpoint reports connected database and ok status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "PatchLens"
    assert data["database"] == "connected"
    assert "queue_depth" in data


def test_prometheus_metrics_endpoint() -> None:
    """Validate /metrics exports Prometheus counters and histograms."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "patchlens_jobs_total" in res.text
    assert "patchlens_queue_depth" in res.text


def test_upload_non_elf_rejected() -> None:
    """Validate that non-ELF files are rejected with HTTP 400."""
    fake_content = b"This is plain text and definitely not an ELF binary."
    file_payload = {"file": ("malicious.txt", io.BytesIO(fake_content), "application/octet-stream")}
    res = client.post("/api/binaries/upload", files=file_payload)
    assert res.status_code == 400
    assert "missing ELF magic header" in res.json()["detail"]


def test_upload_oversized_file_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that files exceeding max_upload_size_mb are rejected with HTTP 413."""
    # Temporarily set max limit to 1 KB for test
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    large_payload = b"\x7fELF" + b"\x00" * (2 * 1024 * 1024)
    file_payload = {"file": ("huge.so", io.BytesIO(large_payload), "application/octet-stream")}
    res = client.post("/api/binaries/upload", files=file_payload)
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"]


def test_upload_valid_elf(zlib_1211_gcc_o2_stripped: Path) -> None:
    """Validate uploading a genuine ELF binary creates a record with SHA-256."""
    content = zlib_1211_gcc_o2_stripped.read_bytes()
    file_payload = {
        "file": (zlib_1211_gcc_o2_stripped.name, io.BytesIO(content), "application/octet-stream")
    }
    res = client.post("/api/binaries/upload", files=file_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] > 0
    assert len(data["sha256"]) == 64
    assert data["filename"] == zlib_1211_gcc_o2_stripped.name


def test_sample_analyses_instant_retrieval() -> None:
    """Validate pre-seeded sample CVE analyses return instantly (<1s)."""
    res = client.get("/api/samples")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) >= 2

    # Check zlib CVE sample
    zlib_sample = next(s for s in samples if s["id"] == "zlib-cve-2018-25032")
    assert zlib_sample["result_id"] is not None

    # Fetch result
    r_res = client.get(f"/api/results/{zlib_sample['result_id']}")
    assert r_res.status_code == 200
    res_data = r_res.json()
    assert res_data["summary"]["total_functions_a"] > 0
    assert len(res_data["ranked_diffs"]) > 0
    assert len(res_data["callgraph"]["nodes"]) > 0


def test_function_detail_view_and_cfg() -> None:
    """Validate deep-dive function detail endpoint with CFG and diff data."""
    res = client.get("/api/samples")
    result_id = res.json()[0]["result_id"]

    # Fetch detail for Rank #1
    f_res = client.get(f"/api/results/{result_id}/functions/1")
    assert f_res.status_code == 200
    detail = f_res.json()
    assert detail["rank"] == 1
    assert "classification" in detail
    assert "unified_diff" in detail
    assert "fingerprint_breakdown" in detail
    if detail["cfg_b"]:
        assert "blocks" in detail["cfg_b"]
        assert "edges" in detail["cfg_b"]


def test_export_endpoints() -> None:
    """Validate JSON and Markdown export endpoints."""
    res = client.get("/api/samples")
    result_id = res.json()[0]["result_id"]

    # JSON export
    j_res = client.get(f"/api/results/{result_id}/export/json")
    assert j_res.status_code == 200
    assert "application/json" in j_res.headers["content-type"]
    assert "ranked_functions" in j_res.json()

    # Markdown export
    m_res = client.get(f"/api/results/{result_id}/export/markdown")
    assert m_res.status_code == 200
    assert "text/markdown" in m_res.headers["content-type"]
    assert "PatchLens Binary Diff Report" in m_res.text
