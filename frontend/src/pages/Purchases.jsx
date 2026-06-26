import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

export default function Purchases() {
  const { data: bills, loading, reload } = useFetch("/api/purchases");
  const [open, setOpen] = useState(false);
  const del = async (id) => { if (confirm("Delete this purchase bill?")) { await api.delete(`/api/purchases/${id}`); reload(); } };

  const columns = [
    { header: "Bill No", key: "bill_number" }, { header: "Date", key: "bill_date" },
    { header: "Supplier", key: "supplier" }, { header: "Items", key: "items" },
    { header: "Subtotal", cell: (r) => rupeeFull(r.subtotal) },
    { header: "GST", cell: (r) => rupeeFull(r.gst_amount) },
    { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
    { header: "", cell: (r) => <button className="text-danger" onClick={() => del(r.id)}>Delete</button> },
  ];
  return (
    <div>
      <PageHeader title="Purchases" action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Purchase</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={bills} empty="No purchase bills yet" />}
      {open && <NewPurchase onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
    </div>
  );
}

function NewPurchase({ onClose, onSaved }) {
  const { data: suppliers } = useFetch("/api/suppliers");
  const { data: materials } = useFetch("/api/material-types");
  const [supplierId, setSupplierId] = useState("");
  const [gstType, setGstType] = useState("none");
  const [gstPct, setGstPct] = useState("5");
  const [items, setItems] = useState([]);
  const [mid, setMid] = useState(""); const [qty, setQty] = useState(""); const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const add = () => {
    const m = materials?.find((x) => String(x.id) === String(mid));
    if (!m) return setErr("Select a material");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setItems([...items, { material_type_id: m.id, unit_id: m.unit_id, name: m.name, quantity: Number(qty), rate: Number(rate) || 0 }]);
    setMid(""); setQty(""); setRate(""); setErr("");
  };
  const subtotal = items.reduce((a, b) => a + b.quantity * b.rate, 0);
  const gstAmt = gstType !== "none" ? subtotal * (Number(gstPct) || 0) / 100 : 0;

  const save = async () => {
    if (!supplierId) return setErr("Select a supplier");
    if (!items.length) return setErr("Add at least one item");
    setBusy(true); setErr("");
    try {
      await api.post("/api/purchases", { supplier_id: Number(supplierId), gst_type: gstType,
        gst_percent: Number(gstPct) || 0,
        items: items.map(({ material_type_id, unit_id, quantity, rate }) => ({ material_type_id, unit_id, quantity, rate })) });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title="New Purchase Bill" wide>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Field label="Supplier" required>
          <Select value={supplierId} onChange={setSupplierId}>
            <option value="">— Select Supplier —</option>
            {suppliers?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
        </Field>
        <Field label="GST Type"><Select value={gstType} onChange={setGstType}>
          <option value="none">No GST</option><option value="cgst_sgst">CGST + SGST</option><option value="igst">IGST</option>
        </Select></Field>
        <Field label="GST %"><input className="input" value={gstPct} onChange={(e) => setGstPct(e.target.value)} /></Field>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2 rounded-xl border border-separator bg-bg p-3">
        <div className="min-w-[160px] flex-1"><label className="label">Material</label>
          <Select value={mid} onChange={setMid}><option value="">— Select —</option>
            {materials?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</Select></div>
        <div className="w-24"><label className="label">Qty</label><input className="input" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
        <div className="w-28"><label className="label">Rate</label><input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} /></div>
        <button className="btn-primary" onClick={add}>+ Add</button>
      </div>

      {items.length > 0 && (
        <div className="mt-3 space-y-1">
          {items.map((it, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2 text-sm">
              <span className="text-ink">{it.name}</span>
              <span className="text-ink2">{it.quantity} × {rupeeFull(it.rate)} = {rupeeFull(it.quantity * it.rate)}</span>
              <button className="text-danger" onClick={() => setItems(items.filter((_, x) => x !== i))}>✕</button>
            </div>
          ))}
          <div className="pt-1 text-right text-sm font-bold text-ink">
            Subtotal: {rupeeFull(subtotal)} | GST: {rupeeFull(gstAmt)} | Total: {rupeeFull(subtotal + gstAmt)}
          </div>
        </div>
      )}

      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save Bill"}</button>
      </div>
    </Modal>
  );
}
