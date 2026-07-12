// Offline write queue. When a save fails because there is no internet, the
// request is stored in localStorage and replayed (oldest first) as soon as
// the connection returns. Single-device assumption: the tablet is the only
// writer while offline.
import api from "../api";

const KEY = "jlc_queue";
const FAILED_KEY = "jlc_queue_failed";

export function isNetworkError(e) {
  // Axios: no response object = the request never reached the server.
  // A 503 {"detail":"offline"} is the service worker's offline fallback.
  return !e?.response || (e.response.status === 503 && e.response.data?.detail === "offline");
}

export function getQueue() {
  try { return JSON.parse(localStorage.getItem(KEY)) || []; }
  catch { return []; }
}

function setQueue(q) {
  localStorage.setItem(KEY, JSON.stringify(q));
  window.dispatchEvent(new CustomEvent("jlc-queue-changed", { detail: { count: q.length } }));
}

export function queueCount() { return getQueue().length; }

// Returns the entry's queue id (usable as a "local:<id>" reference) or false.
// `label` is shown in the banner tooltip/summary.
export function queueRequest({ method = "post", url, body, label = "" }) {
  const entry = { id: Date.now() + "-" + Math.random().toString(36).slice(2, 7),
                  ts: new Date().toISOString(), method, url, body, label };
  const q = getQueue();
  q.push(entry);
  const done = () => {
    // If we're actually online (queued only because of a local reference),
    // sync right away instead of waiting for the interval.
    if (navigator.onLine) setTimeout(() => { flushQueue(); }, 500);
    return entry.id;
  };
  try {
    setQueue(q);
    return done();
  } catch {
    // localStorage quota (usually a big photo) — retry without the image.
    if (body && (body.image_base64 || body.image)) {
      const slim = { ...body }; delete slim.image_base64; delete slim.image;
      entry.body = slim; entry.label = (label || "") + " (photo dropped — too large to store offline)";
      try { setQueue([...getQueue(), entry]); return done(); } catch { return false; }
    }
    return false;
  }
}

let flushing = false;

// ── Local references ──────────────────────────────────────────────────────────
// A record created offline gets a temporary id like "local:<queue-id>", so
// later offline entries can point at it (an order form for a customer whose
// visiting card was scanned minutes earlier, both with no signal). During
// sync the queue replays in order, and each synced entry's REAL server id is
// substituted into everything that referenced its local id.
const IDMAP_KEY = "jlc_queue_idmap";

const getIdMap = () => {
  try { return JSON.parse(localStorage.getItem(IDMAP_KEY)) || {}; }
  catch { return {}; }
};

function resolveLocals(value, map) {
  if (typeof value === "string" && value.startsWith("local:")) {
    const real = map[value.slice(6)];
    return real !== undefined ? real : value;
  }
  if (Array.isArray(value)) return value.map((v) => resolveLocals(v, map));
  if (value && typeof value === "object")
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, resolveLocals(v, map)]));
  return value;
}

// Offline customers (scanned visiting cards etc.) that haven't synced yet —
// shown in the Customers list and the order-form Party dropdown with their
// temporary "local:" id.
export function pendingCustomers() {
  return getQueue().filter((e) => e.url === "/api/customers").map((e) => ({
    id: `local:${e.id}`, name: e.body?.name || "", phone: e.body?.phone || "",
    email: e.body?.email || "", gst_number: e.body?.gst_number || "",
    address: e.body?.address || "", pending: true,
  }));
}

