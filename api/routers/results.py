"""Endpoints for retrieving diff results, function detail views, and report exports."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import AnalysisResultRecord
from api.schemas import (
    AnalysisResultResponse,
    AnalysisSummarySchema,
    CallGraphSchema,
    FunctionDetailResponse,
    RankedFunctionDiffSchema,
)

router = APIRouter(tags=["Results"])


@router.get("/results/{result_id}", response_model=AnalysisResultResponse)
def get_analysis_results(result_id: int, db: Session = Depends(get_db)) -> AnalysisResultResponse:
    """Retrieve top-level binary diff summary, ranked functions list, and call graph."""
    rec = db.query(AnalysisResultRecord).filter(AnalysisResultRecord.id == result_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis result {result_id} not found",
        )

    summary_raw = json.loads(rec.summary_json)
    ranked_raw = json.loads(rec.ranked_diffs_json)
    callgraph_raw = (
        json.loads(rec.callgraph_json) if rec.callgraph_json else {"nodes": [], "edges": []}
    )

    return AnalysisResultResponse(
        id=rec.id,
        job_id=rec.job_id,
        pair_hash=rec.pair_hash,
        summary=AnalysisSummarySchema(**summary_raw),
        ranked_diffs=[RankedFunctionDiffSchema(**item) for item in ranked_raw],
        callgraph=CallGraphSchema(**callgraph_raw),
    )


@router.get("/results/{result_id}/functions/{rank}", response_model=FunctionDetailResponse)
def get_function_detail(
    result_id: int,
    rank: int,
    db: Session = Depends(get_db),
) -> FunctionDetailResponse:
    """Fetch deep-dive CFG graphs, unified diffs, and fingerprint match breakdown for a function."""
    rec = db.query(AnalysisResultRecord).filter(AnalysisResultRecord.id == result_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Result not found")

    details_map = json.loads(rec.details_json) if rec.details_json else {}

    # Look for matching rank in details map
    target_detail = None
    for detail_item in details_map.values():
        if detail_item.get("rank") == rank:
            target_detail = detail_item
            break

    # If rank == 0 (unranked/unchanged function), try finding by address or first item
    if not target_detail and rank == 0 and details_map:
        target_detail = next(iter(details_map.values()))

    if not target_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function details for rank #{rank} not found",
        )

    return FunctionDetailResponse(**target_detail)


@router.get("/results/{result_id}/export/json")
def export_results_json(result_id: int, db: Session = Depends(get_db)) -> Response:
    """Download full diff and security analysis result as a structured JSON file."""
    rec = db.query(AnalysisResultRecord).filter(AnalysisResultRecord.id == result_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Result not found")

    payload = {
        "result_id": rec.id,
        "job_id": rec.job_id,
        "pair_hash": rec.pair_hash,
        "created_at": rec.created_at.isoformat(),
        "summary": json.loads(rec.summary_json),
        "ranked_functions": json.loads(rec.ranked_diffs_json),
        "callgraph": json.loads(rec.callgraph_json),
    }

    content = json.dumps(payload, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=patchlens_diff_{result_id}.json"},
    )


@router.get("/results/{result_id}/export/markdown")
def export_results_markdown(result_id: int, db: Session = Depends(get_db)) -> Response:
    """Download audit report in Markdown format."""
    rec = db.query(AnalysisResultRecord).filter(AnalysisResultRecord.id == result_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Result not found")

    summary = json.loads(rec.summary_json)
    ranked = json.loads(rec.ranked_diffs_json)

    lines = [
        f"# PatchLens Binary Diff Report — Analysis #{result_id}",
        "",
        f"- **Pair Hash**: `{rec.pair_hash}`",
        f"- **Generated At**: {rec.created_at.isoformat()}",
        "",
        "## Summary Metrics",
        "",
        f"- Total Functions Baseline: {summary.get('total_functions_a')}",
        f"- Total Functions Patched: {summary.get('total_functions_b')}",
        f"- Matched Functions: {summary.get('matched_count')}",
        f"- Semantic Changes: {summary.get('changed_semantic_count')}",
        f"- Cosmetic Changes: {summary.get('changed_cosmetic_count')}",
        f"- Added Functions: {summary.get('unmatched_b_count')}",
        f"- Removed Functions: {summary.get('unmatched_a_count')}",
        "",
        "## Top Security Patch Candidates",
        "",
        "| Rank | Function A | Function B | Classification | Sim | Patch Score | Security Tags |",
        "|---:|---|---|---|---:|---:|---|",
    ]

    for item in ranked[:15]:
        tags_str = ", ".join(t["tag_type"] for t in item.get("security_tags", [])) or "none"
        lines.append(
            f"| **#{item['rank']}** | `{item['name_a']}` | `{item['name_b']}` | "
            f"`{item['classification']}` | {item['similarity']:.4f} | "
            f"**{item['patch_score']:.4f}** | `{tags_str}` |"
        )

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=patchlens_report_{result_id}.md"},
    )
