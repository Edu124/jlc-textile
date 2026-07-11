import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError, openPdf, useAmountLock } from "../lib/useFetch.js";
import { isNetworkError, queueRequest } from "../lib/offline.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

const SIZES = [["qty_s", "S"], ["qty_m", "M"], ["qty_l", "L"], ["qty_xl", "XL"], ["qty_xxl", "XXL"], ["qty_xxxl", "3XL"], ["qty_xxxxl", "4XL"], ["qty_mxxl", "M-XXL"]];
const EMPTY_SIZES = { qty_s: "", qty_m: "", qty_l: "", qty_xl: "", qty_xxl: "", qty_xxxl: "", qty_xxxxl: "", qty_mxxl: "" };

export default function Sales() {
  const { data: bills, loading, reload } = useFetch("/api/sales");
  const { data: pending, reload: reloadPending } = useFetch("/api/sales/pending");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [delivering, setDelivering] = useState(null);

  const del = async (id) => {
    if (!confirm("Delete this order form?")) return;
    await api.delete(`/api/sales/${id}`); reload(); reloadPending();
  };

  const delFromPending = async (r) => {
    if (!confirm(`Remove order form ${r.ref}? This deletes the whole bill (all its designs), not just this one line.`)) return;
    await api.delete(`/api/sales/${r.bill_id}`); reload(); reloadPending();
  };

  const [customerFor, setCustomerFor] = useState(null);
  const [pdfFor, setPdfFor] = useState(null);
  const { unlocked, unlock } = useAmountLock();

  const columns = [
    { header: "Ref No.", cell: (r) => (
      <span className="font-medium text-ink">{r.reference_no || r.bill_number}</span>
    )},
    { header: "Date", key: "bill_date" },
    { header: "Party", cell: (r) => (
      <button className="text-accent hover:underline" onClick={() => setCustomerFor(r)}>{r.customer}</button>
    )},
    { header: "Designs", key: "designs" },
    { header: "Total Qty", cell: (r) => num(r.total_qty) },
    { header: "Total ₹", cell: (r) => (unlocked
      ? rupeeFull(r.total_amount)
      : <button className="tracking-widest text-muted hover:text-accent" title="Tap to unlock amounts" onClick={unlock}>***</button>) },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setPdfFor(r.id)}>PDF</button>
        <button className="text-accent" onClick={() => setDelivering(r)}>Delivery</button>
        <button className="text-accent" onClick={() => setEditing(r.id)}>Edit</button>
        <button className="text-danger" onClick={() => del(r.id)}>Delete</button>
      </div>
    )},
  ];

  const pendingColumns = [
    { header: "Ref No.", key: "ref" },
    { header: "Party", key: "customer" },
    { header: "Design", key: "design_no" },
    { header: "Size", key: "size" },
    { header: "Pending", cell: (r) => <span className="font-semibold text-warn">{num(r.pending, 0)}</span> },
    { header: "In Stock Now", cell: (r) => num(r.in_stock, 0) },
    { header: "Status", cell: (r) => (
      r.ready
        ? <span className="rounded px-2 py-0.5 text-xs font-semibold bg-okSoft text-ok">Ready to deliver</span>
        : r.in_stock > 0
        ? <span className="rounded px-2 py-0.5 text-xs font-semibold bg-warnSoft text-warn">Partial ({num(r.in_stock, 0)})</span>
        : <span className="rounded px-2 py-0.5 text-xs font-semibold bg-surface2 text-muted">Waiting stock</span>
    )},
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => {
          const bill = bills?.find((b) => b.id === r.bill_id);
          if (bill) setDelivering(bill);
        }}>Deliver</button>
        <button className="text-danger" onClick={() => delFromPending(r)}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Order Forms" subtitle="Tap Delivery on a bill, then a design, to mark how much is delivered. Tap a party name for their full history."
        action={<button className="btn-primary" onClick={() => setOpen(true)}>+ New Order Form</button>} />
      {loading ? <Spinner /> : <Table columns={columns} rows={bills} empty="No order forms yet" />}

      <div className="mt-8">
        <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">
          Pending Deliveries — waiting pieces per design &amp; size
        </h2>
        <Table columns={pendingColumns} rows={pending || []}
               empty="Nothing pending — every ordered piece is delivered." />
      </div>

      {open && <NewOrderForm onClose={() => setOpen(false)} onSaved={(id) => { setOpen(false); reload(); reloadPending(); setPdfFor(id); }} />}
      {editing && <NewOrderForm billId={editing} onClose={() => setEditing(null)} onSaved={(id) => { setEditing(null); reload(); reloadPending(); setPdfFor(id); }} />}
      {delivering && <DeliveryModal bill={delivering} onClose={() => { setDelivering(null); reloadPending(); }} />}
      {customerFor && <CustomerSummaryModal customerId={customerFor.customer_id} onClose={() => setCustomerFor(null)} />}
      {pdfFor && <PdfOptionsModal billId={pdfFor} onClose={() => setPdfFor(null)} />}
    </div>
  );
}

