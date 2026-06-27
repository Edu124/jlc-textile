import { useRef, useState } from "react";
import api from "../api";
import { apiError } from "../lib/useFetch.js";
import { PageHeader, Field, Spinner } from "../components/ui.jsx";

// Heuristic parse of raw OCR text off a visiting/business card.
function parseCard(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const phoneMatch = text.match(/(?:\+?91[-\s]?)?[6-9]\d{9}/);
  const emailMatch = text.match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
  const gstMatch = text.match(/\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]\b/i);

  // Name guess: first line that isn't the phone/email/gst and looks like words,
  // not all-caps tagline/company keywords are common on the second line.
  const skipWords = ["www", "http", "@", "gst", "mob", "tel", "fax", "ph."];
  let name = "";
  for (const l of lines) {
    const lower = l.toLowerCase();
    if (phoneMatch && l.includes(phoneMatch[0])) continue;
    if (emailMatch && l.includes(emailMatch[0])) continue;
    if (skipWords.some((w) => lower.includes(w))) continue;
    if (/^\d+$/.test(l)) continue;
    name = l;
    break;
  }

  return {
    name,
    phone: phoneMatch ? phoneMatch[0].replace(/[^\d]/g, "").slice(-10) : "",
    email: emailMatch ? emailMatch[0] : "",
    gst_number: gstMatch ? gstMatch[0].toUpperCase() : "",
    address: lines.filter((l) => l !== name).join(", "),
  };
}

export default function VisitingCards() {
  const fileRef = useRef(null);
  const [imgUrl, setImgUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [rawText, setRawText] = useState("");
  const [form, setForm] = useState({ name: "", phone: "", email: "", address: "", gst_number: "" });
  const [err, setErr] = useState(""); const [saved, setSaved] = useState([]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErr(""); setBusy(true); setRawText("");
    const url = URL.createObjectURL(file);
    setImgUrl(url);
    try {
      const Tesseract = await import("tesseract.js");
      const { data } = await Tesseract.recognize(file, "eng");
      setRawText(data.text);
      setForm(parseCard(data.text));
    } catch (e) {
      setErr("Could not read the card — fill the details in manually.");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!form.name.trim()) return setErr("Enter at least a name");
    setBusy(true); setErr("");
    try {
      const { data } = await api.post("/api/customers", form);
      setSaved([{ ...form, id: data.id }, ...saved]);
      setForm({ name: "", phone: "", email: "", address: "", gst_number: "" });
      setRawText(""); setImgUrl("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Visiting Cards" subtitle="Scan a visiting card to capture exhibition leads — works without internet" />

      <div className="card grid grid-cols-1 gap-5 p-5 lg:grid-cols-2">
        <div>
          <input ref={fileRef} type="file" accept="image/*" capture="environment"
                 onChange={onFile} className="hidden" id="card-input" />
          <label htmlFor="card-input"
                 className="btn-primary inline-flex cursor-pointer items-center gap-2">
            📷 Scan Visiting Card
          </label>

          {imgUrl && (
            <img src={imgUrl} alt="card" className="mt-4 max-h-64 rounded-xl border border-separator object-contain" />
          )}
          {busy && !form.name && (
            <div className="mt-3 flex items-center gap-2 text-sm text-muted"><Spinner /> Reading card…</div>
          )}
          {rawText && (
            <details className="mt-3 text-xs text-muted">
              <summary className="cursor-pointer">Raw OCR text</summary>
              <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-surface2 p-2">{rawText}</pre>
            </details>
          )}
        </div>

        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Review &amp; Save</div>
          <div className="space-y-3">
            <Field label="Name" required>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Phone">
              <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            <Field label="Email">
              <input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Address / Company">
              <textarea className="input" rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </Field>
            <Field label="GST Number">
              <input className="input" value={form.gst_number} onChange={(e) => setForm({ ...form, gst_number: e.target.value })} />
            </Field>
          </div>
          {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
          <button className="btn-success mt-4 w-full" onClick={save} disabled={busy}>
            {busy ? <Spinner /> : "Save Lead as Customer"}
          </button>
        </div>
      </div>

      {saved.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Captured this session ({saved.length})</div>
          <div className="space-y-1">
            {saved.map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2 text-sm">
                <span className="text-ink">{s.name}</span>
                <span className="text-ink2">{s.phone} {s.email && `· ${s.email}`}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
