import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError } from "../lib/useFetch.js";
import { rupeeFull } from "../lib/format.js";
import { pendingCustomers } from "../lib/offline.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

/** Generic master CRUD screen.
 * fields: [{name, label, type, required, optionsFrom, optionLabel}]
 * pendingRows: () => rows saved offline & not yet synced (shown with a badge) */
function CrudPage({ title, subtitle, endpoint, columns, fields, itemName, pendingRows }) {
  const { data: rows, loading, reload } = useFetch(endpoint);
  const [editing, setEditing] = useState(null); // null=closed, {}=new, {..}=edit
  const [, setTick] = useState(0);              // refresh when the sync queue changes

  useEffect(() => {
    if (!pendingRows) return;
    const onQueue = () => { setTick((t) => t + 1); reload(); };
    window.addEventListener("jlc-queue-changed", onQueue);
    return () => window.removeEventListener("jlc-queue-changed", onQueue);
  }, [pendingRows, reload]);

  const del = async (id, name) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try { await api.delete(`${endpoint}/${id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const cols = [
    ...columns,
    { header: "Actions", cell: (r) => r.pending ? (
      <span className="text-xs text-amber-400">⟳ will sync when online</span>
    ) : (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setEditing(r)}>Edit</button>
        <button className="text-danger" onClick={() => del(r.id, r.name)}>Delete</button>
      </div>
    )},
  ];
  const allRows = [...(pendingRows ? pendingRows() : []), ...(rows || [])];

  return (
    <div>
      <PageHeader title={title} subtitle={subtitle}
        action={<button className="btn-primary" onClick={() => setEditing({})}>+ Add {itemName}</button>} />
      {loading ? <Spinner /> : <Table columns={cols} rows={allRows} empty={`No ${title.toLowerCase()} yet`} />}
      {editing !== null && (
        <CrudForm endpoint={endpoint} fields={fields} itemName={itemName}
          initial={editing} onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }} />
      )}
    </div>
  );
}

function CrudForm({ endpoint, fields, itemName, initial, onClose, onSaved }) {
  const [form, setForm] = useState(() => {
    const f = {};
    fields.forEach((fd) => { f[fd.name] = initial[fd.name] ?? (fd.type === "number" ? 0 : ""); });
    return f;
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const isEdit = !!initial.id;

  const save = async () => {
    for (const fd of fields)
      if (fd.required && !String(form[fd.name] ?? "").trim()) return setErr(`${fd.label} is required`);
    setBusy(true); setErr("");
    const payload = {};
    fields.forEach((fd) => {
      let v = form[fd.name];
      if (fd.type === "number") v = Number(v) || 0;
      if (fd.type === "select") v = v ? Number(v) : null;
      payload[fd.name] = v;
    });
    try {
      if (isEdit) await api.put(`${endpoint}/${initial.id}`, payload);
      else await api.post(endpoint, payload);
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={`${isEdit ? "Edit" : "Add"} ${itemName}`}>
      <div className="space-y-3">
        {fields.map((fd) => (
          <Field key={fd.name} label={fd.label} required={fd.required}>
            {fd.type === "select" ? (
              <SelectField fd={fd} value={form[fd.name]} onChange={(v) => setForm({ ...form, [fd.name]: v })} />
            ) : fd.type === "textarea" ? (
              <textarea className="input" rows={2} value={form[fd.name]}
                        onChange={(e) => setForm({ ...form, [fd.name]: e.target.value })} />
            ) : (
              <input className="input" type={fd.type === "number" ? "number" : "text"}
                     value={form[fd.name]} placeholder={fd.placeholder || ""}
                     onChange={(e) => setForm({ ...form, [fd.name]: e.target.value })} />
            )}
          </Field>
        ))}
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}

function SelectField({ fd, value, onChange }) {
  const { data: opts } = useFetch(fd.optionsFrom);
  return (
    <Select value={value || ""} onChange={onChange}>
      <option value="">— Select —</option>
      {opts?.map((o) => <option key={o.id} value={o.id}>{o[fd.optionLabel || "name"]}</option>)}
    </Select>
  );
}

// ── Concrete master screens ──────────────────────────────────────────────────
const PARTY_FIELDS = [
  { name: "name", label: "Name", required: true },
  { name: "phone", label: "Phone" },
  { name: "email", label: "Email" },
  { name: "gst_number", label: "GST Number" },
  { name: "address", label: "Address", type: "textarea" },
];
const PARTY_COLS = [
  { header: "Name", key: "name" }, { header: "Phone", key: "phone" },
  { header: "Email", key: "email" }, { header: "GST Number", key: "gst_number" },
];

export const Suppliers = () => (
  <CrudPage title="Suppliers" itemName="Supplier" endpoint="/api/suppliers"
            columns={PARTY_COLS} fields={PARTY_FIELDS} />
);
export const Customers = () => (
  <CrudPage title="Customers" itemName="Customer" endpoint="/api/customers"
            columns={PARTY_COLS} fields={PARTY_FIELDS} pendingRows={pendingCustomers} />
);

export const MaterialTypes = () => (
  <CrudPage title="Material Types" itemName="Material Type" endpoint="/api/material-types"
    columns={[
      { header: "Name", key: "name" }, { header: "Unit", key: "unit" },
      { header: "Low Stock Alert", key: "low_stock_threshold" },
    ]}
    fields={[
      { name: "name", label: "Name", required: true, placeholder: "e.g. Cotton Fabric" },
      { name: "unit_id", label: "Unit", type: "select", optionsFrom: "/api/units" },
      { name: "low_stock_threshold", label: "Low Stock Alert", type: "number" },
    ]} />
);

export const Units = () => (
  <CrudPage title="Units" itemName="Unit" endpoint="/api/units"
    columns={[{ header: "Name", key: "name" }, { header: "Abbreviation", key: "abbreviation" }]}
    fields={[
      { name: "name", label: "Name", required: true, placeholder: "e.g. Pieces" },
      { name: "abbreviation", label: "Abbreviation", required: true, placeholder: "e.g. pcs" },
    ]} />
);
