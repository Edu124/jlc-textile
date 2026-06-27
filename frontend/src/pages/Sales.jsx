import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError, openPdf } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

const SIZES = [["qty_m", "M"], ["qty_l", "L"], ["qty_xl", "XL"], ["qty_xxl", "XXL"], ["qty_mxxl", "M-XXL"]];

export default function Sales() {
  const { data: bills, loading, reload } = useFetch("/api/sales");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const del = async (id) => {
    if (!confirm("Delete this order form?")) return;
    await api.delete(`/api/sales/${id}`); reload();
  };

  const columns = [
    { header: "Bill No", key: "bill_number" },
    { header: "Date", key: "bill_date" },
    { header: "Party", key: "customer" },
    { header: "Designs", key: "designs" },
    { header: "Total Qty", cell: (r) => num(r.total_qty) },
    { header: "Total ₹", cell: (r) => rupeeFull(r.total_amount) },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => openPdf(`/api/sales/${r.id}/pdf`)}>PDF</button>
        <button className="text-accent" onClick={() => setEditing(r.id)}>Edit</button>
        <button className="text-danger" onClick={() => del(r.id)}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Order Forms" subtitle="Jai Laxmi Creation size-grid order forms"
        action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Order Form</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={bills} empty="No order forms yet" />}
      {open && <NewOrderForm onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
      {editing && <NewOrderForm billId={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />}
    </div>
  );
}

