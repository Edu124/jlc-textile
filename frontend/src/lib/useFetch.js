import { useCallback, useEffect, useState } from "react";
import api from "../api";

export function useFetch(path, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
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
