export interface BinaryUpload {
  id: number;
  sha256: string;
  filename: string;
  file_size: number;
  arch: string;
  is_stripped: boolean;
  entry_point: number;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_stage: string;
  stage_details?: string;
  error_message?: string;
  binary_a_id: number;
  binary_b_id: number;
  result_id?: number;
  created_at: string;
  completed_at?: string;
}

export interface SecurityTag {
  tag_type: string;
  description: string;
  confidence: number;
  block_ids_a: number[];
  block_ids_b: number[];
  evidence: string;
}

export interface RankedFunctionDiff {
  rank: number;
  patch_score: number;
  classification: "identical" | "changed-cosmetic" | "changed-semantic" | "added" | "removed";
  addr_a: number | null;
  addr_b: number | null;
  name_a: string;
  name_b: string;
  similarity: number;
  matched_pass: string;
  confidence: number;
  security_tags: SecurityTag[];
  block_diffs_count: number;
  snippet_diff: string;
}

export interface AnalysisSummary {
  total_functions_a: number;
  total_functions_b: number;
  matched_count: number;
  unmatched_a_count: number;
  unmatched_b_count: number;
  identical_count: number;
  changed_cosmetic_count: number;
  changed_semantic_count: number;
  top_patch_candidates_count: number;
}

export interface CFGBlock {
  addr: number;
  end_addr: number;
  change_type: "unchanged" | "modified" | "added" | "removed";
  instructions: string[];
}

export interface CFGEdge {
  src: number;
  dst: number;
  edge_type: "fallthrough" | "conditional_true" | "conditional_false" | "jump" | "call";
}

export interface CFGGraph {
  blocks: CFGBlock[];
  edges: CFGEdge[];
}

export interface FunctionDetail {
  rank: number;
  patch_score: number;
  classification: "identical" | "changed-cosmetic" | "changed-semantic" | "added" | "removed";
  addr_a: number | null;
  addr_b: number | null;
  name_a: string;
  name_b: string;
  similarity: number;
  matched_pass: string;
  confidence: number;
  security_tags: SecurityTag[];
  unified_diff: string;
  cfg_a: CFGGraph | null;
  cfg_b: CFGGraph | null;
  fingerprint_breakdown: Record<string, number>;
}

export interface CallGraphNode {
  id: string;
  name: string;
  addr: number;
  is_changed: boolean;
  rank: number;
}

export interface CallGraphEdge {
  source: string;
  target: string;
}

export interface CallGraphData {
  nodes: CallGraphNode[];
  edges: CallGraphEdge[];
}

export interface AnalysisResult {
  id: number;
  job_id: string | null;
  pair_hash: string;
  summary: AnalysisSummary;
  ranked_diffs: RankedFunctionDiff[];
  callgraph: CallGraphData;
}

export interface SampleCase {
  id: string;
  title: string;
  description: string;
  cve: string;
  binary_a_name: string;
  binary_b_name: string;
  pair_hash: string;
  result_id?: number;
}

