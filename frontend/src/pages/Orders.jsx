import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

const SIZES = [["qty_m", "M"], ["qty_l", "L"], ["qty_xl", "XL"], ["qty_xxl", "XXL"], ["qty_mxxl", "M-XXL"]];

export default function Orders() {
  const { data: orders, loading, reload } = useFetch("/api/orders");
  const [open, setOpen] = useState(false);
  const [delivering, setDelivering] = useState(null);

  const columns = [
    { header: "Order #", key: "order_number" },
    { header: "Customer", key: "customer" },
    { header: "Items", key: "items" },
    { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
    { header: "Delivered", cell: (r) => (
      <span className={r.delivered_qty >= r.total_qty && r.total_qty > 0 ? "text-ok font-semibold" : "text-ink2"}>
        {r.delivered_qty} / {r.total_qty}
      </span>
    )},
    { header: "Delivery", cell: (r) => r.delivery_date || "—" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setDelivering(r.id)}>Deliver</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Orders" action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Order</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={orders} empty="No orders yet" />}
      {open && <OrderForm onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />}
      {delivering && <DeliverModal orderId={delivering} onClose={() => setDelivering(null)} onSaved={() => { setDelivering(null); reload(); }} />}
    </div>
  );
}

function DeliverModal({ orderId, onClose, onSaved }) {
  const { data: order, reload } = useFetch(`/api/orders/${orderId}`);
  const [qtys, setQtys] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const sizeKey = (itemId, size) => `${itemId}_${size}`;

  useEffect(() => {
    if (!order) return;
    const next = {};
    for (const it of order.items) {
      if (it.has_sizes) {
        for (const [k] of SIZES) next[sizeKey(it.id, k)] = it[`delivered_${k.slice(4)}`];
      } else {
        next[it.id] = it.delivered_qty;
      }
    }
    setQtys(next);
  }, [order]);

  const save = async () => {
    setBusy(true); setErr("");
    try {
      for (const it of order.items) {
        if (it.has_sizes) {
          const body = {};
          let changed = false;
          for (const [k] of SIZES) {
            const size = k.slice(4);
            const v = Number(qtys[sizeKey(it.id, k)]) || 0;
            if (v !== it[`delivered_${size}`]) changed = true;
            body[`delivered_${size}`] = v;
          }
          if (changed) await api.put(`/api/orders/${orderId}/items/${it.id}/deliver`, body);
        } else {
          const v = Number(qtys[it.id]) || 0;
          if (v !== it.delivered_qty) {
            await api.put(`/api/orders/${orderId}/items/${it.id}/deliver`, { delivered_qty: v });
          }
        }
      }
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  if (!order) return null;

  return (
    <Modal open onClose={onClose} title={`Mark Delivered — ${order.order_number}`} wide>
      <p className="mb-3 text-sm text-muted">
        Enter how much has been delivered so far — by size where applicable. Click "Left" to fill in the remaining quantity at once.
      </p>
      <div className="space-y-3">
        {order.items.map((it) => (
          <div key={it.id} className="rounded-lg bg-surface2 px-3 py-2">
            <div className="mb-1 text-sm font-semibold text-ink">{it.product}</div>
            {it.has_sizes ? (
              <div className="flex flex-wrap gap-3">
                {SIZES.filter(([k]) => it[`qty_${k.slice(4)}`] > 0).map(([k, lbl]) => {
                  const size = k.slice(4);
                  const ordered = it[`qty_${size}`] || 0;
                  const entered = Number(qtys[sizeKey(it.id, k)]) || 0;
                  const left = Math.max(0, ordered - entered);
                  return (
                    <div key={k} className="text-center">
                      <div className="label">{lbl}</div>
                      <input className="input w-16 text-center" inputMode="numeric"
                             value={qtys[sizeKey(it.id, k)] ?? ""}
                             onChange={(e) => setQtys({ ...qtys, [sizeKey(it.id, k)]: e.target.value.replace(/[^0-9.]/g, "") })} />
                      <button type="button" className="mt-0.5 block w-full text-[11px] text-accent hover:underline"
                              onClick={() => setQtys({ ...qtys, [sizeKey(it.id, k)]: ordered })}
                              title="Click to mark all remaining as delivered">
                        Left: {left}
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <input className="input w-20 text-center" inputMode="numeric"
                       value={qtys[it.id] ?? ""}
                       onChange={(e) => setQtys({ ...qtys, [it.id]: e.target.value.replace(/[^0-9.]/g, "") })} />
                <span className="text-xs text-muted">/ {it.quantity}</span>
                <button type="button" className="text-[11px] text-accent hover:underline"
                        onClick={() => setQtys({ ...qtys, [it.id]: it.quantity })}
                        title="Click to mark all remaining as delivered">
                  Left: {Math.max(0, it.quantity - (Number(qtys[it.id]) || 0))}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
      </div>
    </Modal>
  );
}

function OrderForm({ orderId, onClose, onSaved }) {
  const { data: customers } = useFetch("/api/customers");
  const { data: products } = useFetch("/api/products");
  const { data: existing } = useFetch(orderId ? `/api/orders/${orderId}` : null, [orderId]);
  const [customerId, setCustomerId] = useState("");
  const [delivery, setDelivery] = useState("");
  const [items, setItems] = useState([]);
  const [pid, setPid] = useState(""); const [qty, setQty] = useState(""); const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const locked = existing && existing.items.some((it) => (it.delivered_qty || 0) > 0);

  useEffect(() => {
    if (existing) {
      setCustomerId(String(existing.customer_id || ""));
      setDelivery(existing.delivery_date || "");
      setItems(existing.items.map((it) => ({ product_id: it.product_id, name: it.product, quantity: it.quantity, rate: it.rate })));
    }
  }, [existing]);

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
    const payload = { customer_id: Number(customerId), delivery_date: delivery || null,
      items: items.map(({ product_id, quantity, rate }) => ({ product_id, quantity, rate })) };
    try {
      if (orderId) await api.put(`/api/orders/${orderId}`, payload);
      else await api.post("/api/orders", payload);
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={orderId ? "Edit Order" : "New Order"} wide>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Customer" required>
          <Select value={customerId} onChange={setCustomerId}>
            <option value="">— Select Customer —</option>
            {customers?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Delivery Date"><input type="date" className="input" value={delivery} onChange={(e) => setDelivery(e.target.value)} /></Field>
      </div>

      {locked && (
        <p className="mt-3 rounded-lg bg-warnSoft px-3 py-2 text-xs text-warn">
          Some items already have deliveries recorded — items are locked, only customer/delivery date can be edited. Use "Deliver" to adjust quantities.
        </p>
      )}

      {!locked && (
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
      )}

      {items.length > 0 && (
        <div className="mt-3 space-y-1">
          {items.map((it, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2 text-sm">
              <span className="text-ink">{it.name}</span>
              <span className="text-ink2">{it.quantity} × {rupeeFull(it.rate)} = {rupeeFull(it.quantity * it.rate)}</span>
              {!locked && <button className="text-danger" onClick={() => setItems(items.filter((_, x) => x !== i))}>✕</button>}
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