// Order forms saved offline & waiting to sync — shown at the top of the
// Order Forms list so nothing "disappears" while there's no signal.
export function pendingOrderForms() {
  return getQueue().filter((e) => e.url === "/api/sales").map((e) => {
    const items = e.body?.items || [];
    const qty = items.reduce((a, it) =>
      a + Object.entries(it).reduce((s, [k, v]) => (k.startsWith("qty_") ? s + (Number(v) || 0) : s), 0), 0);
    return {
      id: `local:${e.id}`, qid: e.id, pending: true,
      bill_number: "offline", reference_no: e.body?.reference_no || "",
      bill_date: e.body?.bill_date || (e.ts || "").slice(0, 10),
      customer: (e.label || "").replace(/^Order form\s*(—\s*)?/, "") || "—",
      designs: items.map((i) => i.design_no).filter(Boolean).join(", "),
      total_qty: qty, total_amount: 0,
      items,   // per-size detail for the Pending Deliveries board
    };
  });
}

// Drop a not-yet-synced entry (the only way to "delete" an offline save).
export function removeQueued(qid) {
  setQueue(getQueue().filter((e) => e.id !== qid));
}

// Replays the queue in order. Stops at the first network failure (still
// offline); server rejections (validation etc.) are moved aside so one bad
// entry can't block the rest forever.
export async function flushQueue() {
  if (flushing) return { synced: 0, failed: 0, remaining: queueCount() };
  flushing = true;
  let synced = 0, failed = 0;
  try {
    let q = getQueue();
    while (q.length) {
      const item = q[0];
      const map = getIdMap();
      const body = resolveLocals(item.body, map);
      try {
        // A leftover "local:" means the entry it depended on failed to sync.
        if (JSON.stringify(body ?? {}).includes('"local:')) {
          const err = new Error("depends on an entry that failed to sync");
          err.response = { data: { detail: err.message } };
          throw err;
        }
        const res = await api.request({ method: item.method, url: item.url, data: body });
        if (res?.data?.id !== undefined) {
          map[item.id] = res.data.id;
          try { localStorage.setItem(IDMAP_KEY, JSON.stringify(map)); } catch { /* best effort */ }
        }
        synced++;
      } catch (e) {
        if (isNetworkError(e)) break;   // still offline — try again later
        // Server said no (bad data, deleted design, ...) — set aside, move on.
        failed++;
        try {
          const f = JSON.parse(localStorage.getItem(FAILED_KEY)) || [];
          f.push({ ...item, error: e?.response?.data?.detail || String(e) });
          localStorage.setItem(FAILED_KEY, JSON.stringify(f.slice(-20)));
        } catch { /* best effort */ }
      }
      q = getQueue().filter((x) => x.id !== item.id);
      setQueue(q);
    }
    if (queueCount() === 0) {
      try { localStorage.removeItem(IDMAP_KEY); } catch { /* done syncing */ }
    }
  } finally {
    flushing = false;
  }
  return { synced, failed, remaining: queueCount() };
}

// The lists the client needs to SEE offline (customers, stock, order forms…).
// Fetching them once per app start routes them through the service worker,
// which keeps the freshest copy for offline viewing — even if the user never
// opens those pages while online.
const WARM_URLS = [
  "/api/customers",
  "/api/products",              // design list inside the order form
  "/api/finished-goods",
  "/api/finished-goods/availability",
  "/api/sales",
  "/api/sales/pending",
  "/api/dashboard/summary",
  "/api/dashboard/analytics",
  "/api/raw-materials",
  "/api/production/tailors",
  "/api/suppliers",
  "/api/units",
  "/api/settings",
];

export function warmOfflineCache() {
  if (!navigator.onLine || !localStorage.getItem("jlc_token")) return;
  WARM_URLS.forEach((u) => api.get(u).catch(() => {}));
}

// Wire up auto-sync: on regaining connection, on app load, and every 20s
// while anything is pending (belt and braces for flaky connections).
export function initOfflineSync() {
  window.addEventListener("online", () => { flushQueue().then(warmOfflineCache); });
  setInterval(() => { if (navigator.onLine && queueCount() > 0) flushQueue(); }, 20_000);
  if (navigator.onLine && queueCount() > 0) setTimeout(flushQueue, 3_000);
  setTimeout(warmOfflineCache, 4_000);   // snapshot the key lists for offline
}
