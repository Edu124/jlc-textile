import { useRef, useState } from "react";
import api from "../api";
import { apiError } from "../lib/useFetch.js";
import { PageHeader, Card, Spinner } from "../components/ui.jsx";

export default function ImportCustomers() {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

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

  return (
    <div className="max-w-2xl">
      <PageHeader title="Import Customers" subtitle="Upload an Excel or CSV file and every customer in it gets added to your Customers list" />

      <Card title="Upload File">
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
