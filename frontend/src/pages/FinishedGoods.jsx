import { useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Spinner, StatCard } from "../components/ui.jsx";

const SIZES = [["m", "M"], ["l", "L"], ["xl", "XL"], ["xxl", "XXL"], ["mxxl", "M-XXL"]];

export default function FinishedGoods() {
  const { data: rows, loading, reload } = useFetch("/api/finished-goods");
  const [adjustFor, setAdjustFor] = useState(null);
  const [editFor, setEditFor] = useState(null);
  const [detailFor, setDetailFor] = useState(null);
  const [directOpen, setDirectOpen] = useState(false);

  const totalQty = (rows || []).reduce((a, b) => a + b.quantity, 0);
  const value = (rows || []).reduce((a, b) => a + b.value, 0);

  const del = async (r) => {
    if (!confirm(`Remove "${r.name}" from finished goods?`)) return;
    try { await api.delete(`/api/finished-goods/${r.product_id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "", cell: (r) => (r.image
        ? <img src={r.image} alt="" className="h-10 w-10 rounded-lg object-cover" />
        : <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface2 text-muted">◼</div>) },
    { header: "Item", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setDetailFor(r)}>{r.name}</button>
    )},
    { header: "Unit", key: "unit" },
    { header: "In Stock", cell: (r) => num(r.quantity, 2) },
    { header: "Sale Rate", cell: (r) => rupeeFull(r.sale_rate) },
    { header: "Value", cell: (r) => rupeeFull(r.value) },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setEditFor(r)}>Edit</button>
        <button className="text-accent" onClick={() => setAdjustFor(r)}>Adjust</button>
        <button className="text-danger" onClick={() => del(r)}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Finished Goods" subtitle="Ready to sell. Pieces from final tailors land here automatically — add a photo and rename as needed."
        action={<button className="btn-primary" onClick={() => setDirectOpen(true)}>+ Direct Entry</button>} />
      <div className="mb-4 grid grid-cols-3 gap-4">
        <StatCard label="Items" value={rows?.length || 0} icon="◼" />
        <StatCard label="Total Qty" value={num(totalQty)} icon="◉" accent="#7FA8B8" />
        <StatCard label="Stock Value" value={rupeeFull(value)} icon="₹" accent="#5FB07C" />
      </div>
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No finished goods yet" />}
      {adjustFor && <Adjust row={adjustFor} onClose={() => setAdjustFor(null)} onSaved={() => { setAdjustFor(null); reload(); }} />}
      {editFor && <EditGood row={editFor} onClose={() => setEditFor(null)} onSaved={() => { setEditFor(null); reload(); }} />}
      {detailFor && <DetailModal row={detailFor} onClose={() => setDetailFor(null)} />}
      {directOpen && <DirectEntry onClose={() => setDirectOpen(false)} onSaved={() => { setDirectOpen(false); reload(); }} />}
    </div>
  );
}

function DirectEntry({ onClose, onSaved }) {
  const [name, setName] = useState("");
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [pieces, setPieces] = useState("");
  const [rate, setRate] = useState("");
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const sizeTotal = SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImage(reader.result);
    reader.readAsDataURL(file);
  };

  const save = async () => {
    if (!name.trim()) return setErr("Enter the design name");
    const total = sizeTotal > 0 ? sizeTotal : (Number(pieces) || 0);
    if (!(total > 0)) return setErr("Enter pieces");
    setBusy(true); setErr("");
    try {
      await api.post("/api/finished-goods/direct", {
        name: name.trim(),
        m: Number(sizes.m) || 0, l: Number(sizes.l) || 0, xl: Number(sizes.xl) || 0,
        xxl: Number(sizes.xxl) || 0, mxxl: Number(sizes.mxxl) || 0,
        pieces: Number(pieces) || 0,
        sale_rate: Number(rate) || 0, image_base64: image });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title="Direct Entry — Finished Goods">
      <div className="space-y-3">
        <Field label="Design Name" required>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. D-204" />
        </Field>
        <div>
          <label className="label">Pieces per size (or use total below)</label>
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
        <div className="grid grid-cols-2 gap-3">
          <Field label="Total pieces">
            <input className="input" inputMode="numeric" value={sizeTotal > 0 ? sizeTotal : pieces}
                   disabled={sizeTotal > 0}
                   onChange={(e) => setPieces(e.target.value.replace(/[^0-9]/g, ""))} />
          </Field>
          <Field label="Sale rate (optional)">
            <input className="input" inputMode="decimal" value={rate}
                   onChange={(e) => setRate(e.target.value.replace(/[^0-9.]/g, ""))} />
          </Field>
        </div>
        <Field label="Photo">
          <div className="flex items-center gap-3">
            {image && <img src={image} alt="" className="h-16 w-16 rounded-lg border border-separator object-cover" />}
            <input type="file" accept="image/*" onChange={onFile} className="hidden" id="direct-photo" />
            <label htmlFor="direct-photo" className="btn-ghost cursor-pointer">{image ? "Change photo" : "📷 Add photo"}</label>
          </div>
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Add to Stock"}</button>
        </div>
      </div>
    </Modal>
  );
}

function DetailModal({ row, onClose }) {
  const { data, loading } = useFetch(`/api/finished-goods/${row.product_id}/detail`);
  const sizeStr = (s) => SIZES.filter(([k]) => s[k] > 0).map(([k, l]) => `${l}:${num(s[k], 0)}`).join("  ") || "—";

  return (
    <Modal open onClose={onClose} title={`${row.name} — Production Detail`} wide>
      {loading || !data ? <Spinner /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-ok">{num(data.received_total, 0)}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Received</div>
            </div>
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-warn">{num(data.pending_total, 0)}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Pending</div>
            </div>
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-ink">{num(data.in_stock, 0)}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">In Stock</div>
            </div>
          </div>

          <div>
            <div className="mb-1 text-xs font-bold uppercase tracking-wide text-muted">Sizes Received</div>
            <div className="rounded-lg bg-surface2 px-3 py-2 text-sm text-ink">{sizeStr(data.sizes_received)}</div>
          </div>

          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">By Final Tailor</div>
            {!data.by_tailor.length ? (
              <div className="rounded-lg bg-surface2 px-3 py-4 text-center text-sm text-muted">
                No final-tailor jobs for this design yet.
              </div>
            ) : (
              <div className="space-y-3">
                {data.by_tailor.map((t) => (
                  <div key={t.job_id} className="rounded-xl border border-separator p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-ink">{t.tailor}</div>
                      <div className="text-sm">
                        <span className="text-ok font-semibold">{num(t.received, 0)}</span>
                        <span className="text-muted"> received · </span>
                        <span className="text-warn font-semibold">{num(t.pending, 0)}</span>
                        <span className="text-muted"> pending / {num(t.assigned, 0)} assigned</span>
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-muted">Sizes: {sizeStr(t.sizes)}</div>
                    {t.deliveries.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {t.deliveries.map((d, i) => (
                          <div key={i} className="flex items-center gap-2 rounded-lg bg-surface2 px-2 py-1.5 text-xs">
                            {d.image && <img src={d.image} alt="" className="h-8 w-8 rounded object-cover" />}
                            <span className="font-semibold text-ink">{num(d.pieces, 0)} pcs</span>
                            <span className="text-muted">{sizeStr(d.sizes)}</span>
                            <span className="ml-auto text-muted">{d.date}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

function EditGood({ row, onClose, onSaved }) {
  const [name, setName] = useState(row.name || "");
  const [rate, setRate] = useState(String(row.sale_rate || ""));
  const [rates, setRates] = useState({
    m: String(row.rate_m || ""), l: String(row.rate_l || ""), xl: String(row.rate_xl || ""),
    xxl: String(row.rate_xxl || ""), mxxl: String(row.rate_mxxl || ""),
  });
  const [image, setImage] = useState(row.image || null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImage(reader.result);
    reader.readAsDataURL(file);
  };

  const save = async () => {
    if (!name.trim()) return setErr("Enter a name");
    setBusy(true); setErr("");
    try {
      await api.put(`/api/finished-goods/${row.product_id}`, {
        name: name.trim(), sale_rate: Number(rate) || 0,
        rate_m: Number(rates.m) || 0, rate_l: Number(rates.l) || 0,
        rate_xl: Number(rates.xl) || 0, rate_xxl: Number(rates.xxl) || 0,
        rate_mxxl: Number(rates.mxxl) || 0,
        image_base64: image || "" });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Edit — ${row.name}`}>
      <div className="space-y-3">
        <Field label="Name" required>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Base Rate (used when a size has no rate)">
          <input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} />
        </Field>
        <div>
          <label className="label">Rate per size (₹)</label>
          <div className="flex flex-wrap gap-2">
            {SIZES.map(([k, lbl]) => (
              <div key={k} className="w-16 text-center">
                <div className="text-[11px] text-muted">{lbl}</div>
                <input className="input px-1 text-center" inputMode="decimal" value={rates[k]}
                       onChange={(e) => setRates({ ...rates, [k]: e.target.value })} />
              </div>
            ))}
          </div>
        </div>
        <Field label="Photo">
          <div className="flex items-center gap-3">
            {image && <img src={image} alt="" className="h-16 w-16 rounded-lg border border-separator object-cover" />}
            <input type="file" accept="image/*" onChange={onFile} className="hidden" id={`fg-photo-${row.product_id}`} />
            <label htmlFor={`fg-photo-${row.product_id}`} className="btn-ghost cursor-pointer">{image ? "Change photo" : "📷 Add photo"}</label>
            {image && <button className="text-danger text-sm" onClick={() => setImage(null)}>Remove</button>}
          </div>
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button></div>
      </div>
    </Modal>
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
