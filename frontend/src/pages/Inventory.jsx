import { useSearchParams } from "react-router-dom";
import RawMaterials from "./RawMaterials.jsx";
import Production from "./Production.jsx";
import FinishedGoods from "./FinishedGoods.jsx";

const TABS = [
  ["raw", "Raw Materials", RawMaterials],
  ["production", "Production", Production],
  ["finished", "Finished Goods", FinishedGoods],
];

export default function Inventory() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "raw";
  const active = TABS.find(([key]) => key === tab) || TABS[0];
  const Panel = active[2];

  return (
    <div>
      <div className="mb-5 flex gap-2 rounded-2xl bg-surface2 p-1.5">
        {TABS.map(([key, label]) => (
          <button key={key} onClick={() => setParams({ tab: key })}
            className={`min-h-[44px] flex-1 rounded-xl px-3 text-sm font-semibold transition
              ${key === active[0] ? "bg-accent text-white" : "text-ink3 hover:bg-surface3 hover:text-ink"}`}>
            {label}
          </button>
        ))}
      </div>
      <Panel />
    </div>
  );
}
