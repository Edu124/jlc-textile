export function rupee(v) {
  v = Number(v) || 0;
  if (Math.abs(v) >= 100000) return `₹ ${(v / 100000).toFixed(2)}L`;
  if (Math.abs(v) >= 1000) return `₹ ${(v / 1000).toFixed(1)}K`;
  return `₹ ${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export function rupeeFull(v) {
  v = Number(v) || 0;
  return `₹ ${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function num(v, d = 0) {
  return (Number(v) || 0).toLocaleString("en-IN", { maximumFractionDigits: d });
}

export const STATUS_COLORS = {
  Received: "bg-accentSoft text-info",
  "In Production": "bg-warnSoft text-warn",
  Ready: "bg-okSoft text-ok",
  Dispatched: "bg-[#2E1A40] text-[#9B85B0]",
  "Partially Delivered": "bg-warnSoft text-warn",
  Delivered: "bg-okSoft text-ok",
  Cancelled: "bg-dangerSoft text-danger",
  Cutting: "bg-warnSoft text-warn",
  Stitching: "bg-accentSoft text-info",
  Dyeing: "bg-[#2E1A40] text-[#9B85B0]",
  Finishing: "bg-[#10303A] text-info",
  QC: "bg-warnSoft text-warn",
  Completed: "bg-okSoft text-ok",
  OK: "bg-okSoft text-ok",
  "Low Stock": "bg-dangerSoft text-danger",
};
