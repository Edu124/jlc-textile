import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, Tooltip,
} from "recharts";
import { useFetch } from "../lib/useFetch.js";
import { rupee, num } from "../lib/format.js";
import { StatCard, Card, Badge, EmptyState } from "../components/ui.jsx";

const PIE = ["#5E7E9B", "#5FB07C", "#D9A45B", "#D9685F", "#7FA8B8", "#9B85B0"];

function HBars({ data, color = "#5E7E9B", fmt = num }) {
  if (!data || !data.length) return <EmptyState>No data yet</EmptyState>;
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-2.5">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="w-24 shrink-0 truncate text-right text-xs text-ink2">{d.label}</div>
          <div className="h-4 flex-1 rounded-full bg-surface2">
            <div className="h-4 rounded-full" style={{ width: `${(d.value / max) * 100}%`, background: color }} />
          </div>
          <div className="w-16 shrink-0 text-right text-xs font-semibold text-ink">{fmt(d.value)}</div>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { data: a } = useFetch("/api/dashboard/analytics");
  const { data: s } = useFetch("/api/dashboard/summary");

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Sales This Month" value={a ? rupee(a.month_sales) : "—"} icon="₹" accent="#5E7E9B" />
        <StatCard label="Pieces Sold" value={a ? num(a.month_qty) : "—"} icon="◷" accent="#7FA8B8" />
        <StatCard label="Orders This Month" value={a ? a.month_orders : "—"} icon="◎" accent="#D9A45B" />
        <StatCard label="Avg Order Value" value={a ? rupee(a.avg_order_value) : "—"} icon="⌀" accent="#5FB07C" />
      </div>

      <Card title="Sales — Last 30 Days">
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={a?.sales_trend || []}>
              <XAxis dataKey="label" tick={{ fill: "#8E8E93", fontSize: 10 }} interval={4} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#3A3A3C55" }}
                       contentStyle={{ background: "#2C2C2E", border: "1px solid #48484A", borderRadius: 10, color: "#F5F5F7" }}
                       formatter={(v) => rupee(v)} />
              <Bar dataKey="value" fill="#5E7E9B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
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

        <Card title="Size Mix (pieces sold)"><HBars data={a?.size_mix} color="#7FA8B8" /></Card>
        <Card title="Top Designs (by qty)"><HBars data={a?.top_designs} /></Card>
        <Card title="Top Customers (by ₹)"><HBars data={a?.top_customers} color="#5FB07C" fmt={rupee} /></Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="This Month — Money In vs Out">
          <HBars color="#5FB07C" fmt={rupee} data={a ? [
            { label: "Sales", value: a.month_sales },
            { label: "Purchases", value: a.month_purchases },
          ] : []} />
        </Card>
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
      </div>

      <Card title="Recent Orders">
        {s?.recent_orders?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="text-[11px] uppercase tracking-wide text-muted">
                <th className="py-2 pr-4">Order #</th><th className="pr-4">Customer</th>
                <th className="pr-4">Status</th><th className="pr-4">Amount</th><th>Date</th>
              </tr></thead>
              <tbody>
                {s.recent_orders.map((o, i) => (
                  <tr key={i} className="border-t border-separator/60">
                    <td className="py-2.5 pr-4 text-ink">{o.order_number}</td>
                    <td className="pr-4 text-ink2">{o.customer}</td>
                    <td className="pr-4"><Badge status={o.status} /></td>
                    <td className="pr-4 text-ink2">{rupee(o.total_amount)}</td>
                    <td className="text-muted">{o.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState>No orders yet</EmptyState>}
      </Card>
    </div>
  );
}
