import type { JobStatus } from "./types";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");

if (!BACKEND_URL) {
  // eslint-disable-next-line no-console
  console.warn("VITE_BACKEND_URL is not set. Create a .env file with VITE_BACKEND_URL=...");
}

export interface SubmitResponse {
  job_id: string;
  status: string;
  message: string;
}

export async function submitFactCheck(videoUrl: string): Promise<SubmitResponse> {
  const res = await fetch(`${BACKEND_URL}/api/fact-check/demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl }),
  });

  if (res.status === 429) {
    throw new Error(
      "Demo limit reached (3 per day). Try again tomorrow, or check out the mobile app for unlimited scans.",
    );
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status}). Please try again.`);
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BACKEND_URL}/api/fact-check/demo/${jobId}/status`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Could not fetch status (${res.status}).`);
  }
  return res.json();
}

/**
 * Submit a job and poll until it finishes (or times out).
 * Calls `onProgress` on every tick with the latest status.
 */
export async function runFactCheck(
  videoUrl: string,
  onProgress: (status: JobStatus) => void,
  { timeoutMs = 5 * 60 * 1000, intervalMs = 2000 }: { timeoutMs?: number; intervalMs?: number } = {},
): Promise<JobStatus> {
  const { job_id } = await submitFactCheck(videoUrl);
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    await new Promise((r) => setTimeout(r, intervalMs));
    try {
      const status = await getJobStatus(job_id);
      onProgress(status);
      if (status.status === "completed" || status.status === "failed") {
        return status;
      }
    } catch {
      // transient network hiccup — keep polling
    }
  }
  throw new Error("Analysis timed out after 5 minutes. Please try again.");
}
