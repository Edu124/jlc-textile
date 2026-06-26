import { useState } from "react";
import { useFetch } from "../lib/useFetch.js";
import { rupeeFull, num } from "../lib/format.js";
import { PageHeader, Table, Badge, Card } from "../components/ui.jsx";

const TABS = ["Raw Materials", "Finished Goods", "Sales", "Purchases", "Orders", "Production"];

export default function Reports() {
  const [tab, setTab] = useState("Raw Materials");
  const { data: raw } = useFetch("/api/raw-materials");
  const { data: fg } = useFetch("/api/finished-goods");
  const { data: sales } = useFetch("/api/sales");
  const { data: purchases } = useFetch("/api/purchases");
  const { data: orders } = useFetch("/api/orders");
  const { data: production } = useFetch("/api/production");

  return (
    <div>
      <PageHeader title="Reports" />
      <div className="mb-4 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`rounded-xl px-4 py-2 text-sm font-medium ${tab === t ? "bg-surface2 text-ink" : "text-ink3 hover:text-ink"}`}>{t}</button>
        ))}
      </div>

      {tab === "Raw Materials" && (
        <Table empty="No materials" rows={raw} columns={[
          { header: "Material", key: "name" }, { header: "Unit", key: "unit" },
          { header: "In Stock", cell: (r) => num(r.quantity, 2) },
          { header: "Avg Rate", cell: (r) => rupeeFull(r.avg_rate) },
          { header: "Value", cell: (r) => rupeeFull(r.value) },
          { header: "Status", cell: (r) => <Badge status={r.status} /> },
        ]} />
      )}
      {tab === "Finished Goods" && (
        <Table empty="No products" rows={fg} columns={[
          { header: "Product", key: "name" }, { header: "Category", key: "category" },
          { header: "In Stock", cell: (r) => num(r.quantity, 2) },
          { header: "Sale Rate", cell: (r) => rupeeFull(r.sale_rate) },
          { header: "Value", cell: (r) => rupeeFull(r.value) },
        ]} />
      )}
      {tab === "Sales" && (<>
        <Card className="mb-3 text-sm text-ink2">
          {sales?.length || 0} order forms &nbsp;|&nbsp; Total: {rupeeFull((sales || []).reduce((a, b) => a + b.total_amount, 0))}
        </Card>
        <Table empty="No sales" rows={sales} columns={[
          { header: "Bill No", key: "bill_number" }, { header: "Date", key: "bill_date" },
          { header: "Party", key: "customer" }, { header: "Qty", cell: (r) => num(r.total_qty) },
          { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
        ]} /></>
      )}
      {tab === "Purchases" && (<>
        <Card className="mb-3 text-sm text-ink2">
          {purchases?.length || 0} bills &nbsp;|&nbsp; Total: {rupeeFull((purchases || []).reduce((a, b) => a + b.total_amount, 0))}
        </Card>
        <Table empty="No purchases" rows={purchases} columns={[
          { header: "Bill No", key: "bill_number" }, { header: "Date", key: "bill_date" },
          { header: "Supplier", key: "supplier" }, { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
        ]} /></>
      )}
      {tab === "Orders" && (
        <Table empty="No orders" rows={orders} columns={[
          { header: "Order #", key: "order_number" }, { header: "Customer", key: "customer" },
          { header: "Total", cell: (r) => rupeeFull(r.total_amount) },
          { header: "Status", cell: (r) => <Badge status={r.status} /> },
          { header: "Delivery", cell: (r) => r.delivery_date || "—" },
        ]} />
      )}
      {tab === "Production" && (
        <Table empty="No batches" rows={production} columns={[
          { header: "Batch #", key: "batch_number" }, { header: "Product", key: "product" },
          { header: "Qty", cell: (r) => num(r.quantity) },
          { header: "Stage", cell: (r) => <Badge status={r.current_stage} /> },
          { header: "Started", cell: (r) => (r.started_at || "").slice(0, 10) },
        ]} />
      )}
    </div>
  );
}
