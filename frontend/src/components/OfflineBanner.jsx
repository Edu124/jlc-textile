import { useEffect, useState } from "react";
import { queueCount, flushQueue } from "../lib/offline.js";

// Slim strip under the header: shows when the tablet is offline and/or when
// entries are waiting to sync. Disappears once everything is up to date.
export default function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);
  const [pending, setPending] = useState(queueCount());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    const onQueue = (e) => setPending(e.detail?.count ?? queueCount());
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    window.addEventListener("jlc-queue-changed", onQueue);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
      window.removeEventListener("jlc-queue-changed", onQueue);
    };
  }, []);

  const syncNow = async () => {
    setBusy(true);
    try { await flushQueue(); } finally { setBusy(false); setPending(queueCount()); }
  };

  if (online && pending === 0) return null;

  return (
    <div className={`flex items-center gap-3 px-4 py-2 text-sm md:px-6
                     ${online ? "bg-amber-500/15 text-amber-300" : "bg-red-500/15 text-red-300"}`}>
      <span className="text-base">{online ? "⟳" : "⚠"}</span>
      {!online ? (
        <span>
          No internet — you can still view stock and create order forms, visiting cards
          and direct entries. They will sync automatically when the connection returns.
          {pending > 0 && <b> {pending} waiting to sync.</b>}
        </span>
      ) : (
        <span><b>{pending}</b> offline {pending === 1 ? "entry" : "entries"} waiting to sync.</span>
      )}
      {online && pending > 0 && (
        <button onClick={syncNow} disabled={busy}
                className="ml-auto rounded-lg border border-amber-400/40 px-3 py-1 text-xs font-semibold hover:bg-amber-500/20 disabled:opacity-50">
          {busy ? "Syncing…" : "Sync now"}
        </button>
      )}
    </div>
  );
}
