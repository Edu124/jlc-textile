import { useState, useEffect } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Badge, Spinner, StatCard, EmptyState } from "../components/ui.jsx";

export default function RawMaterials() {
  const { data: rows, loading, reload } = useFetch("/api/raw-materials");
  const [addOpen, setAddOpen] = useState(false);
  const [distFor, setDistFor] = useState(null);

  const total = rows?.length || 0;
  const value = (rows || []).reduce((a, b) => a + b.value, 0);
  const low = (rows || []).filter((r) => r.status === "Low Stock").length;

  const del = async (r) => {
    if (!confirm(`Remove "${r.name}" completely? Its stock, history and tailor jobs will all be deleted.`)) return;
    try { await api.delete(`/api/raw-materials/${r.id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "Name", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setDistFor(r)}>{r.name}</button>
    )},
    { header: "Number", cell: (r) => r.design_no || "—" },
    { header: "Unit", key: "unit" },
    { header: "In Stock", cell: (r) => num(r.quantity, 2) },
    { header: "Description", cell: (r) => r.description || "—" },
    { header: "Status", cell: (r) => <Badge status={r.status} /> },
    { header: "Actions", cell: (r) => (
      <button className="text-danger" onClick={() => del(r)}>Delete</button>
    )},
  ];

  return (
    <div>
      <PageHeader title="Raw Materials" subtitle="Add stock here — give it to tailors from Production → Assign. Tap a name to see where it was given."
        action={<button className="btn-primary" onClick={() => setAddOpen(true)}>+ Add Stock</button>} />
      <div className="mb-4 grid grid-cols-2 gap-4">
        <StatCard label="Materials" value={total} icon="◈" />
        <StatCard label="Low Stock" value={low} icon="⚠" accent="#D9685F" />
      </div>
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No materials yet" />}
      {addOpen && <AddStock onClose={() => setAddOpen(false)} onSaved={() => { setAddOpen(false); reload(); }} />}
      {distFor && <DistributionModal row={distFor} onClose={() => setDistFor(null)} />}
    </div>
  );
}

function AddStock({ onClose, onSaved }) {
  const { data: units } = useFetch("/api/units");
  const [name, setName] = useState("");
  const [designNo, setDesignNo] = useState("");
  const [qty, setQty] = useState("");
  const [unitId, setUnitId] = useState("");
  const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  // Default the unit to Metres once units load.
  useEffect(() => {
    if (units && !unitId) {
      const metres = units.find((u) => /met|mtr/i.test(u.name) || /^m$/i.test(u.abbreviation));
      if (metres) setUnitId(String(metres.id));
    }
  }, [units]);

  const save = async () => {
    if (!name.trim()) return setErr("Enter the design name");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setBusy(true); setErr("");
    try {
      await api.post("/api/raw-materials/stock-entry", {
        name: name.trim(), design_no: designNo.trim(),
        unit_id: unitId ? Number(unitId) : null,
        quantity: Number(qty), rate: 0, description: rate.trim() });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title="Add Stock">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Name" required>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Cotton Blue" />
          </Field>
          <Field label="Number">
            <input className="input" value={designNo} onChange={(e) => setDesignNo(e.target.value)} placeholder="e.g. D-204" />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantity" required>
            <input className="input" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
          </Field>
          <Field label="Unit" required>
            <Select value={unitId} onChange={setUnitId}>
              <option value="">— Unit —</option>
              {units?.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </Select>
          </Field>
        </div>
        <Field label="Description (optional)">
          <textarea className="input" rows={2} value={rate} onChange={(e) => setRate(e.target.value)} placeholder="anything extra about this design" />
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Add"}</button></div>
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
