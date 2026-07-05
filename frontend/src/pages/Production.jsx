import { useEffect, useState } from "react";
import api from "../api";
import { useFetch, apiError, openPdf } from "../lib/useFetch.js";
import { num } from "../lib/format.js";
import { PageHeader, Table, Modal, Field, Select, Spinner } from "../components/ui.jsx";

export default function Production() {
  const { data: jobs, loading, reload } = useFetch("/api/production/jobs");
  const [trackFor, setTrackFor] = useState(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [tailorsOpen, setTailorsOpen] = useState(false);

  const clear = async (j) => {
    if (!confirm(`Remove the job: ${j.material} → ${j.tailor}? (Any stock already created from it is kept.)`)) return;
    try { await api.delete(`/api/production/jobs/${j.id}`); reload(); }
    catch (e) { alert(apiError(e)); }
  };

  const jobsArr = jobs || [];
  const workJobs = jobsArr.filter((j) => (j.tailor_type || "work") === "work" && j.tailor !== "Direct Entry");
  const finalJobs = jobsArr.filter((j) => j.tailor_type === "final" && j.tailor !== "Direct Entry");

  // Pieces-tracked when pieces were set; otherwise the metres given are the goal.
  const piecesCell = (r) => (r.target_pieces > 0
    ? <span className={r.delivered_pieces >= r.target_pieces ? "font-semibold text-ok" : "font-semibold text-ink"}>
        {num(r.delivered_pieces, 0)} / {num(r.target_pieces, 0)} pcs
      </span>
    : <span className={r.delivered_metres >= r.qty_given && r.qty_given > 0 ? "font-semibold text-ok" : "font-semibold text-ink"}>
        {num(r.delivered_metres, 2)} / {num(r.qty_given, 2)} {r.unit || "m"}
      </span>);

  const workColumns = [
    { header: "Design", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setTrackFor(r)}>{r.material}</button>
    )},
    { header: "Work Tailor", key: "tailor" },
    { header: "Given", cell: (r) => `${num(r.qty_given, 2)} ${r.unit}` },
    { header: "Ready", cell: piecesCell },
    { header: "To Assign", cell: (r) => (r.ready_to_assign > 0
        ? <span className="font-semibold text-warn">{num(r.ready_to_assign, 0)} pcs</span>
        : r.ready_metres > 0
        ? <span className="font-semibold text-warn">{num(r.ready_metres, 2)} {r.unit || "m"}</span>
        : "—") },
    { header: "Date", key: "created_at" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setTrackFor(r)}>Track</button>
        <button className="text-accent" onClick={() => openPdf(`/api/production/jobs/${r.id}/challan`, `challan-${r.id}.pdf`)}>Challan</button>
        <button className="text-danger" onClick={() => clear(r)}>Clear</button>
      </div>
    )},
  ];

  const finalColumns = [
    { header: "Design", cell: (r) => (
      <button className="font-medium text-accent hover:underline" onClick={() => setTrackFor(r)}>{r.material}</button>
    )},
    { header: "Final Tailor", key: "tailor" },
    { header: "Pieces Given", cell: (r) => num(r.qty_given, 0) },
    { header: "Delivered", cell: piecesCell },
    { header: "In Finished Goods", cell: (r) => (r.finished_qty > 0
        ? <span className="font-semibold text-ok">{num(r.finished_qty, 0)} pcs</span> : "—") },
    { header: "Date", key: "created_at" },
    { header: "Actions", cell: (r) => (
      <div className="flex gap-3">
        <button className="text-accent" onClick={() => setTrackFor(r)}>Track</button>
        <button className="text-accent" onClick={() => openPdf(`/api/production/jobs/${r.id}/challan`, `challan-${r.id}.pdf`)}>Challan</button>
        <button className="text-danger" onClick={() => clear(r)}>Clear</button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Production — Tailor Jobs"
        subtitle="Assign raw material to a tailor — a printable challan is generated for every assignment."
        action={
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => setTailorsOpen(true)}>+ Add Tailor</button>
            <button className="btn-primary" onClick={() => setAssignOpen(true)}>+ Assign</button>
          </div>
        } />
      {loading ? <Spinner /> : (
        <div className="space-y-8">
          <div>
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">Work Tailors (fabric → pieces)</h2>
            <Table columns={workColumns} rows={workJobs}
                   empty="No work-tailor jobs yet — tap + Assign to give fabric to a work tailor." />
          </div>
          <div>
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">Final Tailors (pieces → finished goods)</h2>
            <Table columns={finalColumns} rows={finalJobs}
                   empty="No final-tailor jobs yet — tap + Assign and pick a final tailor to hand ready work onward." />
          </div>
        </div>
      )}
      {trackFor && <TrackJob job={trackFor} onClose={() => setTrackFor(null)} onChanged={reload} />}
      {assignOpen && <AssignModal onClose={() => setAssignOpen(false)} onSaved={() => { setAssignOpen(false); reload(); }} />}
      {tailorsOpen && <TailorsModal onClose={() => setTailorsOpen(false)} />}
    </div>
  );
}

