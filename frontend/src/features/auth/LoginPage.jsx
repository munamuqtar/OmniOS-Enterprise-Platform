import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../../app/providers/auth-context";
import { parseApiError } from "../../utils/errors";
import { currentYear } from "../../utils/format";
import ErrorBanner from "../../components/common/ErrorBanner";
import Logo from "../../components/common/Logo";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [show, setShow] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/dashboard" replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.username.trim(), form.password);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <main className="auth-stack">
        <Logo className="auth-logo" height={56} />
        <form className="auth-form" onSubmit={submit}>
          <h1>Welcome Back</h1>
          <p className="muted">Please login to your account</p>
          <ErrorBanner message={error} />

          <label className="sr-only" htmlFor="username">Username</label>
          <input id="username" className="auth-input" placeholder="Username" autoComplete="username" required autoFocus
                 value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />

          <label className="sr-only" htmlFor="password">Password</label>
          <div className="auth-pw">
            <input id="password" className="auth-input" placeholder="Password" type={show ? "text" : "password"}
                   autoComplete="current-password" required value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <button type="button" className="auth-eye" title={show ? "Hide password" : "Show password"}
                    aria-pressed={show} onClick={() => setShow((s) => !s)}>
              {show ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
            </button>
          </div>

          <div className="auth-row">
            <button type="button" className="auth-link" aria-expanded={forgot} onClick={() => setForgot((f) => !f)}>
              Forgot password?
            </button>
          </div>
          {forgot && (
            <p className="auth-help" role="note">
              Passwords are reset by your administrator. Ask a Super Admin to set a new one for you in Settings, Users.
            </p>
          )}

          <button className="auth-submit" disabled={busy}>{busy ? "Logging in…" : "Login"}</button>
        </form>
        <small className="auth-foot">© {currentYear()} Omni Teckno</small>
      </main>
    </div>
  );
}