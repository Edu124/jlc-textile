import { useEffect } from "react";
import { STATUS_COLORS } from "../lib/format";

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-5 flex items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-extrabold text-ink">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Badge({ status }) {
  const cls = STATUS_COLORS[status] || "bg-surface2 text-muted";
  return <span className={`chip ${cls}`}>{status}</span>;
}

export function StatCard({ label, value, icon, accent = "#5E7E9B" }) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl2 text-2xl"
           style={{ background: accent + "29", color: accent }}>{icon}</div>
      <div>
        <div className="text-2xl font-extrabold text-ink">{value}</div>
        <div className="mt-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</div>
      </div>
    </div>
  );
}

export function Field({ label, required, children }) {
  return (
    <div>
      {label && <label className="label">{required ? "* " : ""}{label}</label>}
      {children}
    </div>
  );
}

export function Select({ value, onChange, children, ...rest }) {
  return (
    <select className="input appearance-none" value={value}
            onChange={(e) => onChange(e.target.value)} {...rest}>
      {children}
    </select>
  );
}

export function EmptyState({ children = "Nothing here yet." }) {
  return <div className="py-12 text-center text-sm text-muted">{children}</div>;
}

export function Spinner({ className = "" }) {
  return (
    <span className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white ${className}`} />
  );
}

export function Card({ title, children, className = "" }) {
  return (
    <div className={`card p-4 ${className}`}>
      {title && <div className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">{title}</div>}
      {children}
    </div>
  );
}

/** Simple data table with sticky header */
export function Table({ columns, rows, empty }) {
  if (!rows || rows.length === 0) return <div className="card"><EmptyState>{empty}</EmptyState></div>;
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-separator">
              {columns.map((c, i) => (
                <th key={i} className="px-4 py-3 text-[11px] font-bold uppercase tracking-wide text-muted whitespace-nowrap">
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className="border-b border-separator/60 last:border-0 hover:bg-surface2/40">
                {columns.map((c, ci) => (
                  <td key={ci} className="px-4 py-3 align-middle text-ink2 whitespace-nowrap">
                    {c.cell ? c.cell(row) : row[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4"
         onClick={onClose}>
      <div className={`card max-h-[92vh] w-full overflow-y-auto rounded-b-none sm:rounded-xl2 ${wide ? "sm:max-w-4xl" : "sm:max-w-lg"}`}
           onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-separator bg-surface px-5 py-4">
          <h2 className="text-lg font-bold text-ink">{title}</h2>
          <button onClick={onClose} className="text-muted hover:text-ink text-xl leading-none">✕</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