const PDF_OPTIONS = [
  ["ref", "Reference No.", "Print your reference as the bill's No.", true],
  ["delivery", "Delivery Date", "", true],
  ["transport", "Transport", "", true],
  ["agent", "Agent", "", true],
  ["amounts", "Amounts (₹) per design", "The bill never prints a money total — only total quantity.", false],
];

function PdfOptionsModal({ billId, onClose }) {
  const [opts, setOpts] = useState(Object.fromEntries(PDF_OPTIONS.map(([k, , , def]) => [k, def])));
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    const qs = PDF_OPTIONS.map(([k]) => `${k}=${opts[k] ? 1 : 0}`).join("&");
    try { await openPdf(`/api/sales/${billId}/pdf?${qs}`, `order-form-${billId}.pdf`); onClose(); }
    finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title="Generate PDF — what to include?">
      <div className="space-y-2">
        {PDF_OPTIONS.map(([k, label, hint]) => (
          <label key={k} className="flex cursor-pointer items-center gap-3 rounded-xl border border-separator bg-bg p-3">
            <input type="checkbox" className="h-5 w-5 accent-accent" checked={opts[k]}
                   onChange={(e) => setOpts({ ...opts, [k]: e.target.checked })} />
            <div>
              <div className="text-sm font-semibold text-ink">{label}</div>
              {hint && <div className="text-xs text-muted">{hint}</div>}
            </div>
          </label>
        ))}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={generate} disabled={busy}>{busy ? <Spinner /> : "Generate PDF"}</button>
      </div>
    </Modal>
  );
}

