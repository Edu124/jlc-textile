import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { PageHeader, Field, Select, Spinner, Card } from "../components/ui.jsx";

const PRESETS = ["floral pattern", "geometric pattern", "paisley motif", "striped fabric", "checkered pattern", "abstract art print"];

export default function AIStudio() {
  const { data: gallery, reload } = useFetch("/api/ai/gallery");
  const [mode, setMode] = useState("text_to_image");
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [srcB64, setSrcB64] = useState("");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const pickSource = (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const r = new FileReader(); r.onload = () => setSrcB64(r.result); r.readAsDataURL(f);
  };

  const generate = async () => {
    if (!prompt.trim()) return setErr("Enter a description");
    if (mode === "image_to_image" && !srcB64) return setErr("Choose a source image");
    setBusy(true); setErr(""); setResult("");
    try {
      const { data } = await api.post("/api/ai/generate",
        { prompt, mode, source_image_base64: srcB64 || null });
      setResult(data.image_base64);
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  const save = async () => {
    await api.post("/api/ai/save", { name: name || prompt.slice(0, 30), prompt, mode, image_base64: result });
    setResult(""); setName(""); reload();
  };

  return (
    <div>
      <PageHeader title="AI Design Studio" subtitle="Generate fabric & garment designs" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
        <Card>
          <Field label="Mode"><Select value={mode} onChange={setMode}>
            <option value="text_to_image">Text → Image</option>
            <option value="image_to_image">Image → Image</option>
          </Select></Field>
          <div className="mt-3">
            <Field label="Describe the design" required>
              <textarea className="input" rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. blue floral pattern on white cotton, traditional Indian motif" />
            </Field>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button key={p} onClick={() => setPrompt(prompt ? `${prompt}, ${p}` : p)}
                className="rounded-lg bg-surface2 px-2.5 py-1 text-xs text-ink3 hover:bg-surface3 hover:text-ink">{p}</button>
            ))}
          </div>
          {mode === "image_to_image" && (
            <div className="mt-3"><Field label="Source Image"><input type="file" accept="image/*" onChange={pickSource} className="text-sm text-ink3" /></Field></div>
          )}
          <div className="mt-3"><Field label="Design Name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="optional" /></Field></div>
          {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
          <button className="btn-primary mt-4 w-full" onClick={generate} disabled={busy}>
            {busy ? <><Spinner /> Generating…</> : "✦ Generate Design"}</button>
          <p className="mt-2 text-[11px] text-muted">Text→Image is free. Image→Image needs a Stability AI key in Settings.</p>
        </Card>

        <Card title="Result">
          <div className="flex min-h-[300px] items-center justify-center rounded-xl bg-bg">
            {busy ? <Spinner className="h-8 w-8" /> :
             result ? <img src={result} alt="design" className="max-h-[360px] rounded-lg" /> :
             <span className="text-sm text-muted">Generate a design to see it here</span>}
          </div>
          {result && <button className="btn-success mt-3" onClick={save}>Save to Gallery</button>}
        </Card>
      </div>

      <h3 className="mb-3 mt-6 text-xs font-bold uppercase tracking-wide text-muted">Design Gallery</h3>
      {gallery?.length ? (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {gallery.map((d) => (
            <div key={d.id} className="card overflow-hidden">
              <img src={d.image} alt={d.name} className="aspect-square w-full object-cover" />
              <div className="truncate p-2 text-[11px] text-ink3">{d.name}</div>
            </div>
          ))}
        </div>
      ) : <p className="text-sm text-muted">No designs yet</p>}
    </div>
  );
}
