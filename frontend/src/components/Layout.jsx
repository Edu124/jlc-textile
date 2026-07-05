import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import PdfPreviewHost from "./PdfPreview.jsx";

const NAV = [
  { section: "" , items: [
    ["Dashboard", "/", "⊞"],
    ["Inventory", "/inventory", "◈"],
  ]},
  { section: "Commerce", items: [
    ["Order Forms", "/sales", "↑"],
    ["Purchases", "/purchases", "↓"],
  ]},
  { section: "Masters", items: [
    ["Suppliers", "/suppliers", "◷"],
    ["Customers", "/customers", "◶"],
    ["Visiting Cards", "/visiting-cards", "▣"],
    ["Units", "/units", "◫"],
  ]},
  { section: "Tools", items: [
    ["AI Studio", "/ai", "✦"],
    ["Reports", "/reports", "≡"],
    ["Settings", "/settings", "⚙"],
    ["Import Customers", "/import-customers", "⬆"],
  ]},
];

const TITLES = Object.fromEntries(
  NAV.flatMap((g) => g.items).map(([label, path]) => [path, label])
);

export default function Layout() {
  const [open, setOpen] = useState(true);     // sidebar expanded?
  const [mobileOpen, setMobileOpen] = useState(false);
  const { logout } = useAuth();
  const loc = useLocation();
  const title = TITLES[loc.pathname] || "JLC";

  const Sidebar = (
    <aside className={`flex h-full flex-col bg-sidebar border-r border-separator transition-all duration-200
                       ${open ? "w-60" : "w-[68px]"}`}>
      <div className="flex h-16 items-center gap-2 border-b border-separator px-4">
        <button onClick={() => setOpen(!open)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-ink3 hover:bg-surface2 hover:text-ink">
          ☰
        </button>
        {open && (
          <div className="leading-tight">
            <div className="text-[15px] font-extrabold tracking-wider text-ink">JLC</div>
            <div className="text-[9px] tracking-widest text-muted">TEXTILE MANAGER</div>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {NAV.map((group, gi) => (
          <div key={gi}>
            {open && group.section && (
              <div className="px-5 pb-1 pt-4 text-[10px] font-bold uppercase tracking-wider text-muted">
                {group.section}
              </div>
            )}
            {group.items.map(([label, path, icon]) => (
              <NavLink key={path} to={path} end={path === "/"}
                onClick={() => setMobileOpen(false)}
                title={label}
                className={({ isActive }) =>
                  `mx-2 my-0.5 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition
                   ${isActive ? "bg-accent text-white font-semibold"
                              : "text-ink3 hover:bg-surface2 hover:text-ink"}`}>
                <span className="w-5 shrink-0 text-center text-base">{icon}</span>
                {open && <span className="truncate">{label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <button onClick={logout}
              className="m-2 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink3 hover:bg-surface2 hover:text-ink">
        <span className="w-5 text-center">⏻</span>{open && "Log out"}
      </button>
    </aside>
  );

  return (
    <div className="flex h-full">
      {/* Desktop / tablet sidebar */}
      <div className="hidden md:block">{Sidebar}</div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full">{Sidebar}</div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-separator bg-bg px-4 md:px-6">
          <button className="md:hidden text-ink3" onClick={() => setMobileOpen(true)}>☰</button>
          <h1 className="text-lg font-extrabold text-ink">{title}</h1>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto bg-bg p-4 md:p-6">
          <Outlet />
          <PdfPreviewHost />
        </main>
      </div>
    </div>
  );
}
