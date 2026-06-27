import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Badge, Spinner, StatCard, EmptyState } from "../components/ui.jsx";

const REASONS = ["Given to tailor", "Given to customer", "Other"];
const NAME_LABEL = { "Given to tailor": "Tailor name", "Given to customer": "Customer name", "Other": "Name / note" };

export default function RawMaterials() {
  const { data: rows, loading, reload } = useFetch("/api/raw-materials");
  const [addOpen, setAddOpen] = useState(false);
  const [adjustFor, setAdjustFor] = useState(null);
  const [distFor, setDistFor] = useState(null);

  const total = rows?.length || 0;
  const value = (rows || []).reduce((a, b) => a + b.value, 0);
  const low = (rows || []).filter((r) => r.status === "Low Stock").length;

  const columns = [
    { header: "Material", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setDistFor(r)}>{r.name}</button>
    )},
    { header: "Unit", key: "unit" },
    { header: "In Stock", cell: (r) => num(r.quantity, 2) },
    { header: "Avg Rate", cell: (r) => rupeeFull(r.avg_rate) },
    { header: "Value", cell: (r) => rupeeFull(r.value) },
    { header: "Status", cell: (r) => <Badge status={r.status} /> },
    { header: "Actions", cell: (r) => <button className="text-accent" onClick={() => setAdjustFor(r)}>Adjust</button> },
  ];

  return (
    <div>
      <PageHeader title="Raw Materials" subtitle="Tap a material name to see where it was given"
        action={<button className="btn-primary" onClick={() => setAddOpen(true)}>+ Add Stock</button>} />
      <div className="mb-4 grid grid-cols-3 gap-4">
        <StatCard label="Materials" value={total} icon="◈" />
        <StatCard label="Stock Value" value={rupeeFull(value)} icon="₹" accent="#5FB07C" />
        <StatCard label="Low Stock" value={low} icon="⚠" accent="#D9685F" />
      </div>
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No materials yet" />}
      {addOpen && <AddStock onClose={() => setAddOpen(false)} onSaved={() => { setAddOpen(false); reload(); }} />}
      {adjustFor && <Adjust row={adjustFor} onClose={() => setAdjustFor(null)} onSaved={() => { setAdjustFor(null); reload(); }} />}
      {distFor && <DistributionModal row={distFor} onClose={() => setDistFor(null)} />}
    </div>
  );
}

function AddStock({ onClose, onSaved }) {
  const { data: materials } = useFetch("/api/material-types");
  const [mid, setMid] = useState(""); const [qty, setQty] = useState(""); const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const save = async () => {
    if (!mid) return setErr("Select material");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setBusy(true); setErr("");
    try { await api.post("/api/raw-materials/stock-entry", { material_type_id: Number(mid), quantity: Number(qty), rate: Number(rate) || 0 }); onSaved(); }
    catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title="Add Stock Entry">
      <div className="space-y-3">
        <Field label="Material" required><Select value={mid} onChange={setMid}>
          <option value="">— Select —</option>{materials?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </Select></Field>
        <Field label="Quantity" required><input className="input" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} /></Field>
        <Field label="Rate per unit" required><input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Add"}</button></div>
      </div>
    </Modal>
  );
}

function Adjust({ row, onClose, onSaved }) {
  const [qty, setQty] = useState(String(row.quantity));
  const [reason, setReason] = useState("Given to tailor");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const given = Math.max(0, row.quantity - (Number(qty) || 0));

  const save = async () => {
    setBusy(true); setErr("");
    try {
      await api.post(`/api/raw-materials/${row.id}/adjust`, {
        new_quantity: Number(qty) || 0, reason_type: reason, recipient_name: name,
      });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Adjust — ${row.name}`}>
      <div className="space-y-3">
        <div className="text-sm text-ink2">Current stock: <b>{num(row.quantity, 2)} {row.unit}</b></div>
        <Field label="New Quantity" required>
          <input className="input" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
        </Field>
        {given > 0 && (
          <div className="rounded-lg bg-surface2 px-3 py-2 text-xs text-ink3">
            Sending out <b className="text-ink">{num(given, 2)} {row.unit}</b>
            {reason === "Given to tailor" && " → a Production job will be created"}
          </div>
        )}
        <Field label="Reason" required>
          <Select value={reason} onChange={setReason}>
            {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </Field>
        <Field label={NAME_LABEL[reason] + " (optional)"}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                 placeholder={reason === "Given to tailor" ? "e.g. Ramesh" : ""} />
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}

function DistributionModal({ row, onClose }) {
  const { data, loading } = useFetch(`/api/raw-materials/${row.id}/distributions`);
  return (
    <Modal open onClose={onClose} title={`${row.name} — Given to`}>
      {loading ? <Spinner /> : (!data?.items?.length ? <EmptyState>Nothing given out yet</EmptyState> : (
        <div className="space-y-2">
          {data.items.map((it, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2.5">
              <div>
                <div className="text-sm font-semibold text-ink">{it.name}</div>
                <div className="text-xs text-muted">{it.recipient_type} · {it.date}</div>
              </div>
              <div className="text-sm font-bold text-ink">{num(it.quantity, 2)} {row.unit}</div>
            </div>
          ))}
        </div>
      ))}
    </Modal>
  );
}
