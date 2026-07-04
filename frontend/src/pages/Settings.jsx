import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError, downloadFile } from "../lib/useFetch.js";
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

  const downloadBackup = () => downloadFile("/api/backup", `jlc-backup-${new Date().toISOString().slice(0, 10)}.json`);

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

      <Card title="Privacy" className="mt-4">
        <Field label="Amount PIN (unlocks ₹ amounts in Order Forms)">
          <input className="input" type="password" inputMode="numeric" value={form.amount_pin || ""}
                 onChange={(e) => setForm({ ...form, amount_pin: e.target.value })}
                 placeholder="leave blank to keep current PIN" />
        </Field>
        <p className="mt-2 text-[11px] text-muted">Default PIN is 1234. Amounts show as *** until this PIN is entered.</p>
      </Card>

      <Card title="Backup" className="mt-4">
        <p className="mb-3 text-sm text-ink2">Download a full copy of all your data (safety backup).</p>
        <button className="btn-ghost" onClick={downloadBackup}>⬇ Download Backup (JSON)</button>
      </Card>

      <ChangePassword />

      <div className="mt-5 flex items-center gap-3">
        <button className="btn-primary w-40" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save Settings"}</button>
        {saved && <span className="text-sm text-ok">Saved ✓</span>}
      </div>
    </div>
  );
}

function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);

  const save = async () => {
    setErr(""); setOk(false);
    if (!current || !next) return setErr("Fill in both passwords");
    if (next !== confirm) return setErr("New passwords don't match");
    setBusy(true);
    try {
      await api.post("/api/auth/change-password", { current_password: current, new_password: next });
      setCurrent(""); setNext(""); setConfirm(""); setOk(true);
      setTimeout(() => setOk(false), 3000);
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Card title="Change Password" className="mt-4">
      <p className="mb-3 text-sm text-ink2">Forgot the shared shop password? Set a new one here while you're still logged in.</p>
      <div className="space-y-3">
        <Field label="Current Password">
          <input className="input" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label="New Password">
          <input className="input" type="password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        <Field label="Confirm New Password">
          <input className="input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
      </div>
      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <button className="btn-primary mt-3 w-40" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Update Password"}</button>
      {ok && <span className="ml-3 text-sm text-ok">Password updated ✓</span>}
    </Card>
  );
}
