import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Badge, Spinner } from "../components/ui.jsx";

export default function Production() {
  const { data: batches, loading, reload } = useFetch("/api/production");
  const [open, setOpen] = useState(false);

  const advance = async (b) => {
    try { const { data } = await api.post(`/api/production/${b.id}/advance`, { notes: "" }); reload();
      if (data.stage === "Completed") alert("Batch completed — finished goods stock updated."); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "Batch #", key: "batch_number" }, { header: "Product", key: "product" },
    { header: "Qty", cell: (r) => num(r.quantity) },
    { header: "Stage", cell: (r) => <Badge status={r.current_stage} /> },
    { header: "Started", cell: (r) => (r.started_at || "").slice(0, 10) },
    { header: "Actions", cell: (r) => r.current_stage !== "Completed"
      ? <button className="text-ok" onClick={() => advance(r)}>Advance Stage</button>
      : <span className="text-muted">Done</span> },
  ];
  return (
    <div>
      <PageHeader title="Production" action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Batch</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={batches} empty="No production batches yet" />}
      {open && <NewBatch onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
    </div>
  );
}

function NewBatch({ onClose, onSaved }) {
  const { data: products } = useFetch("/api/products");
  const [pid, setPid] = useState(""); const [qty, setQty] = useState(""); const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const save = async () => {
    if (!pid) return setErr("Select a product");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setBusy(true); setErr("");
    try { await api.post("/api/production", { product_id: Number(pid), quantity: Number(qty), notes }); onSaved(); }
    catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title="New Production Batch">
      <div className="space-y-3">
        <Field label="Product" required><Select value={pid} onChange={setPid}>
          <option value="">— Select —</option>{products?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select></Field>
        <Field label="Quantity" required><input className="input" inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value)} /></Field>
        <Field label="Notes"><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Start Batch"}</button></div>
      </div>
    </Modal>
  );
}
