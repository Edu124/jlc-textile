import { useState } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
} from "recharts";
import { useFetch, useAmountLock } from "../lib/useFetch.js";
import { rupee, num } from "../lib/format.js";
import { StatCard, Card, Badge, EmptyState, Modal, Spinner } from "../components/ui.jsx";

const PIE = ["#5E7E9B", "#5FB07C", "#D9A45B", "#D9685F", "#7FA8B8", "#9B85B0"];
const SIZES = [["s", "S"], ["m", "M"], ["l", "L"], ["xl", "XL"], ["xxl", "XXL"], ["xxxl", "3XL"], ["xxxxl", "4XL"], ["mxxl", "M-XXL"]];

export default function Dashboard() {
  const { data: a } = useFetch("/api/dashboard/analytics");
  const { data: s } = useFetch("/api/dashboard/summary");
  const { data: avail } = useFetch("/api/finished-goods/availability");
  const [designFor, setDesignFor] = useState(null);
  const [orderFor, setOrderFor] = useState(null);
  const [soldFor, setSoldFor] = useState(null);
  const { unlocked, unlock } = useAmountLock();

  const stockBars = (avail || [])
    .map((d) => ({ ...d, value: d.total_available }))
    .sort((x, y) => y.value - x.value).slice(0, 8);

  const soldBars = (avail || [])
    .filter((d) => d.total_sold > 0)
    .map((d) => ({ ...d, value: d.total_sold }))
    .sort((x, y) => y.value - x.value).slice(0, 10);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Pieces Sold (month)" value={a ? num(a.month_qty) : "—"} icon="◷" accent="#7FA8B8" />
        <StatCard label="Orders This Month" value={a ? a.month_orders : "—"} icon="◎" accent="#D9A45B" />
        <StatCard label="Finished Goods Qty" value={s ? num(s.finished_goods_qty) : "—"} icon="◼" accent="#5FB07C" />
      </div>

      <Card title="Designs & Stock — available pieces (tap a design for sizes)">
        {!stockBars.length ? <EmptyState>No finished-goods stock yet</EmptyState> : (
          <div className="space-y-2.5">
            {stockBars.map((d, i) => {
              const max = Math.max(...stockBars.map((x) => x.value), 1);
              return (
                <button key={i} onClick={() => setDesignFor(d)}
                  className="flex w-full items-center gap-3 rounded-lg px-1 py-0.5 text-left hover:bg-surface2">
                  <div className="w-28 shrink-0 truncate text-right text-xs text-accent">{d.name}</div>
                  <div className="h-4 flex-1 rounded-full bg-surface2">
                    <div className="h-4 rounded-full" style={{ width: `${(Math.max(d.value, 0) / max) * 100}%`, background: "#5FB07C" }} />
                  </div>
                  <div className="w-16 shrink-0 text-right text-xs font-semibold text-ink">{num(d.value, 0)}</div>
                </button>
              );
            })}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Orders by Status">
          {a?.order_status?.length ? (
            <div className="flex items-center gap-4">
              <div className="h-44 w-44">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={a.order_status} dataKey="value" nameKey="label" innerRadius={42} outerRadius={70} paddingAngle={2}>
                      {a.order_status.map((_, i) => <Cell key={i} fill={PIE[i % PIE.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#2C2C2E", border: "1px solid #48484A", borderRadius: 10 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex-1 space-y-1.5">
                {a.order_status.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="h-3 w-3 rounded" style={{ background: PIE[i % PIE.length] }} />
                    <span className="text-ink2">{d.label}</span>
                    <span className="ml-auto font-semibold text-ink">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <EmptyState>No orders yet</EmptyState>}
        </Card>

        <Card title="Designs Sold — tap a design to see which sizes sold">
          {!soldBars.length ? <EmptyState>Nothing sold yet</EmptyState> : (
            <div className="space-y-2.5">
              {soldBars.map((d, i) => {
                const max = Math.max(...soldBars.map((x) => x.value), 1);
                return (
                  <button key={i} onClick={() => setSoldFor(d)}
                    className="flex w-full items-center gap-3 rounded-lg px-1 py-0.5 text-left hover:bg-surface2">
                    <div className="w-28 shrink-0 truncate text-right text-xs text-accent">{d.name}</div>
                    <div className="h-4 flex-1 rounded-full bg-surface2">
                      <div className="h-4 rounded-full" style={{ width: `${(d.value / max) * 100}%`, background: "#7FA8B8" }} />
                    </div>
                    <div className="w-12 shrink-0 text-right text-xs font-semibold text-ink">{num(d.value, 0)}</div>
                  </button>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      <Card title="Low Stock Alerts">
        {s?.low_stock?.length ? (
          <div className="space-y-2">
            {s.low_stock.map((l, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-warnSoft px-3 py-2">
                <span className="text-sm font-semibold text-warn">{l.name}</span>
                <span className="text-xs text-muted">{num(l.quantity, 1)} / {num(l.threshold, 1)} {l.unit}</span>
              </div>
            ))}
          </div>
        ) : <div className="py-2 text-sm text-ok">All materials well stocked ✓</div>}
      </Card>

      <Card title="Recent Orders — tap to see delivered vs pending">
        {s?.recent_orders?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="text-[11px] uppercase tracking-wide text-muted">
                <th className="py-2 pr-4">Order #</th><th className="pr-4">Customer</th>
                <th className="pr-4">Status</th><th className="pr-4">Delivered</th><th className="pr-4">Amount</th><th>Date</th>
              </tr></thead>
              <tbody>
                {s.recent_orders.map((o, i) => (
                  <tr key={i} className="cursor-pointer border-t border-separator/60 hover:bg-surface2" onClick={() => setOrderFor(o)}>
                    <td className="py-2.5 pr-4 text-accent">{o.order_number}</td>
                    <td className="pr-4 text-ink2">{o.customer}</td>
                    <td className="pr-4"><Badge status={o.status} /></td>
                    <td className="pr-4 text-ink2">{num(o.delivered_qty, 0)} / {num(o.total_qty, 0)}</td>
                    <td className="pr-4 text-ink2">
                      {unlocked ? rupee(o.total_amount) : (
                        <button className="text-muted hover:text-accent"
                                onClick={(e) => { e.stopPropagation(); unlock(); }}>***</button>
                      )}
                    </td>
                    <td className="text-muted">{o.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState>No orders yet</EmptyState>}
      </Card>

      {designFor && <DesignStockModal design={designFor} onClose={() => setDesignFor(null)} />}
      {orderFor && <OrderDeliveryModal order={orderFor} onClose={() => setOrderFor(null)} />}
      {soldFor && <DesignSoldModal design={soldFor} onClose={() => setSoldFor(null)} />}
    </div>
  );
}

function DesignSoldModal({ design, onClose }) {
  const max = Math.max(...SIZES.map(([k]) => design.sold[k] || 0), 1);
  return (
    <Modal open onClose={onClose} title={`${design.name} — Sizes Sold`}>
      <div className="space-y-2.5">
        {SIZES.map(([k, lbl]) => (
          <div key={k} className="flex items-center gap-3">
            <div className="w-14 shrink-0 text-right text-xs text-ink2">{lbl}</div>
            <div className="h-4 flex-1 rounded-full bg-surface2">
              <div className="h-4 rounded-full" style={{ width: `${((design.sold[k] || 0) / max) * 100}%`, background: "#7FA8B8" }} />
            </div>
            <div className="w-10 shrink-0 text-right text-xs font-semibold text-ink">{num(design.sold[k] || 0, 0)}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 text-right text-sm text-muted">
        Total sold: <b className="text-ink">{num(design.total_sold, 0)}</b> pcs
      </div>
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

function DesignStockModal({ design, onClose }) {
  const row = (label, obj, color) => (
    <div className="flex items-center justify-between rounded-lg bg-surface2 px-3 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span className={`font-semibold ${color}`}>
        {SIZES.map(([k, l]) => `${l}:${num(obj[k] || 0, 0)}`).join("   ")}
      </span>
    </div>
  );
  return (
    <Modal open onClose={onClose} title={`${design.name} — Stock by Size`}>
      <div className="space-y-2">
        {row("Received", design.received, "text-ink")}
        {row("Sold", design.sold, "text-warn")}
        {row("Available", design.available, "text-ok")}
      </div>
      <div className="mt-3 text-right text-sm text-muted">
        Total available: <b className="text-ok">{num(design.total_available, 0)}</b> · sold: <b className="text-ink">{num(design.total_sold, 0)}</b>
      </div>
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

function OrderDeliveryModal({ order, onClose }) {
  const { data: detail, loading } = useFetch(`/api/orders/${order.id}`);
  const sizeStr = (it, prefix) => SIZES.filter(([k]) => (it[`qty_${k}`] || 0) > 0)
    .map(([k, l]) => `${l}:${num(it[`${prefix}${k}`] || 0, 0)}`).join("  ") || "—";

  return (
    <Modal open onClose={onClose} title={`${order.order_number} — Delivery Status`} wide>
      {loading || !detail ? <Spinner /> : (
        <div className="space-y-2">
          {detail.items.map((it) => {
            const pending = (it.quantity || 0) - (it.delivered_qty || 0);
            const done = pending <= 0 && it.quantity > 0;
            return (
              <div key={it.id} className="rounded-lg bg-surface2 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink">{it.design_no || it.product}</span>
                  <span className={done ? "text-sm font-semibold text-ok" : "text-sm font-semibold text-warn"}>
                    {done ? "Fully delivered" : `${num(pending, 0)} pending`}
                  </span>
                </div>
                <div className="mt-1 grid grid-cols-2 gap-2 text-xs">
                  <div className="text-muted">Delivered: <span className="text-ok">{sizeStr(it, "delivered_")}</span></div>
                  <div className="text-muted">Ordered: <span className="text-ink2">{sizeStr(it, "qty_")}</span></div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="mt-4 flex justify-end"><button className="btn-ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}
