import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertCircle, ArrowDownToLine, Box, Check, ChevronDown, CircleHelp, Clock3, Cuboid, FileImage, Files, FolderOpen, Gauge, Grid2X2, Layers3, LoaderCircle, Menu, Play, Plus, RefreshCw, ShieldCheck, Sparkles, Upload, X } from "lucide-react";
import { api, type Engine, type Job, type Mode } from "./api";
import ModelViewer from "./viewer/ModelViewer";
import MediaStudio from "./MediaStudio";
import BlenderStudio from "./BlenderStudio";

type UploadItem = { id: string; file: File; preview: string };
const prettyBytes = (bytes: number) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const statusLabel: Record<string, string> = { ready: "Ready", not_configured: "Not configured", validation_required: "Validation required", disabled: "Disabled", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", cancelled: "Cancelled" };
const initialEngineInfo: Record<string, { mode: Mode; license: string; description: string }> = {
  triposr: { mode: "single_image", license: "Verify source + checkpoint", description: "Fast single-view generative reconstruction." },
  meshroom: { mode: "multi_view", license: "Dependency audit", description: "Photogrammetry pipeline for overlapping photographs." },
  colmap_openmvs: { mode: "multi_view", license: "AGPL review required", description: "Camera registration and dense reconstruction pipeline." }
};
export default function App() {
  const [mode, setMode] = useState<Mode>("single_image");
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [tab, setTab] = useState<"studio" | "jobs" | "compare" | "media" | "blender">("studio");
  const [apiError, setApiError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadsRef = useRef<UploadItem[]>([]);
  const refresh = useCallback(async () => {
    try {
      const [engineData, jobData] = await Promise.all([api.engines(), api.jobs()]);
      setEngines(engineData.engines); setJobs(jobData.jobs); setApiError("");
    } catch (error) { setApiError(error instanceof Error ? error.message : "API unavailable"); }
  }, []);
  useEffect(() => { void refresh(); const timer = window.setInterval(() => { void refresh(); }, 5000); return () => window.clearInterval(timer); }, [refresh]);
  useEffect(() => { uploadsRef.current = uploads; }, [uploads]);
  useEffect(() => () => uploadsRef.current.forEach((item) => URL.revokeObjectURL(item.preview)), []);
  const compatibleEngines = useMemo(() => engines.filter((engine) => engine.mode === mode), [engines, mode]);
  const readyCount = compatibleEngines.filter((engine) => engine.status === "ready").length;
  const completedRuns = jobs.flatMap((job) => job.runs.map((run) => ({ ...run, jobId: job.id, mode: job.mode }))).filter((run) => run.status === "completed" && run.artifacts.some((artifact) => artifact.format.toLowerCase() === "glb" || artifact.format.toLowerCase() === "gltf"));
  const addFiles = (files: FileList | File[]) => {
    const incoming = Array.from(files);
    const valid = incoming.filter((file) => file.type.startsWith("image/") && file.size > 0 && file.size <= 25 * 1024 * 1024);
    if (valid.length !== incoming.length) setNotice("Only non-empty image files up to 25 MB each are accepted. The API performs its own validation.");
    const next = valid.map((file) => ({ id: crypto.randomUUID(), file, preview: URL.createObjectURL(file) }));
    setUploads((previous) => [...previous, ...next].slice(0, mode === "single_image" ? 1 : 80));
  };
  const removeUpload = (id: string) => setUploads((previous) => { const removed = previous.find((item) => item.id === id); if (removed) URL.revokeObjectURL(removed.preview); return previous.filter((item) => item.id !== id); });
  const changeMode = (next: Mode) => {
    setMode(next); setSelected([]); setUploads((previous) => next === "single_image" ? previous.slice(0, 1) : previous);
  };
  const toggleEngine = (id: string) => setSelected((previous) => previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id]);
  const run = async () => {
    if (!uploads.length) { setNotice("Add at least one image before starting."); return; }
    if (!selected.length) { setNotice("Select at least one available engine."); return; }
    setBusy(true); setNotice("");
    try {
      const job = await api.createJob(mode, uploads.map((item) => item.file), selected);
      setJobs((previous) => [job, ...previous.filter((entry) => entry.id !== job.id)]); setTab("jobs");
      setNotice("Job submitted. Status and artifacts will update from the API.");
      await refresh();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not submit job."); }
    finally { setBusy(false); }
  };
  const nav = <><button className={tab === "studio" ? "nav-item active" : "nav-item"} onClick={() => { setTab("studio"); setMobileNav(false); }}><Cuboid size={17}/> Studio</button><button className={tab === "jobs" ? "nav-item active" : "nav-item"} onClick={() => { setTab("jobs"); setMobileNav(false); }}><Activity size={17}/> Jobs <span className="nav-count">{jobs.filter((job) => ["queued", "running"].includes(job.status)).length}</span></button><button className={tab === "compare" ? "nav-item active" : "nav-item"} onClick={() => { setTab("compare"); setMobileNav(false); }}><Grid2X2 size={17}/> Compare</button><button className={tab === "media" ? "nav-item active" : "nav-item"} onClick={() => { setTab("media"); setMobileNav(false); }}><Sparkles size={17}/> Create media</button><button className={tab === "blender" ? "nav-item active" : "nav-item"} onClick={() => { setTab("blender"); setMobileNav(false); }}><Box size={17}/> Blender + Python</button></>;
  return <div className="app-shell">
    <header className="topbar"><div className="brand"><div className="brand-mark"><Cuboid size={20}/></div><span>mesh<span className="brand-accent">3d</span></span><span className="brand-version">STUDIO</span></div><button className="mobile-menu icon-button" aria-label="Toggle navigation" onClick={() => setMobileNav((value) => !value)}><Menu size={19}/></button><nav className={mobileNav ? "main-nav nav-open" : "main-nav"}>{nav}</nav><div className="topbar-right"><span className={apiError ? "connection connection-off" : "connection"}><span className="connection-dot"/> {apiError ? "API offline" : "API connected"}</span><button className="icon-button" aria-label="Refresh data" onClick={() => void refresh()}><RefreshCw size={16}/></button><div className="avatar">M</div></div></header>
    <main className="main-content">
      {apiError && <div className="alert alert-error"><AlertCircle size={17}/><div><strong>Backend connection unavailable</strong><p>{apiError}. Start the FastAPI service to load engine status, submit jobs, and retrieve actual outputs. The UI will not invent engine results.</p></div></div>}
      {notice && <div className="toast" role="status">{notice}<button className="icon-button" aria-label="Dismiss" onClick={() => setNotice("")}><X size={15}/></button></div>}
      {tab === "media" && <MediaStudio />}
      {tab === "blender" && <BlenderStudio />}
      {tab === "studio" && <>
        <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> RECONSTRUCTION WORKSPACE</div><h1>Turn images into <span>3D assets.</span></h1><p>Run real reconstruction engines. Inspect outputs side by side. Keep every result reproducible.</p></div><button className="secondary-button" onClick={() => setTab("jobs")}><Clock3 size={16}/> Job history <ChevronDown size={14}/></button></section>
        <div className="workflow"><div className="workflow-step active"><span>01</span><div><b>Input images</b><small>Upload your capture</small></div></div><div className="workflow-connector"/><div className={selected.length ? "workflow-step active" : "workflow-step"}><span>02</span><div><b>Choose engines</b><small>Compare candidates</small></div></div><div className="workflow-connector"/><div className={uploads.length && selected.length ? "workflow-step active" : "workflow-step"}><span>03</span><div><b>Run & inspect</b><small>Review real outputs</small></div></div></div>
        <section className="mode-section"><div className="section-title"><div><h2>Reconstruction mode</h2><p>Choose based on the images you have.</p></div><span className="subtle-tag"><ShieldCheck size={14}/> Separate task classes</span></div><div className="mode-grid">
          <button className={mode === "single_image" ? "mode-card selected" : "mode-card"} onClick={() => changeMode("single_image")}><div className="mode-icon"><FileImage size={20}/></div><div className="mode-copy"><strong>Single image</strong><p>One photo. AI estimates unseen geometry for a fast visual asset.</p><span className="mode-note">Generative · hidden surfaces inferred</span></div><span className="radio-dot"/></button>
          <button className={mode === "multi_view" ? "mode-card selected" : "mode-card"} onClick={() => changeMode("multi_view")}><div className="mode-icon violet"><Files size={20}/></div><div className="mode-copy"><strong>Multiple images</strong><p>Overlapping photos. Recover observed geometry through camera registration.</p><span className="mode-note">Photogrammetry · overlap matters</span></div><span className="radio-dot"/></button>
        </div></section>
        <div className="studio-grid"><section className="panel input-panel"><div className="panel-heading"><div><span className="step-index">01</span><h2>{mode === "single_image" ? "Source image" : "Image set"}</h2></div><span className="counter">{uploads.length} / {mode === "single_image" ? "1" : "80"}</span></div>
          <div className={dragging ? "dropzone dragover" : "dropzone"} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }}><div className="upload-icon"><Upload size={22}/></div><strong>Drop {mode === "single_image" ? "an image" : "your images"} here</strong><span>or browse files from your device</span><button className="secondary-button browse-button" onClick={() => inputRef.current?.click()}><Plus size={15}/> Browse images</button><small>PNG, JPG, WEBP · up to 25 MB per image</small><input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" multiple={mode === "multi_view"} hidden onChange={(event) => { if (event.target.files) addFiles(event.target.files); event.target.value = ""; }}/></div>
          {uploads.length > 0 ? <div className="upload-list">{uploads.map((item, index) => <div className="upload-item" key={item.id}><img src={item.preview} alt={item.file.name}/><div className="upload-meta"><strong title={item.file.name}>{mode === "multi_view" ? `${String(index + 1).padStart(2, "0")} · ` : ""}{item.file.name}</strong><span>{prettyBytes(item.file.size)} · Browser preview</span></div><button className="icon-button remove-button" aria-label={`Remove ${item.file.name}`} onClick={() => removeUpload(item.id)}><X size={15}/></button></div>)}</div> : <div className="empty-upload"><FolderOpen size={17}/><span>No images added yet</span></div>}
          {mode === "multi_view" && <div className="capture-guide"><div className="guide-heading"><CircleHelp size={15}/><strong>Capture checklist</strong></div><div className="guide-items"><span><Check size={13}/> 60–80% overlap</span><span><Check size={13}/> Walk around the object</span><span><Check size={13}/> Consistent lighting</span><span><Check size={13}/> Sharp, focused photos</span></div><p>Client checks are preliminary. The selected engine must report actual camera-registration results.</p></div>}
        </section>
        <section className="panel engines-panel"><div className="panel-heading"><div><span className="step-index">02</span><h2>Engine selection</h2></div><span className="counter">{selected.length} selected</span></div><div className="engine-summary"><span><span className="status-pip"/> {readyCount} ready for this mode</span><span>{compatibleEngines.length} candidates</span></div>
          <div className="engine-list">{compatibleEngines.map((engine) => { const checked = selected.includes(engine.id); const info = initialEngineInfo[engine.id] ?? { mode, license: engine.license, description: engine.reason }; const enabled = engine.status === "ready"; return <div className={checked ? "engine-card engine-selected" : "engine-card"} key={engine.id}><button className="engine-select" aria-label={`Select ${engine.name}`} disabled={!enabled} onClick={() => toggleEngine(engine.id)}><span className={checked ? "check-box checked" : "check-box"}>{checked && <Check size={13}/>}</span></button><div className="engine-emblem">{engine.id.includes("meshroom") || engine.id.includes("colmap") ? <Layers3 size={19}/> : <Sparkles size={19}/>}</div><div className="engine-details"><div className="engine-title"><strong>{engine.name}</strong><span className={`engine-status ${engine.status}`}>{statusLabel[engine.status] ?? engine.status}</span></div><p>{engine.description || info.description}</p><div className="engine-foot"><span><ShieldCheck size={12}/>{engine.license || info.license}</span><a href={engine.upstream} target="_blank" rel="noreferrer">Source ↗</a></div>{!enabled && <div className="engine-reason"><AlertCircle size={13}/>{engine.reason || "The adapter is not configured on this server."}</div>}</div></div>; })}{!compatibleEngines.length && !apiError && <div className="empty-state"><AlertCircle size={20}/><strong>No engine registry returned</strong><p>Check the API engine registry.</p></div>}</div>
          <div className="engine-disclaimer"><ShieldCheck size={15}/><p>Only engines with a configured adapter and cleared license can run. No rankings or quality scores appear until real benchmarks exist.</p></div>
        </section></div>
        <section className="run-bar"><div className="run-summary"><div className="run-icon"><Gauge size={18}/></div><div><strong>Ready to submit</strong><span>{uploads.length} image{uploads.length === 1 ? "" : "s"} · {selected.length} engine{selected.length === 1 ? "" : "s"} selected</span></div></div><div className="run-actions"><span className="no-estimate"><Clock3 size={14}/> Runtime not estimated</span><button className="primary-button" disabled={busy || !uploads.length || !selected.length || !!apiError} onClick={() => void run()}>{busy ? <LoaderCircle className="spin" size={16}/> : <Play size={16} fill="currentColor"/>} Run reconstruction <span>→</span></button></div></section>
      </>}
      {tab === "jobs" && <section className="content-view"><div className="page-heading compact"><div><div className="eyebrow"><span className="eyebrow-line"/> EXECUTION LOG</div><h1>Job <span>history.</span></h1><p>Real API job states, engine logs, failures, and verified artifacts.</p></div><button className="secondary-button" onClick={() => void refresh()}><RefreshCw size={15}/> Refresh</button></div>{jobs.length ? <div className="jobs-table"><div className="jobs-header"><span>Job / input mode</span><span>Images</span><span>Runs</span><span>Status</span><span>Created</span></div>{jobs.map((job) => <article className="job-row" key={job.id}><div><strong>{job.id.slice(0, 8)}</strong><span>{job.mode === "single_image" ? "Single image" : "Multiple images"}</span></div><span>{job.image_count}</span><span>{job.runs.length}</span><span className={`job-status ${job.status}`}>{job.status}</span><time>{new Date(job.created_at).toLocaleString()}</time><div className="job-runs">{job.runs.map((run) => <div key={run.engine_id} className="job-run"><span>{run.engine_name}</span><span className={`job-status ${run.status}`}>{run.status}</span>{run.error && <p>{run.error}</p>}{run.artifacts.map((artifact) => <a key={artifact.url} href={api.artifactUrl(artifact.url)} target="_blank" rel="noreferrer"><ArrowDownToLine size={13}/>{artifact.name}</a>)}</div>)}</div></article>)}</div> : <div className="empty-state large"><Activity size={25}/><strong>No jobs submitted</strong><p>Start a reconstruction from Studio. This list only shows jobs returned by the API.</p><button className="secondary-button" onClick={() => setTab("studio")}>Open Studio</button></div>}</section>}
      {tab === "compare" && <section className="content-view"><div className="page-heading compact"><div><div className="eyebrow"><span className="eyebrow-line"/> OUTPUT INSPECTION</div><h1>Compare <span>3D outputs.</span></h1><p>Inspect actual GLB/GLTF artifacts from completed runs. No sample meshes are preloaded.</p></div><button className="secondary-button" onClick={() => void refresh()}><RefreshCw size={15}/> Refresh</button></div>{completedRuns.length ? <div className="compare-grid">{completedRuns.map((run) => { const artifact = run.artifacts.find((item) => ["glb", "gltf"].includes(item.format.toLowerCase()))!; return <article className="compare-card" key={run.jobId + run.engine_id}><div className="compare-card-heading"><div><strong>{run.engine_name}</strong><span>Job {run.jobId.slice(0, 8)} · {run.mode === "single_image" ? "Single image" : "Multi-view"}</span></div><a className="icon-button" href={api.artifactUrl(artifact.url)} download aria-label={`Download ${artifact.name}`}><ArrowDownToLine size={16}/></a></div><ModelViewer url={api.artifactUrl(artifact.url)} label={run.engine_name}/><div className="compare-meta"><span><Check size={13}/> Real artifact</span><span>{artifact.bytes ? prettyBytes(artifact.bytes) : "Size unavailable"}</span><span>{run.elapsed_seconds != null ? `${run.elapsed_seconds.toFixed(1)} s` : "Runtime unavailable"}</span></div></article>; })}</div> : <div className="empty-state large"><Box size={27}/><strong>No verified models to compare</strong><p>Once an engine finishes and the API validates a real GLB/GLTF artifact, it will appear here.</p><button className="secondary-button" onClick={() => setTab("studio")}>Create a reconstruction</button></div>}</section>}
      <footer className="footer"><span>Mesh3D <span className="footer-dot">·</span> Experimental reconstruction workbench</span><span><span className="footer-live"/> No simulated outputs</span></footer>
    </main>
  </div>;
}