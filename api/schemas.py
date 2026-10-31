"""Pydantic schemas and serialization models for PatchLens API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BinaryUploadResponse(BaseModel):
    """Metadata returned after validating and saving an ELF binary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sha256: str
    filename: str
    file_size: int
    arch: str
    is_stripped: bool
    entry_point: int


class StartAnalysisRequest(BaseModel):
    """Payload to start a diffing and security patch analysis job."""

    binary_a_id: int = Field(..., description="ID of baseline/old binary")
    binary_b_id: int = Field(..., description="ID of patched/new binary")


class JobStatusResponse(BaseModel):
    """Status and progress tracking for an asynchronous analysis job."""

    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: str
    progress: int
    current_stage: str
    stage_details: str | None = None
    error_message: str | None = None
    binary_a_id: int
    binary_b_id: int
    result_id: int | None = None
    created_at: str
    completed_at: str | None = None


class SecurityTagSchema(BaseModel):
    """Security pattern tag identified in a function diff."""

    tag_type: str
    description: str
    confidence: float
    block_ids_a: list[int]
    block_ids_b: list[int]
    evidence: str


class BlockDiffSchema(BaseModel):
    """Block-level diff details."""

    block_addr_a: int | None
    block_addr_b: int | None
    change_type: str
    similarity: float
    unified_diff: str


class RankedFunctionDiffSchema(BaseModel):
    """Summary of a matched and ranked function diff."""

    rank: int
    patch_score: float
    classification: str
    addr_a: int | None
    addr_b: int | None
    name_a: str
    name_b: str
    similarity: float
    matched_pass: str
    confidence: float
    security_tags: list[SecurityTagSchema]
    block_diffs_count: int
    snippet_diff: str


class AnalysisSummarySchema(BaseModel):
    """Aggregated metrics across the binary diff."""

    total_functions_a: int
    total_functions_b: int
    matched_count: int
    unmatched_a_count: int
    unmatched_b_count: int
    identical_count: int
    changed_cosmetic_count: int
    changed_semantic_count: int
    top_patch_candidates_count: int


class CFGBlockSchema(BaseModel):
    """Basic block data formatted for CFG graph visualization."""

    addr: int
    end_addr: int
    change_type: str
    instructions: list[str]


class CFGEdgeSchema(BaseModel):
    """Directed edge in the basic block CFG."""

    src: int
    dst: int
    edge_type: str


class CFGGraphSchema(BaseModel):
    """Full CFG representation for a function."""

    blocks: list[CFGBlockSchema]
    edges: list[CFGEdgeSchema]


class FunctionDetailResponse(BaseModel):
    """Deep-dive data for a single function: CFG graphs, unified diff, and match proof."""

    rank: int
    patch_score: float
    classification: str
    addr_a: int | None
    addr_b: int | None
    name_a: str
    name_b: str
    similarity: float
    matched_pass: str
    confidence: float
    security_tags: list[SecurityTagSchema]
    unified_diff: str
    cfg_a: CFGGraphSchema | None = None
    cfg_b: CFGGraphSchema | None = None
    fingerprint_breakdown: dict[str, float] = Field(default_factory=dict)


class CallGraphNode(BaseModel):
    """Call graph node for Match Explorer."""

    id: str
    name: str
    addr: int
    is_changed: bool
    rank: int


class CallGraphEdge(BaseModel):
    """Directed caller -> callee call graph edge."""

    source: str
    target: str


class CallGraphSchema(BaseModel):
    """Overall call graph dataset."""

    nodes: list[CallGraphNode]
    edges: list[CallGraphEdge]


class AnalysisResultResponse(BaseModel):
    """Full analysis result payload."""

    id: int
    job_id: str | None
    pair_hash: str
    summary: AnalysisSummarySchema
    ranked_diffs: list[RankedFunctionDiffSchema]
    callgraph: CallGraphSchema


class SampleCaseSchema(BaseModel):
    """Metadata describing a pre-seeded real-world CVE demo case."""

    id: str
    title: str
    description: str
    cve: str
    binary_a_name: str
    binary_b_name: str
    pair_hash: str
    result_id: int | None = None
