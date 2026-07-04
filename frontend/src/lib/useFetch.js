import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api";

export function useFetch(path, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!path) { setLoading(false); return; }
    setLoading(true);
    try {
      const { data } = await api.get(path);
      setData(data);
      setError("");
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, deps);

  return { data, loading, error, reload, setData };
}

export function apiError(e) {
  return e?.response?.data?.detail || e?.message || "Something went wrong";
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1]);
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

// Inside the Android app the WebView can't open or download blob files — hand
// the file to the native shell instead, which opens the share/save sheet.
async function sendToApp(blob, filename, mime) {
  const base64 = await blobToBase64(blob);
  window.ReactNativeWebView.postMessage(JSON.stringify({ type: "save-file", filename, mime, base64 }));
}

// window.open(path) can't carry the Bearer auth header, so the API 401s
// silently. Fetch the PDF as a blob (with auth) and open that instead.
export async function openPdf(path, filename = "order-form.pdf") {
  const res = await api.get(path, { responseType: "blob" });
  const blob = new Blob([res.data], { type: "application/pdf" });
  if (window.ReactNativeWebView) return sendToApp(blob, filename, "application/pdf");
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
}

// Amounts are hidden behind a PIN (stored in Settings). Unlocking reveals them
// briefly, then they re-mask to *** automatically.
const RELOCK_MS = 30_000;

export function useAmountLock() {
  const [unlocked, setUnlocked] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  const unlock = async () => {
    const pin = window.prompt("Enter PIN to view amounts");
    if (pin === null) return false;
    try {
      const { data } = await api.post("/api/settings/verify-pin", { pin });
      if (data.ok) {
        setUnlocked(true);
        clearTimeout(timer.current);
        timer.current = setTimeout(() => setUnlocked(false), RELOCK_MS);
        return true;
      }
    } catch { /* fall through */ }
    alert("Wrong PIN");
    return false;
  };
  return { unlocked, unlock };
}

// Same auth problem for any authenticated file download — fetch as a blob
// and trigger a save via a temporary <a download>.
export async function downloadFile(path, filename) {
  const res = await api.get(path, { responseType: "blob" });
  if (window.ReactNativeWebView)
    return sendToApp(res.data, filename, res.data.type || "application/octet-stream");
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
