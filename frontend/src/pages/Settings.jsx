import { useEffect, useState } from "react";
import api from "../api";
import { useFetch } from "../lib/useFetch.js";
import { PageHeader, Field, Card, Spinner } from "../components/ui.jsx";

const FIELDS = [
  ["company_name", "Company Name"], ["company_tagline", "Tagline"],
  ["gst_number", "GST Number"], ["phone", "Mobile"], ["email", "Email"],
  ["instagram", "Instagram"], ["address", "Address"],
];

export default function Settings() {
  const { data, loading } = useFetch("/api/settings");
  const [form, setForm] = useState({});
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (data) setForm(data); }, [data]);

  const save = async () => {
    setBusy(true); setSaved(false);
    await api.put("/api/settings", { values: form });
    setBusy(false); setSaved(true); setTimeout(() => setSaved(false), 2500);
  };

  const downloadBackup = () => window.open("/api/backup", "_blank");

  if (loading) return <Spinner />;
  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" />
      <Card title="Company Information (printed on order forms)">
        <div className="space-y-3">
          {FIELDS.map(([k, label]) => (
            <Field key={k} label={label}>
              {k === "address"
                ? <textarea className="input" rows={2} value={form[k] || ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                : <input className="input" value={form[k] || ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />}
            </Field>
          ))}
        </div>
      </Card>

      <Card title="AI" className="mt-4">
        <Field label="Stability AI Key (for Image → Image)">
          <input className="input" type="password" value={form.ai_api_key || ""} onChange={(e) => setForm({ ...form, ai_api_key: e.target.value })} placeholder="optional" />
        </Field>
        <p className="mt-2 text-[11px] text-muted">Text→Image is free (no key). Image→Image needs a key from stability.ai</p>
      </Card>

      <Card title="Backup" className="mt-4">
        <p className="mb-3 text-sm text-ink2">Download a full copy of all your data (safety backup).</p>
        <button className="btn-ghost" onClick={downloadBackup}>⬇ Download Backup (JSON)</button>
      </Card>

      <div className="mt-5 flex items-center gap-3">
        <button className="btn-primary w-40" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save Settings"}</button>
        {saved && <span className="text-sm text-ok">Saved ✓</span>}
      </div>
    </div>
  );
}
