import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, CircleHelp, Download, FileImage, Film, LoaderCircle, RefreshCw, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { api, type BlenderEngineStatus, type BlenderJob, type BlenderIteration } from "./api";

const terminal = (status: string) => ["completed", "failed"].includes(status);
const artifactFor = (job: BlenderJob, role: string) => job.outputs.find((item) => item.role === role);
const metricsLabel = (iteration: BlenderIteration) => {
  const metrics = iteration.metrics;
  if (!metrics) return "No reference comparison";
  return metrics.exact_pixel_match
    ? "Exact pixel match"
    : `${metrics.changed_pixel_count.toLocaleString()} pixels differ · MAE ${metrics.mean_absolute_error.toFixed(3)} · RMSE ${metrics.rmse.toFixed(3)}`;
};

export default function BlenderStudio() {
  const [kind, setKind] = useState<"image" | "video">("image");
  const [prompt, setPrompt] = useState("");
  const [reference, setReference] = useState<File | null>(null);
  const [referenceUrl, setReferenceUrl] = useState("");
  const [engine, setEngine] = useState<BlenderEngineStatus | null>(null);
  const [job, setJob] = useState<BlenderJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setEngine(await api.blenderEngine());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not inspect Blender worker.");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!reference) { setReferenceUrl(""); return; }
    const url = URL.createObjectURL(reference);
    setReferenceUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [reference]);
  useEffect(() => {
    if (!job || terminal(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.blenderJob(job.id);
        setJob((current) => current?.id === next.id ? next : current);
        if (next.status === "failed") setError(next.error || "Blender job failed.");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not refresh Blender job status.");
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  const submit = async () => {
    setError("");
    if (!prompt.trim()) { setError("Describe the scene to create."); return; }
    if (reference && reference.size > 20 * 1024 * 1024) { setError("The reference image must be at most 20 MB."); return; }
    setBusy(true);
    try {
      const created = await api.createBlenderJob(kind, prompt, reference ?? undefined);
      setJob(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit the Blender job.");
    } finally { setBusy(false); }
  };

  const finalPreview = useMemo(() => job ? artifactFor(job, "final-preview") : undefined, [job]);
  const finalVideo = useMemo(() => job ? artifactFor(job, "video") : undefined, [job]);
  const exact = job?.exact_pixel_match === true;
  const finalMetrics = job?.iterations[job.iterations.length - 1]?.metrics;

  return <section className="blender-studio">
    <div className="page-heading media-heading">
      <div>
        <div className="eyebrow"><span className="eyebrow-line"/> PYTHON · BLENDER · GEMINI OPCIONAL</div>
        <h1>Create with <span>Blender + Python.</span></h1>
        <p>Generate a real Blender scene, render it, inspect the pixels and iterate against a reference image.</p>
      </div>
      <button className="secondary-button" onClick={() => void refresh()}><RefreshCw size={15}/> Check worker</button>
    </div>

    <div className="blender-runtime-strip">
      <div className={engine?.ready ? "runtime-status ready" : "runtime-status"}>
        <span className="runtime-dot"/>
        <div>
          <strong>{engine?.ready ? "Blender worker ready" : "Blender worker not configured"}</strong>
          <p>{engine?.reason ?? "Checking the remote worker..."}</p>
          {engine?.blender_version && <small>{engine.blender_version}</small>}
        </div>
      </div>
      <div className="blender-capabilities">
        <span><ShieldCheck size={15}/> Remote worker token protected</span>
        <span><Sparkles size={15}/> Gemini {engine?.gemini_configured ? "enabled" : "not configured"}</span>
        <span><RefreshCw size={15}/> Up to {engine?.max_iterations || 0} render passes</span>
      </div>
    </div>

    <div className="media-grid blender-grid">
      <section className="panel media-form">
        <div className="panel-heading"><div><span className="step-index">01</span><h2>Scene instructions</h2></div><span className="subtle-tag"><Sparkles size={14}/> Blender Python</span></div>
        <div className="media-kind-toggle" role="group" aria-label="Output type">
          <button className={kind === "image" ? "media-kind active" : "media-kind"} onClick={() => { setKind("image"); setJob(null); }}><FileImage size={17}/> Image</button>
          <button className={kind === "video" ? "media-kind active" : "media-kind"} onClick={() => { setKind("video"); setJob(null); }}><Film size={17}/> Video</button>
        </div>
        <label className="media-label" htmlFor="blender-prompt">Detailed prompt</label>
        <textarea id="blender-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={8000} rows={8} placeholder="Describe the subject, geometry, composition, camera, materials, lighting, atmosphere and visual style..." />
        <div className="media-prompt-footer"><span>Up to 8,000 characters</span><span>{prompt.length}/8000</span></div>

        <label className="media-label" htmlFor="blender-reference">Reference image (optional)</label>
        <div className="blender-reference">
          <input id="blender-reference" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setReference(event.target.files?.[0] ?? null)} />
          {referenceUrl ? <div className="blender-reference-preview"><img src={referenceUrl} alt="Reference image preview"/><div><strong>{reference?.name}</strong><span>{((reference?.size ?? 0) / 1024 / 1024).toFixed(2)} MB</span><button className="secondary-button" onClick={() => { setReference(null); const input = document.getElementById("blender-reference") as HTMLInputElement | null; if (input) input.value = ""; }}>Remove reference</button></div></div> : <p><Upload size={15}/> Add a PNG, JPEG or WebP image up to 20 MB to enable visual comparison.</p>}
        </div>

        <div className="blender-info"><CircleHelp size={16}/><p><strong>Gemini feedback loop:</strong> when <code>GEMINI_API_KEY</code> is configured on the worker and a reference is attached, Gemini writes/revises a Blender Python script, the worker renders a preview, computes pixel metrics, sends the reference and render back to Gemini, and repeats until exact equality or the configured iteration limit.</p></div>
        {!engine?.gemini_configured && <p className="blender-note">Without Gemini, the worker uses its deterministic procedural primitive generator. It still renders a real Blender scene, but does not perform LLM-based script revision.</p>}
        {error && <div className="media-error" role="alert"><AlertCircle size={16}/><span>{error}</span></div>}
        <button className="primary-button media-submit" disabled={busy || !engine?.ready || !prompt.trim()} onClick={() => void submit()}>
          {busy ? <LoaderCircle className="spin" size={16}/> : <Sparkles size={16}/>} Generate {kind} <span>→</span>
        </button>
        <p className="media-footnote">Blender runs on a separate worker, not inside Vercel Functions. Pixel-exact equality is measured honestly and cannot be guaranteed for arbitrary 3D scenes.</p>
      </section>

      <section className="panel media-output">
        <div className="panel-heading"><div><span className="step-index">02</span><h2>Render review</h2></div>{job && <span className="counter">{job.status} · {job.progress}%</span>}</div>
        {!job && <div className="media-empty"><div className="media-empty-icon"><FileImage size={26}/></div><strong>Your render will appear here</strong><p>The panel displays only files returned by the actual Blender worker.</p></div>}
        {job && <div className="blender-job">
          <div className="generation-status">
            {["queued", "running"].includes(job.status) ? <LoaderCircle className="spin" size={17}/> : job.status === "completed" ? <CheckCircle2 size={17}/> : <AlertCircle size={17}/>}
            <span>{job.status === "queued" ? "Waiting for worker" : job.status === "running" ? `Rendering iteration ${job.current_iteration || 1} of ${job.max_iterations}` : job.status === "completed" ? "Render completed" : "Render failed"}</span>
          </div>
          <div className="blender-progress"><span style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }}/></div>
          {job.error && <div className="media-error" role="alert"><AlertCircle size={16}/><span>{job.error}</span></div>}
          {job.status === "completed" && job.reference_attached && <div className={exact ? "blender-match exact" : "blender-match"}>
            <strong>{exact ? "Pixel-perfect match confirmed" : "Reference comparison finished"}</strong>
            <p>{exact ? "Every compared RGB pixel matches exactly at the reference resolution." : finalMetrics ? `${finalMetrics.changed_pixel_count.toLocaleString()} of ${finalMetrics.pixel_count.toLocaleString()} pixels differ. The worker stopped at its configured iteration limit or after the final available pass.` : "No pixel metrics were returned."}</p>
          </div>}
          {finalVideo && <div className="media-artifact"><video controls preload="metadata" src={api.blenderArtifactUrl(job.id, finalVideo.filename)}/><a href={api.blenderArtifactUrl(job.id, finalVideo.filename)} download={finalVideo.filename}><Download size={14}/> {finalVideo.filename}</a></div>}
          {finalPreview && <div className="media-artifact blender-final-preview"><img loading="lazy" src={api.blenderArtifactUrl(job.id, finalPreview.filename)} alt="Final Blender render"/><a href={api.blenderArtifactUrl(job.id, finalPreview.filename)} download={finalPreview.filename}><Download size={14}/> Final render · {finalPreview.filename}</a></div>}
          {job.iterations.length > 0 && <div className="blender-iterations">
            <div className="blender-section-title"><h3>Iteration history</h3><span>{job.iterations.length} render pass(es)</span></div>
            {job.iterations.map((iteration) => {
              const preview = job.outputs.find((item) => item.filename === iteration.preview);
              const diff = iteration.diff ? job.outputs.find((item) => item.filename === iteration.diff) : undefined;
              const script = job.outputs.find((item) => item.filename === iteration.script);
              return <article className="blender-iteration" key={iteration.iteration}>
                <div className="blender-iteration-heading"><strong>Pass {iteration.iteration}</strong><span>{iteration.metrics?.exact_pixel_match ? "Exact match" : iteration.metrics ? `MAE ${iteration.metrics.mean_absolute_error.toFixed(3)}` : "Rendered"}</span></div>
                <p>{iteration.review}</p>
                <p className="blender-metrics">{metricsLabel(iteration)}</p>
                <div className="blender-iteration-assets">
                  {preview && <a href={api.blenderArtifactUrl(job.id, preview.filename)} target="_blank" rel="noreferrer"><img src={api.blenderArtifactUrl(job.id, preview.filename)} alt={`Render pass ${iteration.iteration}`}/><span>Render</span></a>}
                  {diff && <a href={api.blenderArtifactUrl(job.id, diff.filename)} target="_blank" rel="noreferrer"><img src={api.blenderArtifactUrl(job.id, diff.filename)} alt={`Pixel difference pass ${iteration.iteration}`}/><span>Pixel difference</span></a>}
                  {script && <a className="blender-script-link" href={api.blenderArtifactUrl(job.id, script.filename)} download={script.filename}><Download size={14}/><span>Python script</span></a>}
                </div>
              </article>;
            })}
          </div>}
          {job.status === "completed" && <div className="blender-downloads">
            {job.outputs.filter((item) => ["editable-blend", "python-script", "video"].includes(item.role)).map((item) => <a key={item.filename} href={api.blenderArtifactUrl(job.id, item.filename)} download={item.filename}><Download size={14}/>{item.role === "editable-blend" ? "Editable .blend" : item.role === "python-script" ? "Final Python script" : "MP4 video"}</a>)}
          </div>}
        </div>}
      </section>
    </div>
  </section>;
}
