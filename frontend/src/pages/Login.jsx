import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Spinner } from "../components/ui.jsx";

export default function Login() {
  const { login, isAuthed } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (isAuthed) { nav("/", { replace: true }); return null; }

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await login(u.trim(), p);
      nav("/", { replace: true });
    } catch {
      setErr("Invalid username or password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm p-8">
        <div className="mb-6 text-center">
          <div className="text-2xl font-extrabold tracking-wider text-ink">JLC</div>
          <div className="text-xs tracking-widest text-muted">TEXTILE MANAGER</div>
        </div>
        <label className="label">Username</label>
        <input className="input mb-4" value={u} onChange={(e) => setU(e.target.value)}
               autoFocus autoCapitalize="none" placeholder="jailaxmi" />
        <label className="label">Password</label>
        <input className="input mb-5" type="password" value={p}
               onChange={(e) => setP(e.target.value)} placeholder="••••••••" />
        {err && <div className="mb-4 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? <Spinner /> : "Sign in"}
        </button>
      </form>
    </div>
  );
}
