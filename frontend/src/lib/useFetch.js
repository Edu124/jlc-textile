import { useCallback, useEffect, useState } from "react";
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

// window.open(path) can't carry the Bearer auth header, so the API 401s
// silently. Fetch the PDF as a blob (with auth) and open that instead.
export async function openPdf(path) {
  const res = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  window.open(url, "_blank");
}

// Same auth problem for any authenticated file download — fetch as a blob
// and trigger a save via a temporary <a download>.
export async function downloadFile(path, filename) {
  const res = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
