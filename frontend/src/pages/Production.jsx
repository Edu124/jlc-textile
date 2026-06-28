import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Spinner } from "../components/ui.jsx";

export default function Production() {
  const { data: jobs, loading, reload } = useFetch("/api/production/jobs");
  const [trackFor, setTrackFor] = useState(null);
  const [assignFor, setAssignFor] = useState(null);

  const clear = async (j) => {
    if (!confirm(`Remove the job: ${j.material} → ${j.tailor}? (Any stock already created from it is kept.)`)) return;
    try { await api.delete(`/api/production/jobs/${j.id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const jobsArr = jobs || [];
  const workJobs = jobsArr.filter((j) => (j.tailor_type || "work") === "work");
  const finalJobs = jobsArr.filter((j) => j.tailor_type === "final");

  const piecesCell = (r) => (r.target_pieces > 0
    ? <span className={r.delivered_pieces >= r.target_pieces ? "font-semibold text-ok" : "font-semibold text-ink"}>
        {num(r.delivered_pieces, 0)} / {num(r.target_pieces, 0)}
      </span>
    : <span className="text-muted">set target</span>);

  const workColumns = [
    { header: "Design", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setTrackFor(r)}>{r.material}</button>
    )},
    { header: "Work Tailor", key: "tailor" },
    { header: "Given", cell: (r) => `${num(r.qty_given, 2)} ${r.unit}` },
    { header: "Pieces Ready", cell: piecesCell },
    { header: "To Assign", cell: (r) => (r.ready_to_assign > 0
        ? <span className="font-semibold text-warn">{num(r.ready_to_assign, 0)}</span> : "—") },
    { header: "Date", key: "created_at" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setTrackFor(r)}>Track</button>
        <button className="text-accent disabled:text-muted" disabled={r.ready_to_assign <= 0}
                onClick={() => setAssignFor(r)}>Assign →</button>
        <button className="text-danger" onClick={() => clear(r)}>Clear</button>
      </div>
    )},
  ];

  const finalColumns = [
    { header: "Design", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setTrackFor(r)}>{r.material}</button>
    )},
    { header: "Final Tailor", key: "tailor" },
    { header: "Pieces Given", cell: (r) => num(r.qty_given, 0) },
    { header: "Delivered", cell: piecesCell },
    { header: "In Finished Goods", cell: (r) => (r.finished_qty > 0
        ? <span className="font-semibold text-ok">{num(r.finished_qty, 0)} pcs</span> : "—") },
    { header: "Date", key: "created_at" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setTrackFor(r)}>Track</button>
        <button className="text-danger" onClick={() => clear(r)}>Clear</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Production — Tailor Jobs"
        subtitle="Work tailors stitch fabric into pieces; assign those pieces to final tailors, whose deliveries move into Finished Goods." />
      {loading ? <Spinner /> : (
        <div className="space-y-8">
          <div>
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">Work Tailors (fabric → pieces)</h2>
            <Table columns={workColumns} rows={workJobs}
                   empty="No work-tailor jobs — give fabric to a Work tailor from Raw Materials → Adjust." />
          </div>
          <div>
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">Final Tailors (pieces → finished goods)</h2>
            <Table columns={finalColumns} rows={finalJobs}
                   empty="No final-tailor jobs yet — assign ready pieces from a work tailor above, or give pieces to a Final tailor from Raw Materials." />
          </div>
        </div>
      )}
      {trackFor && <TrackJob job={trackFor} onClose={() => setTrackFor(null)} onChanged={reload} />}
      {assignFor && <AssignFinal job={assignFor} onClose={() => setAssignFor(null)} onSaved={() => { setAssignFor(null); reload(); }} />}
    </div>
  );
}

const SIZES = [["m", "M"], ["l", "L"], ["xl", "XL"], ["xxl", "XXL"], ["mxxl", "M-XXL"]];

function AssignFinal({ job, onClose, onSaved }) {
  const [name, setName] = useState("");
  const [pieces, setPieces] = useState(String(job.ready_to_assign || ""));
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const sizeTotal = SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);
  const effectiveTotal = sizeTotal > 0 ? sizeTotal : (Number(pieces) || 0);

  const save = async () => {
    if (!name.trim()) return setErr("Enter the final tailor's name");
    if (!(effectiveTotal > 0)) return setErr("Enter pieces to assign");
    setBusy(true); setErr("");
    const sizeObj = Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));
    try {
      await api.post(`/api/production/jobs/${job.id}/assign-final`, {
        tailor_name: name.trim(), pieces: Number(pieces) || 0,
        sizes: sizeTotal > 0 ? sizeObj : null });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Assign ${job.material} → Final Tailor`}>
      <div className="space-y-3">
        <div className="rounded-lg bg-surface2 px-3 py-2 text-sm text-ink2">
          <b className="text-ink">{num(job.ready_to_assign, 0)}</b> pieces ready to assign from {job.tailor}.
        </div>
        <Field label="Final Tailor Name" required>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Suresh" />
        </Field>
        <Field label="Pieces to assign" required>
          <input className="input" inputMode="numeric" value={sizeTotal > 0 ? sizeTotal : pieces}
                 disabled={sizeTotal > 0}
                 onChange={(e) => setPieces(e.target.value.replace(/[^0-9]/g, ""))} />
        </Field>
        <div>
          <label className="label">Pieces per size (optional)</label>
          <div className="flex flex-wrap gap-2">
            {SIZES.map(([k, lbl]) => (
              <div key={k} className="w-16 text-center">
                <div className="text-[11px] text-muted">{lbl}</div>
                <input className="input px-1 text-center" inputMode="numeric" value={sizes[k]}
                       onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
              </div>
            ))}
          </div>
          {sizeTotal > 0 && <div className="mt-1 text-xs text-muted">Total from sizes: <b className="text-ink">{sizeTotal}</b></div>}
        </div>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Assign"}</button>
        </div>
      </div>
    </Modal>
  );
}

function TrackJob({ job, onClose, onChanged }) {
  const { data: deliveries, reload: reloadDeliveries } = useFetch(`/api/production/jobs/${job.id}/deliveries`);
  const { data: jobData, reload: reloadJob } = useFetch(`/api/production/jobs/${job.id}`);
  const j = jobData || job;

  const [target, setTarget] = useState(String(job.target_pieces || ""));
  const [savingTarget, setSavingTarget] = useState(false);

  const [pieces, setPieces] = useState("");
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [dDate, setDDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const sizeTotal = SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);

  const refreshAll = () => { reloadDeliveries(); reloadJob(); onChanged?.(); };

  const saveTarget = async () => {
    setSavingTarget(true);
    try { await api.post(`/api/production/jobs/${job.id}/target`, { target_pieces: Number(target) || 0 }); refreshAll(); }
    catch (e) { setErr(apiError(e)); } finally { setSavingTarget(false); }
  };

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImage(reader.result);
    reader.readAsDataURL(file);
  };

  const addDelivery = async () => {
    const effective = sizeTotal > 0 ? sizeTotal : (Number(pieces) || 0);
    if (!(effective > 0)) return setErr("Enter pieces delivered");
    setBusy(true); setErr("");
    const sizeObj = Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));
    try {
      await api.post(`/api/production/jobs/${job.id}/deliveries`, {
        delivery_date: dDate, pieces: Number(pieces) || 0,
        sizes: sizeTotal > 0 ? sizeObj : null, image_base64: image, notes });
      setPieces(""); setSizes({ m: "", l: "", xl: "", xxl: "", mxxl: "" }); setNotes(""); setImage(null);
      refreshAll();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  const removeDelivery = async (id) => {
    if (!confirm("Remove this delivery record?")) return;
    await api.delete(`/api/production/jobs/${job.id}/deliveries/${id}`); refreshAll();
  };

  const delivered = j.delivered_pieces || 0;
  const targetNum = j.target_pieces || 0;
  const remaining = Math.max(0, targetNum - delivered);

  return (
    <Modal open onClose={onClose} title={`${job.material} → ${job.tailor}`} wide>
      {/* Target */}
      <div className="rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Piece Target</div>
        <div className="flex items-end gap-2">
          <div className="w-32">
            <label className="label">Target pieces</label>
            <input className="input" inputMode="numeric" value={target}
                   onChange={(e) => setTarget(e.target.value.replace(/[^0-9]/g, ""))} />
          </div>
          <button className="btn-ghost" onClick={saveTarget} disabled={savingTarget}>{savingTarget ? <Spinner /> : "Save Target"}</button>
          {targetNum > 0 && (
            <div className="ml-auto text-right text-sm">
              <span className="font-bold text-ink">{num(delivered, 0)}</span>
              <span className="text-muted"> / {num(targetNum, 0)} done · </span>
              <span className={remaining === 0 ? "font-semibold text-ok" : "font-semibold text-warn"}>{num(remaining, 0)} left</span>
            </div>
          )}
        </div>
      </div>

      {/* Add delivery */}
      <div className="mt-4 rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Log Ready Pieces</div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-28"><label className="label">Date</label>
            <input type="date" className="input" value={dDate} onChange={(e) => setDDate(e.target.value)} /></div>
          <div className="w-24"><label className="label">Pieces</label>
            <input className="input" inputMode="numeric" value={sizeTotal > 0 ? sizeTotal : pieces}
                   disabled={sizeTotal > 0}
                   onChange={(e) => setPieces(e.target.value.replace(/[^0-9]/g, ""))} /></div>
          <div className="min-w-[140px] flex-1"><label className="label">Notes</label>
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="optional" /></div>
          <div>
            <label className="label">Photo</label>
            <input type="file" accept="image/*" capture="environment" onChange={onFile} className="hidden" id={`photo-${job.id}`} />
            <label htmlFor={`photo-${job.id}`} className="btn-ghost inline-block cursor-pointer">{image ? "✓ Photo" : "📷 Add"}</label>
          </div>
          <button className="btn-primary" onClick={addDelivery} disabled={busy}>{busy ? <Spinner /> : "+ Add"}</button>
        </div>
        <div className="mt-2">
          <label className="label">Pieces per size (optional)</label>
          <div className="flex flex-wrap gap-2">
            {SIZES.map(([k, lbl]) => (
              <div key={k} className="w-16 text-center">
                <div className="text-[11px] text-muted">{lbl}</div>
                <input className="input px-1 text-center" inputMode="numeric" value={sizes[k]}
                       onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
              </div>
            ))}
          </div>
        </div>
        {image && <img src={image} alt="preview" className="mt-2 h-20 rounded-lg border border-separator object-cover" />}
        {err && <div className="mt-2 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      </div>

      {/* Delivery log */}
      <div className="mt-4">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Delivery Log</div>
        {!deliveries?.length ? (
          <div className="rounded-lg bg-surface2 px-3 py-4 text-center text-sm text-muted">No deliveries logged yet</div>
        ) : (
          <div className="space-y-2">
            {deliveries.map((d) => (
              <div key={d.id} className="flex items-center gap-3 rounded-lg bg-surface2 px-3 py-2">
                {d.image
                  ? <img src={d.image} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" />
                  : <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-bg text-muted">—</div>}
                <div className="flex-1">
                  <div className="text-sm font-semibold text-ink">
                    {num(d.pieces, 0)} pieces
                    {d.sizes && SIZES.some(([k]) => d.sizes[k] > 0) && (
                      <span className="ml-2 text-xs font-normal text-muted">
                        ({SIZES.filter(([k]) => d.sizes[k] > 0).map(([k, l]) => `${l}:${num(d.sizes[k], 0)}`).join("  ")})
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-muted">{d.delivery_date}{d.notes ? ` · ${d.notes}` : ""}</div>
                </div>
                <button className="text-danger" onClick={() => removeDelivery(d.id)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-end">
        <button className="btn-ghost" onClick={onClose}>Close</button>
      </div>
    </Modal>
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
