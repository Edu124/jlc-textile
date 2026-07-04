import { useState, useEffect } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Badge, Spinner, StatCard, EmptyState } from "../components/ui.jsx";

const REASONS = ["Given to tailor", "Given to customer", "Other"];
const NAME_LABEL = { "Given to tailor": "Tailor name", "Given to customer": "Customer name", "Other": "Name / note" };

export default function RawMaterials() {
  const { data: rows, loading, reload } = useFetch("/api/raw-materials");
  const [addOpen, setAddOpen] = useState(false);
  const [adjustFor, setAdjustFor] = useState(null);
  const [distFor, setDistFor] = useState(null);

  const total = rows?.length || 0;
  const value = (rows || []).reduce((a, b) => a + b.value, 0);
  const low = (rows || []).filter((r) => r.status === "Low Stock").length;

  const del = async (r) => {
    if (!confirm(`Remove "${r.name}" from stock entirely?`)) return;
    try { await api.delete(`/api/raw-materials/${r.id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const columns = [
    { header: "Material", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setDistFor(r)}>{r.name}</button>
    )},
    { header: "Unit", key: "unit" },
    { header: "In Stock", cell: (r) => num(r.quantity, 2) },
    { header: "Avg Rate", cell: (r) => rupeeFull(r.avg_rate) },
    { header: "Value", cell: (r) => rupeeFull(r.value) },
    { header: "Status", cell: (r) => <Badge status={r.status} /> },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setAdjustFor(r)}>Adjust</button>
        <button className="text-danger" onClick={() => del(r)}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Raw Materials" subtitle="Tap a material name to see where it was given"
        action={<button className="btn-primary" onClick={() => setAddOpen(true)}>+ Add Stock</button>} />
      <div className="mb-4 grid grid-cols-3 gap-4">
        <StatCard label="Materials" value={total} icon="◈" />
        <StatCard label="Stock Value" value={rupeeFull(value)} icon="₹" accent="#5FB07C" />
        <StatCard label="Low Stock" value={low} icon="⚠" accent="#D9685F" />
      </div>
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="No materials yet" />}
      {addOpen && <AddStock onClose={() => setAddOpen(false)} onSaved={() => { setAddOpen(false); reload(); }} />}
      {adjustFor && <Adjust row={adjustFor} onClose={() => setAdjustFor(null)} onSaved={() => { setAdjustFor(null); reload(); }} />}
      {distFor && <DistributionModal row={distFor} onClose={() => setDistFor(null)} />}
    </div>
  );
}

function AddStock({ onClose, onSaved }) {
  const { data: units } = useFetch("/api/units");
  const [name, setName] = useState("");
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
    if (!name.trim()) return setErr("Enter design number / name");
    if (!(Number(qty) > 0)) return setErr("Enter quantity");
    setBusy(true); setErr("");
    try {
      await api.post("/api/raw-materials/stock-entry", {
        name: name.trim(), unit_id: unitId ? Number(unitId) : null,
        quantity: Number(qty), rate: Number(rate) || 0 });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title="Add Stock">
      <div className="space-y-3">
        <Field label="Design Number / Name" required>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. D-204 or Cotton Blue" />
        </Field>
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
        <Field label="Rate per unit (optional)">
          <input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="0" />
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2"><button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Add"}</button></div>
      </div>
    </Modal>
  );
}

const SIZES = [["m", "M"], ["l", "L"], ["xl", "XL"], ["xxl", "XXL"], ["mxxl", "M-XXL"]];

function Adjust({ row, onClose, onSaved }) {
  const [givenStr, setGivenStr] = useState("");
  const [reason, setReason] = useState("Given to tailor");
  const [name, setName] = useState("");
  const [tailorType, setTailorType] = useState("work");
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const given = Number(givenStr) || 0;
  const remaining = row.quantity - given;
  const sizeTotal = SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);

  const save = async () => {
    if (!(given > 0)) return setErr("Enter how much you gave / used");
    if (given > row.quantity) return setErr(`Only ${num(row.quantity, 2)} ${row.unit} in stock`);
    setBusy(true); setErr("");
    const sizeObj = Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));
    try {
      await api.post(`/api/raw-materials/${row.id}/adjust`, {
        new_quantity: remaining, reason_type: reason, recipient_name: name,
        tailor_type: tailorType, sizes: sizeTotal > 0 ? sizeObj : null,
      });
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`Give / Use — ${row.name}`}>
      <div className="space-y-3">
        <div className="text-sm text-ink2">Current stock: <b>{num(row.quantity, 2)} {row.unit}</b></div>
        <Field label={`Quantity given (${row.unit})`} required>
          <input className="input" inputMode="decimal" value={givenStr} autoFocus
                 placeholder={`e.g. 10`}
                 onChange={(e) => setGivenStr(e.target.value.replace(/[^0-9.]/g, ""))} />
        </Field>
        {given > 0 && (
          <div className={`rounded-lg px-3 py-2 text-xs ${remaining < 0 ? "bg-dangerSoft text-danger" : "bg-surface2 text-ink3"}`}>
            {remaining < 0
              ? `Not enough stock — only ${num(row.quantity, 2)} ${row.unit} available`
              : <>Remaining stock after this: <b className="text-ink">{num(remaining, 2)} {row.unit}</b>
                 {reason === "Given to tailor" && ` · a ${tailorType} tailor job will be created in Production`}</>}
          </div>
        )}
        <Field label="Reason" required>
          <Select value={reason} onChange={setReason}>
            {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </Field>
        {reason === "Given to tailor" && (
          <>
            <Field label="Type of tailor" required>
              <Select value={tailorType} onChange={setTailorType}>
                <option value="work">Work (stitching — fabric → pieces)</option>
                <option value="final">Final (finishing — pieces → finished goods)</option>
              </Select>
            </Field>
            <div>
              <label className="label">Pieces per size (optional)</label>
              <div className="flex flex-wrap gap-2">
                {SIZES.map(([k, lbl]) => (
                  <div key={k} className="w-16 text-center">
                    <div className="text-[11px] text-muted">{lbl}</div>
                    <input className="input px-1 text-center" inputMode="numeric" value={sizes[k]}
                           onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
                  </div>
                ))}
              </div>
              {sizeTotal > 0 && <div className="mt-1 text-xs text-muted">Total target: <b className="text-ink">{sizeTotal}</b> pieces</div>}
            </div>
          </>
        )}
        <Field label={NAME_LABEL[reason] + " (optional)"}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                 placeholder={reason === "Given to tailor" ? "e.g. Ramesh" : ""} />
        </Field>
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
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
