export type Mode = "single_image" | "multi_view";
export type Engine = { id: string; name: string; mode: Mode; upstream: string; license: string; status: "ready" | "not_configured" | "validation_required" | "disabled"; reason: string; outputs: string[]; description: string };
export type Artifact = { name: string; format: string; url: string; bytes?: number; sha256?: string };
export type Run = { engine_id: string; engine_name: string; status: string; started_at?: string; finished_at?: string; elapsed_seconds?: number; error?: string; artifacts: Artifact[]; log?: string };
export type Job = { id: string; mode: Mode; status: string; created_at: string; image_count: number; runs: Run[]; error?: string };

// In production the browser and API share the Vercel deployment origin.
// Keep VITE_API_BASE_URL as an explicit override for local/dev deployments only.
const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
export const api = {
  engines: () => request<{ engines: Engine[] }>("/api/engines"),
  jobs: () => request<{ jobs: Job[] }>("/api/jobs"),
  job: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  createJob: (mode: Mode, files: File[], engines: string[]) => {
    const data = new FormData();
    data.append("mode", mode);
    engines.forEach((engine) => data.append("engines", engine));
    files.forEach((file) => data.append("images", file, file.name));
    return request<Job>("/api/jobs", { method: "POST", body: data });
  },
  mediaEngines: () => request<MediaEngineStatus>("/api/media/engines"),
  generateMedia: (kind: "image" | "video", prompt: string, provider = "comfyui-local") => request<MediaGeneration>("/api/media/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, prompt, provider }) }),
  mediaJob: (id: string) => request<MediaGeneration>(`/api/media/jobs/${encodeURIComponent(id)}`),
  mediaArtifactUrl: (output: MediaOutput, generationId: string) => {
    const query = new URLSearchParams({ generation_id: generationId, filename: output.filename, subfolder: output.subfolder, artifact_type: output.type });
    return base + "/api/media/artifact?" + query.toString();
  },
  artifactUrl: (url: string) => url.startsWith("http") ? url : base + url
};

export type MediaWorkflowStatus = { ready: boolean; workflow_configured: boolean; workflow_exists: boolean; prompt_node_configured: boolean; reason: string };
export type MediaProviderStatus = { id: string; name: string; supports: Array<"image" | "video">; configured: boolean; ready: boolean; ready_for: Array<"image" | "video">; free_tier: string; reason: string };
export type MediaEngineStatus = { engine: string; configured: boolean; reachable: boolean; enabled: boolean; image: MediaWorkflowStatus; video: MediaWorkflowStatus; providers?: MediaProviderStatus[] };
export type MediaOutput = { filename: string; subfolder: string; type: string };
export type MediaGeneration = { id: string; kind?: "image" | "video"; status: string; engine?: string; outputs?: MediaOutput[] };
