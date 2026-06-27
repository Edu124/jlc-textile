import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

export default function Products() {
  const { data: rows, loading, reload } = useFetch("/api/products");
  const [editing, setEditing] = useState(null);   // add/edit modal
  const [rateFor, setRateFor] = useState(null);   // set-rate modal

  const del = async (id, name) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try { await api.delete(`/api/products/${id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "Name", cell: (r) => (
      <span>{r.name}{r.pending_qty > 0 && <span className="ml-2 chip bg-warnSoft text-warn">Pending Rate</span>}</span>
    )},
    { header: "Category", key: "category" },
    { header: "Unit", key: "unit" },
    { header: "Sale Rate", cell: (r) => (r.sale_rate > 0 ? rupeeFull(r.sale_rate) : "—") },
    { header: "Awaiting Rate", cell: (r) => (r.pending_qty > 0
        ? <span className="font-semibold text-warn">{num(r.pending_qty, 2)}</span> : "—") },
    { header: "In Finished Goods", cell: (r) => (r.finished_qty > 0
        ? <span className="font-semibold text-ok">{num(r.finished_qty, 2)}</span> : "—") },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        {r.pending_qty > 0 && <button className="text-warn font-semibold" onClick={() => setRateFor(r)}>Set Rate</button>}
        <button className="text-accent" onClick={() => setEditing(r)}>Edit</button>
        <button className="text-danger" onClick={() => del(r.id, r.name)}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Products" subtitle="Your designs — pick these when billing. Job-work returns appear here awaiting a rate."
        action={<button className="btn-primary" onClick={() => setEditing({})}>+ Add Product</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No products yet" />}
      {editing !== null && (
        <ProductForm initial={editing} onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }} />
      )}
      {rateFor && (
        <SetRateModal product={rateFor} onClose={() => setRateFor(null)}
          onSaved={() => { setRateFor(null); reload(); }} />
      )}
    </div>
  );
}

const SIZE_RATES = [["rate_m", "M"], ["rate_l", "L"], ["rate_xl", "XL"], ["rate_xxl", "XXL"], ["rate_mxxl", "M-XXL"]];

function ProductForm({ initial, onClose, onSaved }) {
  const isEdit = !!initial.id;
  const [name, setName] = useState(initial.name || "");
  const [categoryId, setCategoryId] = useState(initial.category_id || "");
  const [unitId, setUnitId] = useState(initial.unit_id || "");
  const [rate, setRate] = useState(initial.sale_rate ? String(initial.sale_rate) : "");
  const [sizeRates, setSizeRates] = useState(() =>
    Object.fromEntries(SIZE_RATES.map(([k]) => [k, initial[k] ? String(initial[k]) : ""])));
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const { data: categories } = useFetch("/api/categories");
  const { data: units } = useFetch("/api/units");

  const save = async () => {
    if (!name.trim()) return setErr("Name is required");
    setBusy(true); setErr("");
    const payload = { name: name.trim(), category_id: categoryId ? Number(categoryId) : null,
      unit_id: unitId ? Number(unitId) : null, sale_rate: Number(rate) || 0, description: "",
      ...Object.fromEntries(SIZE_RATES.map(([k]) => [k, Number(sizeRates[k]) || 0])) };
    try {
      if (isEdit) await api.put(`/api/products/${initial.id}`, payload);
      else await api.post("/api/products", payload);
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Product" : "Add Product"}>
      <div className="space-y-3">
        <Field label="Name (Design No.)" required>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. D-204" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category"><Select value={categoryId} onChange={setCategoryId}>
            <option value="">— Select —</option>{categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select></Field>
          <Field label="Unit"><Select value={unitId} onChange={setUnitId}>
            <option value="">— Select —</option>{units?.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </Select></Field>
        </div>

        <div className="rounded-xl border border-separator bg-bg p-3">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Size-wise Rates</div>
          <p className="mb-2 text-[11px] text-muted">
            Set a rate per size. Bills auto-calculate from these. Blank sizes use the Base Rate below.
          </p>
          <div className="grid grid-cols-5 gap-2">
            {SIZE_RATES.map(([k, lbl]) => (
              <div key={k}>
                <label className="mb-1 block text-center text-[11px] font-semibold text-ink3">{lbl}</label>
                <input className="input px-1 text-center" inputMode="decimal" value={sizeRates[k]}
                       onChange={(e) => setSizeRates({ ...sizeRates, [k]: e.target.value })} />
              </div>
            ))}
          </div>
        </div>

        <Field label="Base Rate (fallback for blank sizes)">
          <input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} />
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}

function SetRateModal({ product, onClose, onSaved }) {
  const [rate, setRate] = useState(product.sale_rate > 0 ? String(product.sale_rate) : "");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const save = async () => {
    if (!(Number(rate) > 0)) return setErr("Enter a valid rate");
    setBusy(true); setErr("");
    try {
      await api.post(`/api/products/${product.id}/set-rate`, { rate: Number(rate) });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Set Rate — ${product.name}`}>
      <div className="space-y-3">
        <div className="rounded-lg bg-warnSoft px-3 py-2.5 text-sm text-warn">
          <b>{num(product.pending_qty, 2)} {product.unit}</b> is awaiting a rate from job-work returns.
        </div>
        <Field label="Rate per unit" required>
          <input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="e.g. 650" />
        </Field>
        <p className="text-xs text-muted">
          Once saved, all {num(product.pending_qty, 2)} {product.unit} moves into Finished Goods at this rate.
        </p>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-success" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Set Rate & Move to Finished Goods"}</button>
        </div>
      </div>
    </Modal>
  );
}