function NewOrderForm({ onClose, onSaved, billId }) {
  const { data: customers } = useFetch("/api/customers");
  const { data: products } = useFetch("/api/products");
  const { data: existing } = useFetch(billId ? `/api/sales/${billId}` : null, [billId]);
  const [customerId, setCustomerId] = useState("");
  const [billDate, setBillDate] = useState(new Date().toISOString().slice(0, 10));
  const [delivery, setDelivery] = useState("");
  const [transport, setTransport] = useState("");
  const [agent, setAgent] = useState("");
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (existing) {
      setCustomerId(String(existing.customer?.id || ""));
      setBillDate(existing.bill_date || new Date().toISOString().slice(0, 10));
      setDelivery(existing.delivery_date || "");
      setTransport(existing.transport || "");
      setAgent(existing.agent || "");
      setItems(existing.items.map((it) => ({ ...it })));
    }
  }, [existing]);

  // entry row
  const [pid, setPid] = useState("");
  const [sizes, setSizes] = useState({ qty_m: "", qty_l: "", qty_xl: "", qty_xxl: "", qty_mxxl: "" });

  const selProduct = products?.find((x) => String(x.id) === String(pid));

  // Per-size rate from the product, falling back to its base sale_rate.
  const sizeRate = (p, sizeKey) => {
    if (!p) return 0;
    const rk = sizeKey.replace("qty_", "rate_");
    return Number(p[rk]) > 0 ? Number(p[rk]) : Number(p.sale_rate) || 0;
  };
  const computeAmount = (p, s) =>
    SIZES.reduce((sum, [k]) => sum + (Number(s[k]) || 0) * sizeRate(p, k), 0);

  // Live amount for the row being entered
  const entryAmount = computeAmount(selProduct, sizes);

  const addItem = () => {
    const p = selProduct;
    if (!p) return setErr("Select a design/product");
    const s = Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));
    const rowQty = Object.values(s).reduce((a, b) => a + b, 0);
    if (rowQty <= 0) return setErr("Enter quantity for at least one size");
    const amount = computeAmount(p, s);
    setItems([...items, { design_no: p.name, product_id: p.id, ...s, row_qty: rowQty, amount }]);
    setPid(""); setSizes({ qty_m: "", qty_l: "", qty_xl: "", qty_xxl: "", qty_mxxl: "" }); setErr("");
  };

  const totalQty = items.reduce((a, b) => a + b.row_qty, 0);
  const totalAmt = items.reduce((a, b) => a + b.amount, 0);

  const save = async () => {
    if (!customerId) return setErr("Select a party");
    if (!items.length) return setErr("Add at least one design");
    setBusy(true); setErr("");
    const payload = {
      customer_id: Number(customerId), bill_date: billDate, delivery_date: delivery || null,
      transport, agent,
      items: items.map(({ design_no, product_id, qty_m, qty_l, qty_xl, qty_xxl, qty_mxxl }) =>
        ({ design_no, product_id, qty_m, qty_l, qty_xl, qty_xxl, qty_mxxl })),
    };
    try {
      const { data } = billId ? await api.put(`/api/sales/${billId}`, payload) : await api.post("/api/sales", payload);
      await openPdf(`/api/sales/${data.id}/pdf`);
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={billId ? "Edit Order Form" : "New Order Form"} wide>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Field label="Party (Customer)" required>
          <Select value={customerId} onChange={setCustomerId}>
            <option value="">— Select Party —</option>
            {customers?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Bill Date"><input type="date" className="input" value={billDate} onChange={(e) => setBillDate(e.target.value)} /></Field>
        <Field label="Delivery Date"><input type="date" className="input" value={delivery} onChange={(e) => setDelivery(e.target.value)} /></Field>
        <Field label="Transport"><input className="input" value={transport} onChange={(e) => setTransport(e.target.value)} placeholder="Transporter" /></Field>
        <Field label="Agent"><input className="input" value={agent} onChange={(e) => setAgent(e.target.value)} placeholder="Sales agent" /></Field>
      </div>

      <div className="mt-5 mb-2 text-xs font-bold uppercase tracking-wide text-muted">Add Design</div>
      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-separator bg-bg p-3">
        <div className="min-w-[160px] flex-1">
          <label className="label">Design / Product</label>
          <Select value={pid} onChange={setPid}>
            <option value="">— Select Design —</option>
            {products?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
        </div>
        {SIZES.map(([k, lbl]) => (
          <div key={k} className="w-16">
            <label className="label text-center">{lbl}</label>
            <input className="input px-1 text-center" inputMode="numeric" value={sizes[k]}
                   onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
            {selProduct && <div className="mt-0.5 text-center text-[10px] text-muted">₹{sizeRate(selProduct, k)}</div>}
          </div>
        ))}
        <div className="w-24">
          <label className="label">Amount</label>
          <div className="input flex items-center justify-end font-semibold text-ok">{rupeeFull(entryAmount)}</div>
        </div>
        <button className="btn-primary" onClick={addItem}>+ Add</button>
      </div>
      {pid && !selProduct?.rate_m && !selProduct?.sale_rate && (
        <p className="mt-1 text-xs text-warn">This design has no rates set. Add size rates in Products first.</p>
      )}

      {items.length > 0 && (
        <div className="mt-3 overflow-x-auto rounded-xl border border-separator">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b border-separator text-[11px] uppercase tracking-wide text-muted">
              <th className="px-3 py-2">Design</th>{SIZES.map(([k, l]) => <th key={k} className="px-2 py-2 text-center">{l}</th>)}
              <th className="px-2 text-center">Qty</th><th className="px-2 text-right">Amount</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i} className="border-b border-separator/60 last:border-0">
                  <td className="px-3 py-2 text-ink">{it.design_no}</td>
                  {SIZES.map(([k]) => <td key={k} className="px-2 text-center text-ink2">{it[k] || "—"}</td>)}
                  <td className="px-2 text-center font-semibold text-ink">{it.row_qty}</td>
                  <td className="px-2 text-right font-semibold text-ink">{rupeeFull(it.amount)}</td>
                  <td className="px-2 text-center"><button className="text-danger" onClick={() => setItems(items.filter((_, x) => x !== i))}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-3 text-right text-sm font-bold text-ink">
        Total Quantity: {totalQty} &nbsp; | &nbsp; Total: {rupeeFull(totalAmt)}
      </div>

      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-success" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save & Generate PDF"}</button>
      </div>
    </Modal>
  );
}
