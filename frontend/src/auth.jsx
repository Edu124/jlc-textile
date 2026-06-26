import { createContext, useContext, useState } from "react";
import api from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("jlc_token") || "");

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
