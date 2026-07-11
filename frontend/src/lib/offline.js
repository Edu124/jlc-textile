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

// Returns true if queued. `label` is shown in the banner tooltip/summary.
export function queueRequest({ method = "post", url, body, label = "" }) {
  const entry = { id: Date.now() + "-" + Math.random().toString(36).slice(2, 7),
                  ts: new Date().toISOString(), method, url, body, label };
  const q = getQueue();
  q.push(entry);
  try {
    setQueue(q);
    return true;
  } catch {
    // localStorage quota (usually a big photo) — retry without the image.
    if (body && (body.image_base64 || body.image)) {
      const slim = { ...body }; delete slim.image_base64; delete slim.image;
      entry.body = slim; entry.label = (label || "") + " (photo dropped — too large to store offline)";
      try { setQueue([...getQueue(), entry]); return true; } catch { return false; }
    }
    return false;
  }
}

let flushing = false;

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
      try {
        await api.request({ method: item.method, url: item.url, data: item.body });
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
  } finally {
    flushing = false;
  }
  return { synced, failed, remaining: queueCount() };
}

// Wire up auto-sync: on regaining connection, on app load, and every 20s
// while anything is pending (belt and braces for flaky connections).
export function initOfflineSync() {
  window.addEventListener("online", () => { flushQueue(); });
  setInterval(() => { if (navigator.onLine && queueCount() > 0) flushQueue(); }, 20_000);
  if (navigator.onLine && queueCount() > 0) setTimeout(flushQueue, 3_000);
}
