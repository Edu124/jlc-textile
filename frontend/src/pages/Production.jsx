import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Spinner } from "../components/ui.jsx";

export default function Production() {
  const { data: jobs, loading, reload } = useFetch("/api/production/jobs");
  const [adjustFor, setAdjustFor] = useState(null);
  const [detailFor, setDetailFor] = useState(null);

  const clear = async (j) => {
    if (!confirm(`Remove the job: ${j.material} → ${j.tailor}? (Any stock already created from it is kept.)`)) return;
    try { await api.delete(`/api/production/jobs/${j.id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "Material", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setDetailFor(r)}>{r.material}</button>
    )},
    { header: "Tailor", key: "tailor" },
    { header: "Given", cell: (r) => `${num(r.qty_given, 2)} ${r.unit}` },
    { header: "With Tailor", cell: (r) => `${num(r.held, 2)} ${r.unit}` },
    { header: "Awaiting Rate", cell: (r) => (r.pending_qty > 0
        ? <span className="font-semibold text-warn">{num(r.pending_qty, 2)} {r.unit}</span> : "—") },
    { header: "In Finished Goods", cell: (r) => (r.finished_qty > 0
        ? <span className="font-semibold text-ok">{num(r.finished_qty, 2)} {r.unit}</span> : "—") },
    { header: "Date", key: "created_at" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setAdjustFor(r)}>Adjust</button>
        <button className="text-danger" onClick={() => clear(r)}>Clear</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Production — Tailor Jobs"
        subtitle="Fabric given to tailors. Reduce 'With Tailor' as work returns — it moves to Products, awaiting a rate, then to Finished Goods once priced." />
      {loading ? <Spinner /> :
        <Table columns={columns} rows={jobs}
               empty="No tailor jobs yet — give material to a tailor from Raw Materials → Adjust." />}
      {adjustFor && <AdjustJob job={adjustFor} onClose={() => setAdjustFor(null)} onSaved={() => { setAdjustFor(null); reload(); }} />}
      {detailFor && <JobDetail job={detailFor} onClose={() => setDetailFor(null)} />}
    </div>
  );
}

function AdjustJob({ job, onClose, onSaved }) {
  const [held, setHeld] = useState(String(job.held));
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const returning = Math.max(0, job.held - (Number(held) || 0));

  const save = async () => {
    setBusy(true); setErr("");
    try { await api.post(`/api/production/jobs/${job.id}/adjust`, { new_held: Number(held) || 0 }); onSaved(); }
    catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title={`${job.material} → ${job.tailor}`}>
      <div className="space-y-3">
        <div className="text-sm text-ink2">Given: <b>{num(job.qty_given, 2)} {job.unit}</b> · Currently with tailor: <b>{num(job.held, 2)} {job.unit}</b></div>
        <Field label="Quantity still with tailor" required>
          <input className="input" inputMode="decimal" value={held} onChange={(e) => setHeld(e.target.value)} />
        </Field>
        {returning > 0 && (
          <div className="rounded-lg bg-warnSoft px-3 py-2 text-xs text-warn">
            {num(returning, 2)} {job.unit} returned → moved to <b>Products</b>, awaiting a rate.
            Set a rate there to move it into Finished Goods.
          </div>
        )}
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}

function JobDetail({ job, onClose }) {
  const rows = [
    ["Raw Material", job.material],
    ["Tailor", job.tailor],
    ["Given out", `${num(job.qty_given, 2)} ${job.unit}`],
    ["Still with tailor", `${num(job.held, 2)} ${job.unit}`],
    ["Total returned so far", `${num(job.qty_returned, 2)} ${job.unit}`],
    ["— Awaiting rate (in Products)", `${num(job.pending_qty, 2)} ${job.unit}`],
    ["— Priced & in Finished Goods", `${num(job.finished_qty, 2)} ${job.unit}`],
    ["Date", job.created_at],
  ];
  return (
    <Modal open onClose={onClose} title="Job Details">
      <div className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-separator/60 py-2 text-sm">
            <span className="text-muted">{k}</span><span className="font-semibold text-ink">{v}</span>
          </div>
        ))}
      </div>
      {job.pending_qty > 0 && (
        <p className="mt-3 text-xs text-warn">
          Go to Products and click "Set Rate" on "{job.material} ({job.tailor})" to move the awaiting quantity into Finished Goods.
        </p>
      )}
    </Modal>
  );
}
