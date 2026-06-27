import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Spinner, StatCard } from "../components/ui.jsx";

export default function FinishedGoods() {
  const { data: rows, loading, reload } = useFetch("/api/finished-goods");
  const [adjustFor, setAdjustFor] = useState(null);

  const totalQty = (rows || []).reduce((a, b) => a + b.quantity, 0);
  const value = (rows || []).reduce((a, b) => a + b.value, 0);

  const columns = [
    { header: "Item", key: "name" },
    { header: "Category", key: "category" },
    { header: "Unit", key: "unit" },
    { header: "In Stock", cell: (r) => num(r.quantity, 2) },
    { header: "Sale Rate", cell: (r) => rupeeFull(r.sale_rate) },
    { header: "Value", cell: (r) => rupeeFull(r.value) },
    { header: "Actions", cell: (r) => <button className="text-accent" onClick={() => setAdjustFor(r)}>Adjust</button> },
  ];

  return (
    <div>
      <PageHeader title="Finished Goods" subtitle="Priced & ready to sell. Job-work returns awaiting a rate live under Products." />
      <div className="mb-4 grid grid-cols-3 gap-4">
        <StatCard label="Items" value={rows?.length || 0} icon="◼" />
        <StatCard label="Total Qty" value={num(totalQty)} icon="◉" accent="#7FA8B8" />
        <StatCard label="Stock Value" value={rupeeFull(value)} icon="₹" accent="#5FB07C" />
      </div>
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No finished goods yet" />}
      {adjustFor && <Adjust row={adjustFor} onClose={() => setAdjustFor(null)} onSaved={() => { setAdjustFor(null); reload(); }} />}
    </div>
  );
}

function Adjust({ row, onClose, onSaved }) {
  const [qty, setQty] = useState(String(row.quantity));
  const [reason, setReason] = useState("Manual Adjustment");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const save = async () => {
    setBusy(true); setErr("");
    try {
      await api.post("/api/finished-goods/adjust", { product_id: row.product_id, new_quantity: Number(qty) || 0, reason });
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
        <Field label="Reason"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button></div>
      </div>
    </Modal>
  );
}
