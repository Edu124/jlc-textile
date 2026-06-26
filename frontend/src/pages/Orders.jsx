import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Badge, Spinner } from "../components/ui.jsx";

const STATUSES = ["Received", "In Production", "Ready", "Dispatched", "Delivered", "Cancelled"];

export default function Orders() {
  const { data: orders, loading, reload } = useFetch("/api/orders");
  const [open, setOpen] = useState(false);
  const [statusFor, setStatusFor] = useState(null);

  const columns = [
    { header: "Order #", key: "order_number" },
    { header: "Customer", key: "customer" },
    { header: "Items", key: "items" },
    { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
    { header: "Status", cell: (r) => <Badge status={r.status} /> },
    { header: "Delivery", cell: (r) => r.delivery_date || "—" },
    { header: "Actions", cell: (r) => (
      <button className="text-accent" onClick={() => setStatusFor(r)}>Update Status</button>
    )},
  ];

  return (
    <div>
      <PageHeader title="Orders" action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Order</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={orders} empty="No orders yet" />}
      {open && <NewOrder onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
      {statusFor && <StatusModal order={statusFor} onClose={() => setStatusFor(null)} onSaved={() => { setStatusFor(null); reload(); }} />}
    </div>
  );
}

function StatusModal({ order, onClose, onSaved }) {
  const [status, setStatus] = useState(order.status);
  const save = async () => { await api.put(`/api/orders/${order.id}/status`, { status }); onSaved(); };
  return (
    <Modal open onClose={onClose} title={`Order ${order.order_number}`}>
      <Field label="Status"><Select value={status} onChange={setStatus}>
        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
      </Select></Field>
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={save}>Save</button>
      </div>
    </Modal>
  );
}

function NewOrder({ onClose, onSaved }) {
  const { data: customers } = useFetch("/api/customers");
  const { data: products } = useFetch("/api/products");
  const [customerId, setCustomerId] = useState("");
  const [delivery, setDelivery] = useState("");
  const [items, setItems] = useState([]);
  const [pid, setPid] = useState(""); const [qty, setQty] = useState(""); const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  useEffect(() => {
    if (pid && products) { const p = products.find((x) => String(x.id) === String(pid)); if (p) setRate(String(p.sale_rate || "")); }
  }, [pid, products]);

  const add = () => {
    const p = products?.find((x) => String(x.id) === String(pid));
    if (!p) return setErr("Select a product");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setItems([...items, { product_id: p.id, name: p.name, quantity: Number(qty), rate: Number(rate) || 0 }]);
    setPid(""); setQty(""); setRate(""); setErr("");
  };
  const total = items.reduce((a, b) => a + b.quantity * b.rate, 0);

  const save = async () => {
    if (!customerId) return setErr("Select a customer");
    if (!items.length) return setErr("Add at least one product");
    setBusy(true); setErr("");
    try {
      await api.post("/api/orders", { customer_id: Number(customerId), delivery_date: delivery || null,
        items: items.map(({ product_id, quantity, rate }) => ({ product_id, quantity, rate })) });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title="New Order" wide>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Customer" required>
          <Select value={customerId} onChange={setCustomerId}>
            <option value="">— Select Customer —</option>
            {customers?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Delivery Date"><input type="date" className="input" value={delivery} onChange={(e) => setDelivery(e.target.value)} /></Field>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2 rounded-xl border border-separator bg-bg p-3">
        <div className="min-w-[160px] flex-1">
          <label className="label">Product</label>
          <Select value={pid} onChange={setPid}>
            <option value="">— Select —</option>
            {products?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
        </div>
        <div className="w-24"><label className="label">Qty</label><input className="input" inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
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
          <div className="pt-1 text-right font-bold text-ink">Total: {rupeeFull(total)}</div>
        </div>
      )}

      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-success" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save Order"}</button>
      </div>
    </Modal>
  );
}
