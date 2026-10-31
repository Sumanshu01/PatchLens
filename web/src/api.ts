import {
  AnalysisResult,
  BinaryUpload,
  FunctionDetail,
  JobStatus,
  SampleCase,
} from "./types";

const API_BASE = "/api";

export async function uploadBinary(file: File): Promise<BinaryUpload> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/binaries/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function startAnalysis(
  binaryAId: number,
  binaryBId: number
): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/analyses/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ binary_a_id: binaryAId, binary_b_id: binaryBId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed starting analysis" }));
    throw new Error(err.detail || "Failed starting analysis");
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/analyses/${jobId}`);
  if (!res.ok) throw new Error("Failed fetching job status");
  return res.json();
}

export async function getAnalysisResult(resultId: number): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/results/${resultId}`);
  if (!res.ok) throw new Error("Failed fetching analysis results");
  return res.json();
}

export async function getFunctionDetail(
  resultId: number,
  rank: number
): Promise<FunctionDetail> {
  const res = await fetch(`${API_BASE}/results/${resultId}/functions/${rank}`);
  if (!res.ok) throw new Error("Failed fetching function details");
  return res.json();
}

export async function getSampleCases(): Promise<SampleCase[]> {
  const res = await fetch(`${API_BASE}/samples`);
  if (!res.ok) throw new Error("Failed fetching sample cases");
  return res.json();
}

export function subscribeToJobProgress(
  jobId: string,
  onProgress: (event: { stage: string; progress: number; details: string; status: string }) => void,
  onError?: (err: any) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/analyses/${jobId}/stream`);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onProgress(data);
      if (data.status === "completed" || data.status === "failed") {
        eventSource.close();
      }
    } catch {
      // Ignored ping/heartbeat
    }
  };

  eventSource.onerror = (err) => {
    if (onError) onError(err);
    eventSource.close();
  };

  return () => eventSource.close();
}

export function getExportJsonUrl(resultId: number): string {
  return `${API_BASE}/results/${resultId}/export/json`;
}

export function getExportMarkdownUrl(resultId: number): string {
  return `${API_BASE}/results/${resultId}/export/markdown`;
}

