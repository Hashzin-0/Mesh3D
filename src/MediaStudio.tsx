import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Film, Image as ImageIcon, LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { api, type MediaEngineStatus, type MediaGeneration } from "./api";

const statusCopy: Record<string, string> = {
  queued: "Queued in local ComfyUI",
  running: "Generating on the configured local runtime",
  completed: "Generation completed",
  failed: "Generation failed"
};

export default function MediaStudio() {
  const [kind, setKind] = useState<"image" | "video">("image");
  const [prompt, setPrompt] = useState("");
  const [engine, setEngine] = useState<MediaEngineStatus | null>(null);
  const [generation, setGeneration] = useState<MediaGeneration | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const refreshEngine = useCallback(async () => {
    try { setEngine(await api.mediaEngines()); } catch (e) { setError(e instanceof Error ? e.message : "Could not inspect local media runtime."); }
  }, []);
  useEffect(() => { void refreshEngine(); }, [refreshEngine]);
  useEffect(() => {
    if (!generation || ["completed", "failed"].includes(generation.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.mediaJob(generation.id);
        setGeneration((current) => current?.id === next.id ? next : current);
        if (next.status === "failed") setError("The local workflow failed. Inspect the ComfyUI queue and server logs.");
      } catch (e) { setError(e instanceof Error ? e.message : "Could not refresh generation status."); }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [generation?.id, generation?.status]);
  const activeStatus = engine?.[kind];
  const submit = async () => {
    setError("");
    if (!prompt.trim()) { setError("Enter a prompt before generating."); return; }
    setBusy(true);
    try {
      const result = await api.generateMedia(kind, prompt);
      setGeneration(result);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not submit the local workflow."); }
    finally { setBusy(false); }
  };
  return <section className="media-studio">
    <div className="page-heading media-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> LOCAL GENERATIVE WORKSPACE</div><h1>Create <span>images and video.</span></h1><p>Run locally hosted open-weight models through ComfyUI. No paid generation API is called.</p></div><button className="secondary-button" onClick={() => void refreshEngine()}><RefreshCw size={15}/> Check runtime</button></div>
    <div className="media-grid">
      <section className="panel media-form">
        <div className="panel-heading"><div><span className="step-index">01</span><h2>Generation settings</h2></div><span className="subtle-tag"><Sparkles size={14}/> Self-hosted</span></div>
        <div className="media-kind-toggle" role="group" aria-label="Generation type">
          <button className={kind === "image" ? "media-kind active" : "media-kind"} onClick={() => { setKind("image"); setGeneration(null); }}><ImageIcon size={17}/> Image</button>
          <button className={kind === "video" ? "media-kind active" : "media-kind"} onClick={() => { setKind("video"); setGeneration(null); }}><Film size={17}/> Video</button>
        </div>
        <label className="media-label" htmlFor="media-prompt">Prompt</label>
        <textarea id="media-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={8000} rows={7} placeholder={kind === "image" ? "Describe the image, subject, lighting, style, composition..." : "Describe the scene, camera movement, subject motion, lighting..."} />
        <div className="media-prompt-footer"><span>Up to 8,000 characters</span><span>{prompt.length}/8000</span></div>
        <div className={activeStatus?.ready ? "runtime-status ready" : "runtime-status"}><span className="runtime-dot"/><div><strong>{kind === "image" ? "Image workflow" : "Video workflow"} · {activeStatus?.ready ? "Ready" : "Not configured"}</strong><p>{activeStatus?.reason ?? "Checking local ComfyUI runtime..."}</p></div></div>
        {error && <div className="media-error" role="alert"><AlertCircle size={16}/><span>{error}</span></div>}
        <button className="primary-button media-submit" disabled={busy || !activeStatus?.ready || !prompt.trim()} onClick={() => void submit()}>{busy ? <LoaderCircle className="spin" size={16}/> : <Sparkles size={16}/>} Generate {kind === "image" ? "image" : "video"} <span>→</span></button>
        <p className="media-footnote">Generation requires a running ComfyUI instance, an API-format workflow, installed model weights, and a compatible runtime. Vercel Functions do not provide GPU inference.</p>
      </section>
      <section className="panel media-output">
        <div className="panel-heading"><div><span className="step-index">02</span><h2>Output</h2></div>{generation && <span className="counter">{generation.status}</span>}</div>
        {!generation && <div className="media-empty"><div className="media-empty-icon">{kind === "image" ? <ImageIcon size={26}/> : <Film size={26}/>}</div><strong>Your generated {kind} will appear here</strong><p>Outputs are shown only when returned by the configured local engine. No sample or simulated media is inserted.</p></div>}
        {generation && <div className="generation-result">
          <div className="generation-status">{["queued", "running"].includes(generation.status) ? <LoaderCircle className="spin" size={17}/> : generation.status === "completed" ? <CheckCircle2 size={17}/> : <AlertCircle size={17}/>}<span>{statusCopy[generation.status] ?? generation.status}</span></div>
          {generation.status === "completed" && generation.outputs.length === 0 && <p className="media-result-note">The workflow completed but no supported image/video output was reported. Check its Save Image/Video node and workflow output mapping.</p>}
          <div className="media-artifacts">{generation.outputs.map((output, index) => {
            const url = api.mediaArtifactUrl(output);
            const isVideo = /\.(mp4|webm|mov|mkv)$/i.test(output.filename);
            return <div className="media-artifact" key={output.filename + output.subfolder + index}>{isVideo ? <video controls preload="metadata" src={url}/> : <img loading="lazy" src={url} alt={output.filename}/>}<a href={url} download={output.filename}>{output.filename}</a></div>;
          })}</div>
        </div>}
      </section>
    </div>
  </section>;
}
