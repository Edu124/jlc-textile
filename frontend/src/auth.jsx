import { createContext, useContext, useState, useEffect } from "react";
import api from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("jlc_token") || "");

  // Dev-only auto-login so local testing skips the login screen. Also enabled
  // in local production test builds via VITE_LOCAL_AUTOLOGIN=1 (never set on
  // Railway, so deployed builds always show the login screen).
  useEffect(() => {
    if ((import.meta.env.DEV || import.meta.env.VITE_LOCAL_AUTOLOGIN === "1") &&
        !localStorage.getItem("jlc_token")) {
      const form = new URLSearchParams({ username: "jailaxmi", password: "jlc@2026" });
      api.post("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      }).then(({ data }) => {
        localStorage.setItem("jlc_token", data.access_token);
        setToken(data.access_token);
      }).catch(() => {});
    }
  }, []);

  const login = async (username, password) => {
    const form = new URLSearchParams({ username, password });
    const { data } = await api.post("/api/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("jlc_token", data.access_token);
    setToken(data.access_token);
  };

  const logout = () => {
    localStorage.removeItem("jlc_token");
    setToken("");
  };

  return (
    <AuthCtx.Provider value={{ token, isAuthed: !!token, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
