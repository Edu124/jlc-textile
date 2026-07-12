import { useRef, useState } from "react";
import api from "../api";
import { apiError } from "../lib/useFetch.js";
import { PageHeader, Card, Spinner } from "../components/ui.jsx";

const NAME_HEADINGS = ["name", "customer", "party", "shop"];
const PHONE_HEADINGS = ["phone", "mobile", "contact", "number", "no."];

export default function ImportCustomers() {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [gsUrl, setGsUrl] = useState("");
  const [namesText, setNamesText] = useState("");
  const [numbersText, setNumbersText] = useState("");

  // ── Copy & Paste (two columns) ──────────────────────────────────────────────
  // Lines are paired by position: 1st name ↔ 1st number, and so on. Empty
  // lines are kept while pairing so a blank phone cell in the sheet doesn't
  // shift every number after it onto the wrong customer.
  const rawNames = namesText.split(/\r?\n/).map((s) => s.trim());
  const rawNums = numbersText.split(/\r?\n/).map((s) => s.trim());
  while (rawNames.length && !rawNames[rawNames.length - 1]) rawNames.pop();
  while (rawNums.length && !rawNums[rawNums.length - 1]) rawNums.pop();
  // If they copied the headings too ("Name" / "Phone"), drop that first line.
  const nameStart = rawNames.length && NAME_HEADINGS.some((w) => rawNames[0].toLowerCase().includes(w)) ? 1 : 0;
  const numStart = rawNums.length && PHONE_HEADINGS.some((w) => rawNums[0].toLowerCase().includes(w)) ? 1 : 0;
  const names = rawNames.slice(nameStart);
  const nums = rawNums.slice(numStart);
  const pairs = names
    .map((n, i) => [n, (nums[i] || "").replace(/[^\d+\/ ]/g, "").trim()])
    .filter(([n]) => n);
  const extraNums = Math.max(0, nums.length - names.length);

  const importPasted = async () => {
    if (!pairs.length) return setErr("Paste the names in the left box first");
    setErr(""); setResult(null); setBusy(true);
    try {
      // Explicit heading row so the server pairs the columns exactly as shown.
      const { data } = await api.post("/api/customers/import-rows",
        { rows: [["Name", "Phone"], ...pairs] });
      setResult(data); setNamesText(""); setNumbersText("");
    } catch (ex) { setErr(apiError(ex)); }
    finally { setBusy(false); }
  };

  // ── Excel / CSV file ────────────────────────────────────────────────────────
  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErr(""); setResult(null); setBusy(true);
    try {
      // Read the Excel ON THIS DEVICE and send only the cell values — a heavy
      // file full of logos and formatting becomes a few KB over the network.
      // This also reads old .xls files. If local parsing fails for any reason,
      // fall back to uploading the raw file for the server to read.
      let rows = null;
      try {
        const XLSX = await import("xlsx");
        const wb = XLSX.read(await file.arrayBuffer());
        for (const name of wb.SheetNames) {
          const sheet = XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, defval: "" });
          const filled = sheet.filter((r) => r.some((c) => String(c).trim() !== ""));
          if (filled.length) { rows = filled; break; }
        }
      } catch { rows = null; }

      let data;
      if (rows && rows.length) {
        ({ data } = await api.post("/api/customers/import-rows", { rows }));
      } else {
        const form = new FormData();
        form.append("file", file);
        ({ data } = await api.post("/api/customers/import", form));
      }
      setResult(data);
    } catch (ex) { setErr(apiError(ex)); }
    finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  // ── Google Sheets link ──────────────────────────────────────────────────────
  const importSheet = async () => {
    if (!gsUrl.trim()) return setErr("Paste the Google Sheets link first");
    setErr(""); setResult(null); setBusy(true);
    try {
      const { data } = await api.post("/api/customers/import-gsheet", { url: gsUrl.trim() });
      setResult(data); setGsUrl("");
    } catch (ex) { setErr(apiError(ex)); }
    finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl">
      <PageHeader title="Import Customers" subtitle="Paste your list, upload an Excel file, or use a Google Sheets link — every customer gets added to your Customers list" />

      <Card title="Copy & Paste — easiest">
        <p className="mb-3 text-sm text-ink2">
          In your Excel or Sheet: select the <b>whole Names column</b>, copy, and paste it in the
          left box. Then copy the <b>whole Numbers column</b> and paste it in the right box.
          The 1st name goes with the 1st number, the 2nd with the 2nd, and so on.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="label">Customer Names</label>
            <textarea className="input font-mono text-sm" rows={8}
                      placeholder={"Krishna Fashion\nBombay Textiles\nMeena Collection"}
                      value={namesText} onChange={(e) => setNamesText(e.target.value)} />
          </div>
          <div>
            <label className="label">Phone Numbers</label>
            <textarea className="input font-mono text-sm" rows={8}
                      placeholder={"9876543210\n9876543211\n9876543212"}
                      value={numbersText} onChange={(e) => setNumbersText(e.target.value)} />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button className="btn-primary" onClick={importPasted} disabled={busy || !pairs.length}>
            {busy ? <Spinner /> : `Add ${pairs.length || ""} Customer${pairs.length === 1 ? "" : "s"}`}
          </button>
          {pairs.length > 0 && (
            <span className="text-xs text-muted">
              First one: <b className="text-ink2">{pairs[0][0]}</b>{pairs[0][1] && <> — {pairs[0][1]}</>}
            </span>
          )}
        </div>
        {extraNums > 0 && (
          <p className="mt-2 text-xs text-amber-400">
            There are {extraNums} more number{extraNums === 1 ? "" : "s"} than names — check that
            both boxes start from the same row.
          </p>
        )}
      </Card>

      <Card title="Or upload an Excel / CSV file" className="mt-4">
        <p className="mb-1 text-sm text-ink2">
          The first row can be headings — <b>Name, Phone, Email, Address, GST</b> in any order.
        </p>
        <p className="mb-4 text-xs text-muted">
          Without headings, columns are read in that same order. Only Name is required.
          Customers that already exist (same name) are skipped, never duplicated.
        </p>
        <input ref={fileRef} type="file" accept=".xlsx,.xlsm,.xls,.csv" onChange={onFile}
               className="hidden" id="import-input" />
        <label htmlFor="import-input" className="btn-primary inline-flex cursor-pointer items-center gap-2">
          {busy ? <Spinner /> : "⬆ Choose Excel / CSV File"}
        </label>
      </Card>

      <Card title="Or import from Google Sheets" className="mt-4">
        <p className="mb-1 text-sm text-ink2">
          Paste the sheet's link — the tab open in the link is the one that gets imported.
        </p>
        <p className="mb-3 text-xs text-muted">
          The sheet must be shared first: in Google Sheets tap <b>Share</b> and set
          General access to <b>"Anyone with the link"</b> (Viewer is enough).
        </p>
        <div className="flex flex-wrap gap-2">
          <input className="input min-w-[240px] flex-1" placeholder="https://docs.google.com/spreadsheets/d/…"
                 value={gsUrl} onChange={(e) => setGsUrl(e.target.value)} />
          <button className="btn-primary" onClick={importSheet} disabled={busy}>
            {busy ? <Spinner /> : "Import Sheet"}
          </button>
        </div>
      </Card>

      {err && <div className="mt-4 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}

      {result && (
        <Card title="Import Result" className="mt-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-ok">{result.added}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Added</div>
            </div>
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-warn">{result.skipped_duplicate}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Already Existed</div>
            </div>
            <div className="rounded-xl bg-surface2 px-3 py-3 text-center">
              <div className="text-2xl font-extrabold text-muted">{result.skipped_no_name}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">No Name (skipped)</div>
            </div>
          </div>
          {result.names.length > 0 && (
            <div className="mt-4">
              <div className="mb-1 text-xs font-bold uppercase tracking-wide text-muted">Added customers</div>
              <div className="flex flex-wrap gap-1.5">
                {result.names.map((n, i) => (
                  <span key={i} className="rounded-lg bg-okSoft px-2 py-1 text-xs text-ok">{n}</span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
