export type Mode = "single_image" | "multi_view";
export type Engine = { id: string; name: string; mode: Mode; upstream: string; license: string; status: "ready" | "not_configured" | "license_review" | "disabled"; reason: string; outputs: string[]; description: string };
export type Artifact = { name: string; format: string; url: string; bytes?: number; sha256?: string };
export type Run = { engine_id: string; engine_name: string; status: string; started_at?: string; finished_at?: string; elapsed_seconds?: number; error?: string; artifacts: Artifact[]; log?: string };
export type Job = { id: string; mode: Mode; status: string; created_at: string; image_count: number; runs: Run[]; error?: string };
const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "http://localhost:8000";
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
  artifactUrl: (url: string) => url.startsWith("http") ? url : base + url
};