function CustomerSummaryModal({ customerId, onClose }) {
  const { data, loading } = useFetch(`/api/customers/${customerId}/summary`);

  return (
    <Modal open onClose={onClose} title={data ? `${data.customer} — Order History` : "Order History"} wide>
      {loading || !data ? <Spinner /> : !data.bills.length ? (
        <div className="rounded-lg bg-surface2 px-3 py-4 text-center text-sm text-muted">No order forms for this party yet</div>
      ) : (
        <div className="space-y-3">
          {data.bills.map((b) => (
            <div key={b.bill_id} className="rounded-xl border border-separator p-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-bold text-ink">{b.reference_no || b.bill_number}</span>
                  <span className="ml-2 text-xs text-muted">{b.bill_date}</span>
                </div>
                <span className={b.completed ? "rounded px-2 py-0.5 text-xs font-semibold bg-okSoft text-ok"
                                             : "rounded px-2 py-0.5 text-xs font-semibold bg-warnSoft text-warn"}>
                  {b.completed ? "Completed" : `${num(b.delivered_qty, 0)} / ${num(b.total_qty, 0)} delivered`}
                </span>
              </div>
              <div className="mt-2 space-y-1">
                {b.items.map((it, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-1.5 text-sm">
                    <span className="text-ink">{it.design_no || "Design"}</span>
                    <span className="text-ink2">{num(it.delivered, 0)} / {num(it.qty, 0)} pcs · {rupeeFull(it.amount)}</span>
                  </div>
                ))}
              </div>
              {b.delivery_refs.length > 0 && (
                <details className="mt-2 text-xs">
                  <summary className="cursor-pointer text-muted">Delivery references ({b.delivery_refs.length})</summary>
                  <div className="mt-1 space-y-1">
                    {b.delivery_refs.map((d, i) => (
                      <div key={i} className="flex items-center justify-between rounded bg-surface2 px-2 py-1">
                        <span className="text-ink">{d.reference_no || "—"} · {d.design_no}</span>
                        <span className="text-muted">{num(d.pieces, 0)} pcs · {d.date}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

const SIZE_NAME = { qty_s: "S", qty_m: "M", qty_l: "L", qty_xl: "XL", qty_xxl: "XXL", qty_xxxl: "3XL", qty_xxxxl: "4XL", qty_mxxl: "M-XXL" };

function DeliveryModal({ bill, onClose }) {
  const { data: order, loading, reload } = useFetch(bill.order_id ? `/api/orders/${bill.order_id}` : null, [bill.order_id]);
  const [designFor, setDesignFor] = useState(null);

  if (!bill.order_id) {
    return (
      <Modal open onClose={onClose} title={`Delivery — ${bill.bill_number}`}>
        <p className="text-sm text-muted">This bill has no delivery record yet. Re-save it from Edit to enable delivery tracking.</p>
        <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
      </Modal>
    );
  }

  return (
    <Modal open onClose={onClose} title={`Delivery — ${bill.bill_number}`} wide>
      <p className="mb-3 text-sm text-muted">Tap a design to mark how many of each size are delivered. Leftover adjusts automatically.</p>
      {loading || !order ? <Spinner /> : (
        <div className="space-y-2">
          {order.items.map((it) => {
            const totalDelivered = it.delivered_qty || 0;
            const done = totalDelivered >= it.quantity && it.quantity > 0;
            return (
              <button key={it.id} onClick={() => setDesignFor(it)}
                className="flex w-full items-center justify-between rounded-lg bg-surface2 px-3 py-2.5 text-left hover:bg-surface3">
                <div>
                  <div className="text-sm font-semibold text-ink">{it.design_no || it.product || "Design"}</div>
                  <div className="text-xs text-muted">
                    {SIZES.filter(([k]) => it[k] > 0).map(([k, l]) => `${l}:${it[k]}`).join("  ") || "—"}
                  </div>
                </div>
                <div className="text-right">
                  <div className={done ? "text-sm font-semibold text-ok" : "text-sm font-semibold text-ink"}>
                    {num(totalDelivered, 0)} / {num(it.quantity, 0)}
                  </div>
                  <div className="text-[11px] text-muted">delivered</div>
                </div>
              </button>
            );
          })}
        </div>
      )}
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
      {designFor && (
        <DesignDeliverModal orderId={bill.order_id} item={designFor}
          onClose={() => { setDesignFor(null); reload(); }}
          onSaved={reload} />
      )}
    </Modal>
  );
}

function DesignDeliverModal({ orderId, item, onClose, onSaved }) {
  const { data: allLogs, reload: reloadLogs } = useFetch(`/api/orders/${orderId}/deliveries`);
  const { data: order, reload: reloadOrder } = useFetch(`/api/orders/${orderId}`);
  // Live item (so delivered totals refresh after each log).
  const it = order?.items.find((x) => x.id === item.id) || item;
  const logs = (allLogs || []).filter((l) => l.order_item_id === item.id);

  const hasSizes = SIZES.some(([k]) => it[k] > 0);
  const [vals, setVals] = useState({ ...EMPTY_SIZES, flat: "" });
  const [dDate, setDDate] = useState(new Date().toISOString().slice(0, 10));
  const [dRef, setDRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const remainingSize = (k) => Math.max(0, (it[k] || 0) - (it[`delivered_${k.slice(4)}`] || 0));
  const remainingFlat = Math.max(0, (it.quantity || 0) - (it.delivered_qty || 0));

  const refresh = () => { reloadLogs(); reloadOrder(); onSaved?.(); };

  const save = async () => {
    setBusy(true); setErr("");
    const body = { delivery_date: dDate, reference_no: dRef.trim() };
    if (hasSizes) {
      let any = false;
      for (const [k] of SIZES) { const v = Number(vals[k]) || 0; body[k.slice(4)] = v; if (v > 0) any = true; }
      if (!any) { setBusy(false); return setErr("Enter pieces delivered now"); }
    } else {
      const v = Number(vals.flat) || 0;
      if (!(v > 0)) { setBusy(false); return setErr("Enter pieces delivered now"); }
      body.m = v; // single-bucket items use M slot as the plain count
    }
    try {
      await api.post(`/api/orders/${orderId}/items/${item.id}/deliver-log`, body);
      setVals({ ...EMPTY_SIZES, flat: "" });
      setDRef("");
      refresh();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  const removeLog = async (id) => {
    if (!confirm("Undo this delivery entry?")) return;
    await api.delete(`/api/orders/${orderId}/deliveries/${id}`); refresh();
  };

  const totalDelivered = it.delivered_qty || 0;
  const totalOrdered = it.quantity || 0;
  const sizeStr = (s) => SIZES.filter(([k]) => s[k.slice(4)] > 0).map(([k, l]) => `${l}:${num(s[k.slice(4)], 0)}`).join("  ") || `${num(s.m || 0, 0)}`;

  return (
    <Modal open onClose={onClose} title={`${it.design_no || it.product} — Delivery`} wide>
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-surface2 px-3 py-2 text-center">
          <div className="text-xl font-extrabold text-ink">{num(totalOrdered, 0)}</div>
          <div className="text-[11px] uppercase tracking-wide text-muted">Ordered</div>
        </div>
        <div className="rounded-xl bg-surface2 px-3 py-2 text-center">
          <div className="text-xl font-extrabold text-ok">{num(totalDelivered, 0)}</div>
          <div className="text-[11px] uppercase tracking-wide text-muted">Delivered</div>
        </div>
        <div className="rounded-xl bg-surface2 px-3 py-2 text-center">
          <div className="text-xl font-extrabold text-warn">{num(totalOrdered - totalDelivered, 0)}</div>
          <div className="text-[11px] uppercase tracking-wide text-muted">Pending</div>
        </div>
      </div>

      {/* Add a dated delivery */}
      <div className="mt-4 rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Deliver Now</div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-32"><label className="label">Date</label>
            <input type="date" className="input" value={dDate} onChange={(e) => setDDate(e.target.value)} /></div>
          <div className="w-32"><label className="label">Reference No.</label>
            <input className="input" value={dRef} placeholder="optional"
                   onChange={(e) => setDRef(e.target.value)} /></div>
          {hasSizes ? SIZES.filter(([k]) => it[k] > 0).map(([k, lbl]) => (
            <div key={k} className="w-16 text-center">
              <div className="label">{lbl} <span className="text-muted">·{remainingSize(k)}</span></div>
              <input className="input px-1 text-center" inputMode="numeric" value={vals[k]}
                     onChange={(e) => setVals({ ...vals, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
              <button type="button" className="mt-0.5 block w-full text-[11px] text-accent hover:underline"
                      onClick={() => setVals({ ...vals, [k]: remainingSize(k) })}>all</button>
            </div>
          )) : (
            <div className="w-24"><label className="label">Pieces <span className="text-muted">·{remainingFlat} left</span></label>
              <input className="input text-center" inputMode="numeric" value={vals.flat}
                     onChange={(e) => setVals({ ...vals, flat: e.target.value.replace(/[^0-9]/g, "") })} /></div>
          )}
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "+ Add"}</button>
        </div>
        {err && <div className="mt-2 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      </div>

      {/* Dated log */}
      <div className="mt-4">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Delivery Log</div>
        {!logs.length ? (
          <div className="rounded-lg bg-surface2 px-3 py-4 text-center text-sm text-muted">Nothing delivered yet</div>
        ) : (
          <div className="space-y-1">
            {logs.map((l) => (
              <div key={l.id} className="flex items-center gap-3 rounded-lg bg-surface2 px-3 py-2 text-sm">
                <span className="font-semibold text-ink">{num(l.pieces, 0)} pcs</span>
                <span className="text-xs text-muted">{sizeStr(l.sizes)}</span>
                {l.reference_no && <span className="rounded bg-bg px-1.5 py-0.5 text-xs text-accent">Ref: {l.reference_no}</span>}
                <span className="ml-auto text-xs text-muted">{l.date}</span>
                <button className="text-danger" onClick={() => removeLog(l.id)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

function NewOrderForm({ onClose, onSaved, billId }) {
  const { data: customers } = useFetch("/api/customers");
  const { data: products } = useFetch("/api/products");
  const { data: existing } = useFetch(billId ? `/api/sales/${billId}` : null, [billId]);
  const { data: availability } = useFetch("/api/finished-goods/availability");
  const [customerId, setCustomerId] = useState("");
  const [billDate, setBillDate] = useState(new Date().toISOString().slice(0, 10));
  const [delivery, setDelivery] = useState("");
  const [reference, setReference] = useState("");
  const [transport, setTransport] = useState("");
  const [agent, setAgent] = useState("");
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const { unlocked, unlock } = useAmountLock();
  const masked = (v) => (unlocked ? rupeeFull(v)
    : <button type="button" className="tracking-widest text-muted hover:text-accent" title="Tap to unlock amounts" onClick={unlock}>***</button>);

  useEffect(() => {
    if (existing) {
      setCustomerId(String(existing.customer?.id || ""));
      setBillDate(existing.bill_date || new Date().toISOString().slice(0, 10));
      setDelivery(existing.delivery_date || "");
      setReference(existing.reference_no || "");
      setTransport(existing.transport || "");
      setAgent(existing.agent || "");
      setItems(existing.items.map((it) => ({ ...it })));
    }
  }, [existing]);

  // entry row
  const [pid, setPid] = useState("");
  const [sizes, setSizes] = useState({ ...EMPTY_SIZES });

  const selProduct = products?.find((x) => String(x.id) === String(pid));
  // Available stock per size for the selected design (by name).
  const selAvail = selProduct && availability
    ? availability.find((a) => a.name.trim().toLowerCase() === selProduct.name.trim().toLowerCase())
    : null;
  // Once a design is picked, always show stock (0 when the design has none yet).
  const availFor = (qtyKey) => selProduct ? (selAvail ? (selAvail.available[qtyKey.replace("qty_", "")] || 0) : 0) : null;

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

    // Warn when any size is being ordered beyond what's in stock.
    const exceeded = SIZES.filter(([k]) => {
      const avail = availFor(k);
      return avail !== null && s[k] > avail;
    });
    if (exceeded.length) {
      const detail = exceeded
        .map(([k, lbl]) => `${lbl}: in stock ${num(availFor(k), 0)}, you entered ${num(s[k], 0)}`)
        .join("\n");
      const ok = confirm(
        `⚠ Not enough stock for ${p.name}:\n\n${detail}\n\nDo you still want to add it? (The extra pieces will need to be produced.)`
      );
      if (!ok) return;
    }

    const amount = computeAmount(p, s);
    setItems([...items, { design_no: p.name, product_id: p.id, ...s, row_qty: rowQty, amount }]);
    setPid(""); setSizes({ ...EMPTY_SIZES }); setErr("");
  };

  const totalQty = items.reduce((a, b) => a + b.row_qty, 0);
  const totalAmt = items.reduce((a, b) => a + b.amount, 0);

  const save = async () => {
    if (!customerId) return setErr("Select a party");
    if (!items.length) return setErr("Add at least one design");
    setBusy(true); setErr("");
    const payload = {
      customer_id: Number(customerId), bill_date: billDate, delivery_date: delivery || null,
      reference_no: reference, transport, agent,
      items: items.map((it) => ({
        design_no: it.design_no, product_id: it.product_id,
        ...Object.fromEntries(SIZES.map(([k]) => [k, it[k] || 0])),
      })),
    };
    try {
      const { data } = billId ? await api.put(`/api/sales/${billId}`, payload) : await api.post("/api/sales", payload);
      onSaved(data.id);   // parent opens the PDF-options popup
    } catch (e) {
      // No internet: queue the new order form and sync it later. (Edits of
      // existing forms still need a connection.)
      if (!billId && isNetworkError(e) &&
          queueRequest({ method: "post", url: "/api/sales", body: payload, label: "Order form" })) {
        alert("No internet — the order form is saved on this device and will sync automatically when the connection returns. (PDF can be printed after it syncs.)");
        onClose();
      } else setErr(apiError(e));
    } finally { setBusy(false); }
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
        <Field label="Reference No. (optional)"><input className="input" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="e.g. PO-1234" /></Field>
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
        {SIZES.map(([k, lbl]) => {
          const avail = availFor(k);
          const short = avail !== null && (Number(sizes[k]) || 0) > avail;
          return (
            <div key={k} className="w-16">
              <label className="label text-center">{lbl}</label>
              <input className={`input px-1 text-center ${short ? "border-danger" : ""}`} inputMode="numeric" value={sizes[k]}
                     onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
              {selProduct && <div className="mt-0.5 text-center text-[10px] text-muted">₹{sizeRate(selProduct, k)}</div>}
              {avail !== null && (
                <div className={`text-center text-[10px] ${short ? "text-danger" : "text-ok"}`}>stk {num(avail, 0)}</div>
              )}
            </div>
          );
        })}
        <div className="w-24">
          <label className="label">Amount</label>
          <div className="input flex items-center justify-end font-semibold text-ok">{masked(entryAmount)}</div>
        </div>
        <button className="btn-primary" onClick={addItem}>+ Add</button>
      </div>
      {selProduct && (
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted">In stock:</span>
          {SIZES.map(([k, lbl]) => {
            const v = availFor(k) ?? 0;
            return <span key={k} className={`rounded px-1.5 py-0.5 ${v > 0 ? "bg-okSoft text-ok" : "bg-surface2 text-muted"}`}>{lbl} {num(v, 0)}</span>;
          })}
          {!selAvail && <span className="text-muted">— no finished-goods stock recorded for this design yet</span>}
        </div>
      )}
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
                  <td className="px-2 text-right font-semibold text-ink">{masked(it.amount)}</td>
                  <td className="px-2 text-center"><button className="text-danger" onClick={() => setItems(items.filter((_, x) => x !== i))}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-3 text-right text-sm font-bold text-ink">
        Total Quantity: {totalQty} &nbsp; | &nbsp; Total: {masked(totalAmt)}
      </div>

      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-success" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save & Generate PDF"}</button>
      </div>
    </Modal>
  );
}
