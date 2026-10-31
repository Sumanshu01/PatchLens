"""Background worker task executing PatchLens analysis pipeline with progress tracking."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.cfg import recover_all_functions
from core.diff import ChangeClassification, diff_matched_functions
from core.disasm import disassemble_text
from core.fingerprint import (
    extract_fingerprints,
    md_index_similarity,
    mnemonic_cosine_similarity,
    wl_subtree_kernel_similarity,
)
from core.loader import load_elf
from core.match import FunctionMatcher
from core.models import Binary
from core.normalize import InstructionNormalizer
from core.rank import score_and_rank_diffs

from api.database import SessionLocal
from api.models import AnalysisJob, AnalysisResultRecord, BinaryRecord

logger = logging.getLogger("patchlens.worker")


def execute_analysis_job(
    job_id: str,
    progress_callback: Callable[[str, int, str], None] | None = None,
) -> None:
    """Execute complete analysis pipeline for an AnalysisJob under isolation."""
    db = SessionLocal()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        db.close()
        logger.error("Job %s not found in database", job_id)
        return

    def update_progress(stage: str, progress: int, details: str = "") -> None:
        try:
            job.status = "running"
            job.current_stage = stage
            job.progress = progress
            job.stage_details = details
            db.commit()
            if progress_callback:
                progress_callback(stage, progress, details)
        except Exception as exc:
            logger.warning("Failed to commit progress update: %s", exc)

    try:
        bin_a_rec = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_a_id).first()
        bin_b_rec = db.query(BinaryRecord).filter(BinaryRecord.id == job.binary_b_id).first()
        if not bin_a_rec or not bin_b_rec:
            raise ValueError("Binary records not found")

        path_a = Path(bin_a_rec.file_path)
        path_b = Path(bin_b_rec.file_path)
        if not path_a.is_file() or not path_b.is_file():
            raise FileNotFoundError(f"Binary files missing on disk: {path_a} or {path_b}")

        pair_hash = f"{bin_a_rec.sha256}_{bin_b_rec.sha256}"

        # Check existing result cache in DB
        existing_result = (
            db.query(AnalysisResultRecord)
            .filter(AnalysisResultRecord.pair_hash == pair_hash)
            .first()
        )
        if existing_result:
            update_progress("completed", 100, "Loaded from result cache")
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            existing_result.job_id = job.id
            db.commit()
            return

        # Stage 1: Load ELF Headers & Sections (10%)
        update_progress("loading_elf", 10, "Parsing ELF structures and symbol tables")
        loaded_a = load_elf(path_a)
        loaded_b = load_elf(path_b)

        # Update records if missing info
        if bin_a_rec.arch == "unknown":
            bin_a_rec.arch = loaded_a.binary.arch.value
            bin_a_rec.is_stripped = loaded_a.binary.is_stripped
            bin_a_rec.entry_point = loaded_a.binary.entry_point
        if bin_b_rec.arch == "unknown":
            bin_b_rec.arch = loaded_b.binary.arch.value
            bin_b_rec.is_stripped = loaded_b.binary.is_stripped
            bin_b_rec.entry_point = loaded_b.binary.entry_point
        db.commit()

        # Stage 2: Disassembly (30%)
        update_progress("disassembling", 30, "Recursive-descent disassembly with Capstone")
        disasm_a = disassemble_text(loaded_a)
        disasm_b = disassemble_text(loaded_b)

        # Stage 3: CFG Recovery (50%)
        update_progress("cfg_recovery", 50, "Basic-block splitting and CFG reconstruction")
        funcs_a = recover_all_functions(loaded_a, disasm_a)
        funcs_b = recover_all_functions(loaded_b, disasm_b)

        b_a = loaded_a.binary
        b_b = loaded_b.binary
        bin_obj_a = Binary(
            path=b_a.path,
            sha256=b_a.sha256,
            arch=b_a.arch,
            bits=b_a.bits,
            endian=b_a.endian,
            is_pie=b_a.is_pie,
            is_stripped=b_a.is_stripped,
            entry_point=b_a.entry_point,
            sections=b_a.sections,
            symbols=b_a.symbols,
            imports=b_a.imports,
            functions=funcs_a,
        )
        bin_obj_b = Binary(
            path=b_b.path,
            sha256=b_b.sha256,
            arch=b_b.arch,
            bits=b_b.bits,
            endian=b_b.endian,
            is_pie=b_b.is_pie,
            is_stripped=b_b.is_stripped,
            entry_point=b_b.entry_point,
            sections=b_b.sections,
            symbols=b_b.symbols,
            imports=b_b.imports,
            functions=funcs_b,
        )

        # Stage 4: Fingerprinting (65%)
        update_progress("fingerprinting", 65, "Computing WL subtree hashes, MD-index, and n-grams")
        normalizer = InstructionNormalizer()
        fps_a = {}
        fps_b = {}
        for f in funcs_a:
            nf = normalizer.normalize_function(f)
            fps_a[f.addr] = (extract_fingerprints(f, nf, loaded=loaded_a), nf)
        for f in funcs_b:
            nf = normalizer.normalize_function(f)
            fps_b[f.addr] = (extract_fingerprints(f, nf, loaded=loaded_b), nf)

        # Stage 5: Multi-Pass Function Matching (80%)
        update_progress(
            "function_matching", 80, "Executing 6-pass confidence ladder and Hungarian matching"
        )
        matcher = FunctionMatcher()
        match_result = matcher.match(
            bin_obj_a,
            bin_obj_b,
            loaded_a=loaded_a,
            loaded_b=loaded_b,
            use_symbols=not bin_a_rec.is_stripped and not bin_b_rec.is_stripped,
        )

        # Stage 6: Diffing & Security Detectors (95%)
        update_progress(
            "diffing_and_detecting",
            95,
            "Computing block diffs and detecting security check additions",
        )
        func_diffs = diff_matched_functions(
            match_result,
            bin_obj_a,
            bin_obj_b,
            loaded_a=loaded_a,
            loaded_b=loaded_b,
        )
        ranked_diffs = score_and_rank_diffs(func_diffs, bin_obj_b)

        # Serialize results
        summary_data = {
            "total_functions_a": len(funcs_a),
            "total_functions_b": len(funcs_b),
            "matched_count": len(match_result.matches),
            "unmatched_a_count": len(match_result.unmatched_a),
            "unmatched_b_count": len(match_result.unmatched_b),
            "identical_count": sum(
                1 for d in ranked_diffs if d.classification == ChangeClassification.IDENTICAL
            ),
            "changed_cosmetic_count": sum(
                1 for d in ranked_diffs if d.classification == ChangeClassification.CHANGED_COSMETIC
            ),
            "changed_semantic_count": sum(
                1 for d in ranked_diffs if d.classification == ChangeClassification.CHANGED_SEMANTIC
            ),
            "top_patch_candidates_count": sum(1 for d in ranked_diffs if d.rank > 0),
        }

        # Build map for fast function lookup
        func_a_map = {f.addr: f for f in funcs_a}
        func_b_map = {f.addr: f for f in funcs_b}

        ranked_list_json: list[dict[str, Any]] = []
        details_map: dict[str, Any] = {}

        for d in ranked_diffs:
            # Match info
            m_pass = "unmatched"
            m_conf = 0.0

            # Find matching pass and conf if available
            for m in match_result.matches:
                if m.addr_b == d.addr_b:
                    m_pass = m.pass_name
                    m_conf = m.confidence
                    break

            tags_data = [
                {
                    "tag_type": t.tag_type,
                    "description": t.description,
                    "confidence": t.confidence,
                    "block_ids_a": list(t.block_ids_a),
                    "block_ids_b": list(t.block_ids_b),
                    "evidence": t.evidence,
                }
                for t in d.security_tags
            ]

            # Snippet diff
            snippet = ""
            for bd in d.block_diffs:
                if bd.unified_diff:
                    snippet = "\n".join(bd.unified_diff)
                    break

            item_dict = {
                "rank": d.rank,
                "patch_score": round(d.patch_score, 4),
                "classification": d.classification.value,
                "addr_a": d.addr_a,
                "addr_b": d.addr_b,
                "name_a": d.name_a,
                "name_b": d.name_b,
                "similarity": round(d.similarity, 4),
                "matched_pass": m_pass,
                "confidence": round(m_conf, 4),
                "security_tags": tags_data,
                "block_diffs_count": len(d.block_diffs),
                "snippet_diff": snippet,
            }
            ranked_list_json.append(item_dict)

            # Build CFG graphs for detail view
            fa = func_a_map.get(d.addr_a) if d.addr_a else None
            fb = func_b_map.get(d.addr_b) if d.addr_b else None

            # Change types per block
            block_change_a: dict[int, str] = {}
            block_change_b: dict[int, str] = {}
            for bd in d.block_diffs:
                if bd.block_a:
                    block_change_a[bd.block_a.start_addr] = bd.change_type.value
                if bd.block_b:
                    block_change_b[bd.block_b.start_addr] = bd.change_type.value

            cfg_a_data = None
            if fa:
                cfg_a_data = {
                    "blocks": [
                        {
                            "addr": bb.start_addr,
                            "end_addr": bb.end_addr,
                            "change_type": block_change_a.get(bb.start_addr, "unchanged"),
                            "instructions": [
                                f"{insn.mnemonic} {insn.op_str}".strip() for insn in bb.instructions
                            ],
                        }
                        for bb in fa.blocks
                    ],
                    "edges": [
                        {"src": e.src, "dst": e.dst, "edge_type": e.edge_type.value}
                        for e in fa.edges
                    ],
                }

            cfg_b_data = None
            if fb:
                cfg_b_data = {
                    "blocks": [
                        {
                            "addr": bb.start_addr,
                            "end_addr": bb.end_addr,
                            "change_type": block_change_b.get(bb.start_addr, "unchanged"),
                            "instructions": [
                                f"{insn.mnemonic} {insn.op_str}".strip() for insn in bb.instructions
                            ],
                        }
                        for bb in fb.blocks
                    ],
                    "edges": [
                        {"src": e.src, "dst": e.dst, "edge_type": e.edge_type.value}
                        for e in fb.edges
                    ],
                }

            # Combined unified diff
            all_diffs = []
            for bd in d.block_diffs:
                if bd.unified_diff:
                    all_diffs.append("\n".join(bd.unified_diff))
            combined_unified_diff = "\n\n".join(all_diffs)

            # Fingerprint breakdown
            fp_breakdown: dict[str, float] = {}
            if d.addr_a and d.addr_b and d.addr_a in fps_a and d.addr_b in fps_b:
                fpa, _ = fps_a[d.addr_a]
                fpb, _ = fps_b[d.addr_b]
                fp_breakdown["mnemonic_similarity"] = round(
                    mnemonic_cosine_similarity(fpa.mnemonic_hist, fpb.mnemonic_hist), 4
                )
                fp_breakdown["wl_graph_similarity"] = round(
                    wl_subtree_kernel_similarity(fpa.wl_subtrees, fpb.wl_subtrees), 4
                )
                fp_breakdown["md_index_similarity"] = round(
                    md_index_similarity(fpa.md_index, fpb.md_index), 4
                )

            detail_key = f"{d.addr_a}_{d.addr_b}"
            details_map[detail_key] = {
                "rank": d.rank,
                "patch_score": round(d.patch_score, 4),
                "classification": d.classification.value,
                "addr_a": d.addr_a,
                "addr_b": d.addr_b,
                "name_a": d.name_a,
                "name_b": d.name_b,
                "similarity": round(d.similarity, 4),
                "matched_pass": m_pass,
                "confidence": round(m_conf, 4),
                "security_tags": tags_data,
                "unified_diff": combined_unified_diff,
                "cfg_a": cfg_a_data,
                "cfg_b": cfg_b_data,
                "fingerprint_breakdown": fp_breakdown,
            }

        # Build Call Graph for Match Explorer
        cg_nodes: list[dict[str, Any]] = []
        cg_edges: list[dict[str, Any]] = []
        changed_ranks = {d.addr_b: d.rank for d in ranked_diffs if d.rank > 0}

        for fb in funcs_b:
            node_id = f"func_{hex(fb.addr)}"
            is_ch = fb.addr in changed_ranks
            cg_nodes.append(
                {
                    "id": node_id,
                    "name": fb.name,
                    "addr": fb.addr,
                    "is_changed": is_ch,
                    "rank": changed_ranks.get(fb.addr, 0),
                }
            )
            for callee_addr in fb.call_targets:
                if callee_addr in func_b_map:
                    cg_edges.append(
                        {
                            "source": node_id,
                            "target": f"func_{hex(callee_addr)}",
                        }
                    )

        callgraph_data = {"nodes": cg_nodes, "edges": cg_edges}

        # Save to database
        result_record = AnalysisResultRecord(
            job_id=job.id,
            pair_hash=pair_hash,
            summary_json=json.dumps(summary_data),
            ranked_diffs_json=json.dumps(ranked_list_json),
            callgraph_json=json.dumps(callgraph_data),
            details_json=json.dumps(details_map),
        )
        db.add(result_record)

        update_progress("completed", 100, "Analysis complete")
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        db.commit()

    except Exception as exc:
        logger.exception("Error executing analysis job %s: %s", job_id, exc)
        try:
            job.status = "failed"
            job.current_stage = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            db.commit()
            if progress_callback:
                progress_callback("failed", job.progress, str(exc))
        except Exception:
            pass
    finally:
        db.close()