function TailorsModal({ onClose }) {
  const { data: tailors, reload } = useFetch("/api/production/tailors");
  const [name, setName] = useState("");
  const [ttype, setTtype] = useState("work");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  const add = async () => {
    if (!name.trim()) return setErr("Enter the tailor's name");
    setBusy(true); setErr("");
    try {
      await api.post("/api/production/tailors", { name: name.trim(), tailor_type: ttype });
      setName(""); reload();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  const remove = async (t) => {
    if (!confirm(`Remove tailor "${t.name}"?`)) return;
    await api.delete(`/api/production/tailors/${t.id}`); reload();
  };

  return (
    <Modal open onClose={onClose} title="Tailors">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Ramesh" />
        </div>
        <div className="w-40">
          <label className="label">Type</label>
          <Select value={ttype} onChange={setTtype}>
            <option value="work">Work</option>
            <option value="final">Final</option>
          </Select>
        </div>
        <button className="btn-primary" onClick={add} disabled={busy}>{busy ? <Spinner /> : "+ Add"}</button>
      </div>
      {err && <div className="mt-2 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 space-y-1">
        {!tailors?.length ? (
          <div className="rounded-lg bg-surface2 px-3 py-3 text-center text-sm text-muted">No tailors added yet</div>
        ) : tailors.map((t) => (
          <div key={t.id} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2 text-sm">
            <span className="text-ink">{t.name}</span>
            <div className="flex items-center gap-3">
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${t.tailor_type === "final" ? "bg-okSoft text-ok" : "bg-accentSoft text-info"}`}>
                {t.tailor_type === "final" ? "Final" : "Work"}
              </span>
              <button className="text-danger" onClick={() => remove(t)}>✕</button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

const BASE_COLORS = ["Red", "Blue", "Green", "Yellow", "Pink", "White"];
const SIZE_LABELS = ["M", "L", "XL", "XXL", "M-XXL"];

function AssignModal({ onClose, onSaved }) {
  const { data: tailors } = useFetch("/api/production/tailors");
  const { data: materials } = useFetch("/api/raw-materials");
  const { data: allJobs } = useFetch("/api/production/jobs");
  const { data: settings } = useFetch("/api/settings");
  const [tailorId, setTailorId] = useState("");
  const [matId, setMatId] = useState("");
  const [metres, setMetres] = useState("");
  const [pieces, setPieces] = useState("");
  // colors list: [{size, color, pieces}] built row by row
  const [colorSize, setColorSize] = useState("M");
  const [colorSel, setColorSel] = useState("Red");
  const [customColor, setCustomColor] = useState("");
  const [colorPcs, setColorPcs] = useState("");
  const [colorItems, setColorItems] = useState([]);
  const [savedCustom, setSavedCustom] = useState([]);   // custom colors from Settings
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [takes, setTakes] = useState({});          // work job id -> qty taken
  const [addDesc, setAddDesc] = useState("");
  const [addMetres, setAddMetres] = useState("");
  const [additional, setAdditional] = useState([]);  // [{description, metres}]
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");

  useEffect(() => {
    if (settings?.custom_colors) {
      setSavedCustom(settings.custom_colors.split(",").map((c) => c.trim()).filter(Boolean));
    }
  }, [settings]);

  const mat = materials?.find((m) => String(m.id) === String(matId));
  const tailor = tailors?.find((t) => String(t.id) === String(tailorId));
  const isFinal = tailor?.tailor_type === "final";

  // With color entries, sizes come from them automatically.
  const colorSizeTotals = SIZES.reduce((acc, [k, lbl]) => {
    acc[k] = colorItems.filter((c) => c.size === lbl).reduce((a, c) => a + (c.pieces || 0), 0);
    return acc;
  }, {});
  const useColorSizes = colorItems.length > 0;
  const sizeTotal = useColorSizes
    ? Object.values(colorSizeTotals).reduce((a, b) => a + b, 0)
    : SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);
  const effSizes = useColorSizes
    ? colorSizeTotals
    : Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));

  const allColors = [...BASE_COLORS, ...savedCustom.filter((c) => !BASE_COLORS.some((b) => b.toLowerCase() === c.toLowerCase()))];

  const pushColor = async () => {
    const color = colorSel === "__custom__" ? customColor.trim() : colorSel;
    if (!color) return setErr("Enter the custom color name");
    if (!(Number(colorPcs) > 0)) return setErr("Enter pieces for this color");
    setErr("");
    setColorItems([...colorItems, { size: colorSize, color, pieces: Number(colorPcs) }]);
    setColorPcs("");
    // remember new custom colors for next time
    if (colorSel === "__custom__" && !allColors.some((c) => c.toLowerCase() === color.toLowerCase())) {
      const updated = [...savedCustom, color];
      setSavedCustom(updated);
      setColorSel(color); setCustomColor("");
      try { await api.put("/api/settings", { values: { custom_colors: updated.join(",") } }); } catch { /* non-fatal */ }
    }
  };

  // Work-tailor output ready to hand onward (pieces or metres), optionally
  // filtered to the selected design.
  const readyJobs = (allJobs || []).filter((j) =>
    (j.tailor_type || "work") === "work" &&
    (j.ready_to_assign > 0 || j.ready_metres > 0) &&
    (!matId || String(j.material_id) === String(matId)));
  const takenTotal = readyJobs.reduce((a, j) => a + (Number(takes[j.id]) || 0), 0);

  const pushAdditional = () => {
    if (!addDesc.trim() && !(Number(addMetres) > 0)) return;
    setAdditional([...additional, { description: addDesc.trim(), metres: Number(addMetres) || 0 }]);
    setAddDesc(""); setAddMetres("");
  };

  const save = async (printChallan) => {
    if (!tailorId) return setErr("Select a tailor");
    setBusy(true); setErr("");
    const sizeObj = effSizes;
    try {
      if (isFinal && takenTotal > 0) {
        // hand ready work output onward to the final tailor
        const sources = readyJobs
          .filter((j) => (Number(takes[j.id]) || 0) > 0)
          .map((j) => (j.ready_to_assign > 0
            ? { job_id: j.id, pieces: Number(takes[j.id]) }
            : { job_id: j.id, metres: Number(takes[j.id]) }));
        const { data } = await api.post("/api/production/assign-from-work", {
          tailor_id: Number(tailorId), sources, colors: colorItems,
          sizes: sizeTotal > 0 ? sizeObj : null, additional,
        });
        if (printChallan) {
          for (const id of data.ids) await openPdf(`/api/production/jobs/${id}/challan`, `challan-${id}.pdf`);
        }
      } else {
        if (!matId) { setBusy(false); return setErr(isFinal ? "Enter a quantity from a work tailor below, or pick a design to give from stock" : "Select a design"); }
        const given = Number(metres) > 0 ? Number(metres) : (Number(pieces) || 0);
        if (!(given > 0 || sizeTotal > 0)) { setBusy(false); return setErr("Enter metres or pieces"); }
        if (mat && Number(metres) > 0 && Number(metres) > mat.quantity) {
          setBusy(false); return setErr(`Only ${num(mat.quantity, 2)} ${mat.unit} in stock`);
        }
        const { data } = await api.post("/api/production/assign", {
          tailor_id: Number(tailorId), material_type_id: Number(matId),
          metres: Number(metres) || 0, pieces: Number(pieces) || 0,
          colors: colorItems, sizes: sizeTotal > 0 ? sizeObj : null, additional,
        });
        if (printChallan) await openPdf(`/api/production/jobs/${data.id}/challan`, `challan-${data.id}.pdf`);
      }
      onSaved();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title="Assign Work to Tailor" wide>
      {/* Row 1: who + what */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Tailor" required>
          <Select value={tailorId} onChange={setTailorId}>
            <option value="">— Select Tailor —</option>
            {tailors?.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.tailor_type === "final" ? "Final" : "Work"})</option>)}
          </Select>
        </Field>
        <Field label={isFinal ? "Design Number (optional — filters the list below)" : "Design Number"} required={!isFinal}>
          <Select value={matId} onChange={setMatId}>
            <option value="">— Select Design —</option>
            {materials?.map((m) => <option key={m.id} value={m.id}>{m.name}{m.design_no ? ` (${m.design_no})` : ""} — {num(m.quantity, 2)} {m.unit} in stock</option>)}
          </Select>
        </Field>
      </div>

      {/* Final tailor: ready output from work tailors */}
      {isFinal && (
        <div className="mt-3 rounded-xl border border-separator bg-bg p-3">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Ready from Work Tailors</div>
          {!readyJobs.length ? (
            <div className="py-1 text-sm text-muted">
              {matId ? "Nothing ready from work tailors for this design yet." : "Nothing ready from work tailors yet."}
            </div>
          ) : (
            <div className="space-y-1.5">
              {readyJobs.map((j) => {
                const inPieces = j.ready_to_assign > 0;
                const ready = inPieces ? j.ready_to_assign : j.ready_metres;
                const unitLbl = inPieces ? "pcs" : (j.unit || "m");
                return (
                  <div key={j.id} className="flex items-center gap-3 rounded-lg bg-surface2 px-3 py-2 text-sm">
                    <div className="flex-1">
                      <span className="font-semibold text-ink">{j.material}</span>
                      <span className="ml-2 text-xs text-muted">{j.tailor} · {num(ready, inPieces ? 0 : 2)} {unitLbl} ready</span>
                    </div>
                    <input className="input w-24 text-center" inputMode="decimal" placeholder={`${unitLbl}`}
                           value={takes[j.id] ?? ""}
                           onChange={(e) => setTakes({ ...takes, [j.id]: e.target.value.replace(/[^0-9.]/g, "") })} />
                    <button type="button" className="text-xs text-accent hover:underline"
                            onClick={() => setTakes({ ...takes, [j.id]: ready })}>all</button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Give from raw material stock (main flow for work tailors; optional extra for final) */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Field label={`Metres${mat ? ` (stock ${num(mat.quantity, 2)} ${mat.unit})` : ""}`}>
          <input className="input" inputMode="decimal" value={metres}
                 onChange={(e) => setMetres(e.target.value.replace(/[^0-9.]/g, ""))} placeholder="e.g. 50" />
        </Field>
        <Field label="Pieces">
          <input className="input" inputMode="numeric" value={pieces}
                 onChange={(e) => setPieces(e.target.value.replace(/[^0-9]/g, ""))} placeholder="e.g. 100" />
        </Field>
      </div>

      {/* Colors: size + color + pieces, built as a list */}
      <div className="mt-3 rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Colors (per size)</div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-24">
            <label className="label">Size</label>
            <Select value={colorSize} onChange={setColorSize}>
              {SIZE_LABELS.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </div>
          <div className="w-32">
            <label className="label">Color</label>
            <Select value={colorSel} onChange={setColorSel}>
              {allColors.map((c) => <option key={c} value={c}>{c}</option>)}
              <option value="__custom__">Custom…</option>
            </Select>
          </div>
          {colorSel === "__custom__" && (
            <div className="w-32">
              <label className="label">Custom color</label>
              <input className="input" value={customColor} onChange={(e) => setCustomColor(e.target.value)} placeholder="e.g. Maroon" />
            </div>
          )}
          <div className="w-24">
            <label className="label">Pieces</label>
            <input className="input text-center" inputMode="numeric" value={colorPcs}
                   onChange={(e) => setColorPcs(e.target.value.replace(/[^0-9]/g, ""))} />
          </div>
          <button type="button" className="btn-ghost" onClick={pushColor}>+ Add</button>
        </div>
        {colorItems.length > 0 && (
          <div className="mt-2 space-y-1">
            {colorItems.map((c, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-1.5 text-sm">
                <span className="text-ink"><b>{c.size}</b> · {c.color}</span>
                <div className="flex items-center gap-3">
                  <span className="text-ink2">{num(c.pieces, 0)} pcs</span>
                  <button className="text-danger" onClick={() => setColorItems(colorItems.filter((_, x) => x !== i))}>✕</button>
                </div>
              </div>
            ))}
            <div className="pt-1 text-right text-xs text-muted">Total: <b className="text-ink">{num(sizeTotal, 0)}</b> pcs</div>
          </div>
        )}
      </div>

      {/* Sizes — auto-filled from the colors list when it's used */}
      <div className="mt-3">
        <label className="label">Pieces per size {useColorSizes ? "(from colors list)" : "(optional)"}</label>
        <div className="flex flex-wrap gap-2">
          {SIZES.map(([k, lbl]) => (
            <div key={k} className="w-16 text-center">
              <div className="text-[11px] text-muted">{lbl}</div>
              <input className="input px-1 text-center" inputMode="numeric"
                     value={useColorSizes ? (colorSizeTotals[k] || "") : sizes[k]}
                     disabled={useColorSizes}
                     onChange={(e) => setSizes({ ...sizes, [k]: e.target.value.replace(/[^0-9]/g, "") })} />
            </div>
          ))}
          {sizeTotal > 0 && <div className="self-end pb-2 text-xs text-muted">= <b className="text-ink">{sizeTotal}</b> pcs</div>}
        </div>
      </div>

      {/* Additional items given (astar, lining, buttons...) */}
      <div className="mt-3 rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Additional (extra material given)</div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="label">Description</label>
            <input className="input" value={addDesc} onChange={(e) => setAddDesc(e.target.value)} placeholder="e.g. Astar cloth" />
          </div>
          <div className="w-28">
            <label className="label">Metres</label>
            <input className="input" inputMode="decimal" value={addMetres}
                   onChange={(e) => setAddMetres(e.target.value.replace(/[^0-9.]/g, ""))} />
          </div>
          <button type="button" className="btn-ghost" onClick={pushAdditional}>+ Add</button>
        </div>
        {additional.length > 0 && (
          <div className="mt-2 space-y-1">
            {additional.map((a, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-1.5 text-sm">
                <span className="text-ink">{a.description || "—"}</span>
                <div className="flex items-center gap-3">
                  <span className="text-ink2">{a.metres ? `${num(a.metres, 2)} m` : "—"}</span>
                  <button className="text-danger" onClick={() => setAdditional(additional.filter((_, x) => x !== i))}>✕</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {tailor && (
        <p className="mt-2 text-xs text-muted">
          {isFinal
            ? "Final tailor — delivered pieces will move straight into Finished Goods."
            : "Work tailor — log ready pieces/metres from Track as they come back, then assign them onward to a final tailor."}
        </p>
      )}
      {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-ghost" onClick={() => save(false)} disabled={busy}>Save</button>
        <button className="btn-primary" onClick={() => save(true)} disabled={busy}>{busy ? <Spinner /> : "Save & Print Challan"}</button>
      </div>
    </Modal>
  );
}

const SIZES = [["m", "M"], ["l", "L"], ["xl", "XL"], ["xxl", "XXL"], ["mxxl", "M-XXL"]];

function TrackJob({ job, onClose, onChanged }) {
  const { data: deliveries, reload: reloadDeliveries } = useFetch(`/api/production/jobs/${job.id}/deliveries`);
  const { data: jobData, reload: reloadJob } = useFetch(`/api/production/jobs/${job.id}`);
  const j = jobData || job;

  const [target, setTarget] = useState(String(job.target_pieces || ""));
  const [savingTarget, setSavingTarget] = useState(false);

  const [pieces, setPieces] = useState("");
  const [sizes, setSizes] = useState({ m: "", l: "", xl: "", xxl: "", mxxl: "" });
  const [dDate, setDDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const sizeTotal = SIZES.reduce((a, [k]) => a + (Number(sizes[k]) || 0), 0);

  const refreshAll = () => { reloadDeliveries(); reloadJob(); onChanged?.(); };

  const saveTarget = async () => {
    setSavingTarget(true);
    try { await api.post(`/api/production/jobs/${job.id}/target`, { target_pieces: Number(target) || 0 }); refreshAll(); }
    catch (e) { setErr(apiError(e)); } finally { setSavingTarget(false); }
  };

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImage(reader.result);
    reader.readAsDataURL(file);
  };

  const [metres, setMetres] = useState("");
  // Pieces mode when pieces were set; otherwise progress is tracked in metres
  // against the metres given.
  const pieceMode = (j.target_pieces || 0) > 0;

  const addDelivery = async () => {
    const effective = pieceMode ? (sizeTotal > 0 ? sizeTotal : (Number(pieces) || 0)) : (Number(metres) || 0);
    if (!(effective > 0)) return setErr(pieceMode ? "Enter pieces received" : "Enter metres received");
    setBusy(true); setErr("");
    const sizeObj = Object.fromEntries(SIZES.map(([k]) => [k, Number(sizes[k]) || 0]));
    try {
      await api.post(`/api/production/jobs/${job.id}/deliveries`, {
        delivery_date: dDate, pieces: pieceMode ? (Number(pieces) || 0) : 0,
        metres: pieceMode ? 0 : (Number(metres) || 0),
        sizes: pieceMode && sizeTotal > 0 ? sizeObj : null, image_base64: image, notes });
      setPieces(""); setMetres(""); setSizes({ m: "", l: "", xl: "", xxl: "", mxxl: "" }); setNotes(""); setImage(null);
      refreshAll();
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  const removeDelivery = async (id) => {
    if (!confirm("Remove this delivery record?")) return;
    await api.delete(`/api/production/jobs/${job.id}/deliveries/${id}`); refreshAll();
  };

  const delivered = j.delivered_pieces || 0;
  const targetNum = j.target_pieces || 0;
  const remaining = Math.max(0, targetNum - delivered);
  const deliveredM = j.delivered_metres || 0;
  const givenM = j.qty_given || 0;

  return (
    <Modal open onClose={onClose} title={`${job.material} → ${job.tailor}`} wide>
      {/* Progress + pieces setting */}
      <div className="rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Progress</div>
        <div className="flex items-end gap-2">
          <div className="w-32">
            <label className="label">Total pieces</label>
            <input className="input" inputMode="numeric" value={target} placeholder="empty = metres"
                   onChange={(e) => setTarget(e.target.value.replace(/[^0-9]/g, ""))} />
          </div>
          <button className="btn-ghost" onClick={saveTarget} disabled={savingTarget}>{savingTarget ? <Spinner /> : "Save"}</button>
          <div className="ml-auto text-right text-sm">
            {pieceMode ? (
              <>
                <span className="font-bold text-ink">{num(delivered, 0)}</span>
                <span className="text-muted"> / {num(targetNum, 0)} pcs done · </span>
                <span className={remaining === 0 ? "font-semibold text-ok" : "font-semibold text-warn"}>{num(remaining, 0)} left</span>
              </>
            ) : (
              <>
                <span className="font-bold text-ink">{num(deliveredM, 2)}</span>
                <span className="text-muted"> / {num(givenM, 2)} {j.unit || "m"} done · </span>
                <span className={givenM - deliveredM <= 0 ? "font-semibold text-ok" : "font-semibold text-warn"}>{num(Math.max(0, givenM - deliveredM), 2)} {j.unit || "m"} left</span>
              </>
            )}
          </div>
        </div>
        {!pieceMode && (
          <p className="mt-1 text-[11px] text-muted">No pieces set — this job is tracked in metres against the {num(givenM, 2)} {j.unit || "m"} given. Enter total pieces above to switch.</p>
        )}
      </div>

      {/* Add delivery */}
      <div className="mt-4 rounded-xl border border-separator bg-bg p-3">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{pieceMode ? "Log Ready Pieces" : "Log Ready Metres"}</div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-28"><label className="label">Date</label>
            <input type="date" className="input" value={dDate} onChange={(e) => setDDate(e.target.value)} /></div>
          {pieceMode ? (
            <div className="w-24"><label className="label">Pieces</label>
              <input className="input" inputMode="numeric" value={sizeTotal > 0 ? sizeTotal : pieces}
                     disabled={sizeTotal > 0}
                     onChange={(e) => setPieces(e.target.value.replace(/[^0-9]/g, ""))} /></div>
          ) : (
            <div className="w-28"><label className="label">Metres</label>
              <input className="input" inputMode="decimal" value={metres}
                     onChange={(e) => setMetres(e.target.value.replace(/[^0-9.]/g, ""))} /></div>
          )}
          <div className="min-w-[140px] flex-1"><label className="label">Notes</label>
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="optional" /></div>
          <div>
            <label className="label">Photo</label>
            <input type="file" accept="image/*" onChange={onFile} className="hidden" id={`photo-${job.id}`} />
            <label htmlFor={`photo-${job.id}`} className="btn-ghost inline-block cursor-pointer">{image ? "✓ Photo" : "📷 Add"}</label>
          </div>
          <button className="btn-primary" onClick={addDelivery} disabled={busy}>{busy ? <Spinner /> : "+ Add"}</button>
        </div>
        {pieceMode && (
          <div className="mt-2">
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
          </div>
        )}
        {image && <img src={image} alt="preview" className="mt-2 h-20 rounded-lg border border-separator object-cover" />}
        {err && <div className="mt-2 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
      </div>

      {/* Delivery log */}
      <div className="mt-4">
        <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Delivery Log</div>
        {!deliveries?.length ? (
          <div className="rounded-lg bg-surface2 px-3 py-4 text-center text-sm text-muted">No deliveries logged yet</div>
        ) : (
          <div className="space-y-2">
            {deliveries.map((d) => (
              <div key={d.id} className="flex items-center gap-3 rounded-lg bg-surface2 px-3 py-2">
                {d.image
                  ? <img src={d.image} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" />
                  : <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-bg text-muted">—</div>}
                <div className="flex-1">
                  <div className="text-sm font-semibold text-ink">
                    {d.metres > 0 ? `${num(d.metres, 2)} ${j.unit || "m"}` : `${num(d.pieces, 0)} pieces`}
                    {d.sizes && SIZES.some(([k]) => d.sizes[k] > 0) && (
                      <span className="ml-2 text-xs font-normal text-muted">
                        ({SIZES.filter(([k]) => d.sizes[k] > 0).map(([k, l]) => `${l}:${num(d.sizes[k], 0)}`).join("  ")})
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-muted">{d.delivery_date}{d.notes ? ` · ${d.notes}` : ""}</div>
                </div>
                <button className="text-danger" onClick={() => removeDelivery(d.id)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-end">
        <button className="btn-ghost" onClick={onClose}>Close</button>
      </div>
    </Modal>
  );
}

function AdjustJob({ job, onClose, onSaved }) {
  const [held, setHeld] = useState(String(job.held));
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const returning = Math.max(0, job.held - (Number(held) || 0));

  const save = async () => {
    setBusy(true); setErr("");
    try { await api.post(`/api/production/jobs/${job.id}/adjust`, { new_held: Number(held) || 0 }); onSaved(); }
    catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title={`${job.material} → ${job.tailor}`}>
      <div className="space-y-3">
        <div className="text-sm text-ink2">Given: <b>{num(job.qty_given, 2)} {job.unit}</b> · Currently with tailor: <b>{num(job.held, 2)} {job.unit}</b></div>
        <Field label="Quantity still with tailor" required>
          <input className="input" inputMode="decimal" value={held} onChange={(e) => setHeld(e.target.value)} />
        </Field>
        {returning > 0 && (
          <div className="rounded-lg bg-warnSoft px-3 py-2 text-xs text-warn">
            {num(returning, 2)} {job.unit} returned → moved to <b>Products</b>, awaiting a rate.
            Set a rate there to move it into Finished Goods.
          </div>
        )}
        {err && <div className="rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner /> : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}

function JobDetail({ job, onClose }) {
  const rows = [
    ["Raw Material", job.material],
    ["Tailor", job.tailor],
    ["Given out", `${num(job.qty_given, 2)} ${job.unit}`],
    ["Still with tailor", `${num(job.held, 2)} ${job.unit}`],
    ["Total returned so far", `${num(job.qty_returned, 2)} ${job.unit}`],
    ["— Awaiting rate (in Products)", `${num(job.pending_qty, 2)} ${job.unit}`],
    ["— Priced & in Finished Goods", `${num(job.finished_qty, 2)} ${job.unit}`],
    ["Date", job.created_at],
  ];
  return (
    <Modal open onClose={onClose} title="Job Details">
      <div className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-separator/60 py-2 text-sm">
            <span className="text-muted">{k}</span><span className="font-semibold text-ink">{v}</span>
          </div>
        ))}
      </div>
      {job.pending_qty > 0 && (
        <p className="mt-3 text-xs text-warn">
          Go to Products and click "Set Rate" on "{job.material} ({job.tailor})" to move the awaiting quantity into Finished Goods.
        </p>
      )}
    </Modal>
  );
}
