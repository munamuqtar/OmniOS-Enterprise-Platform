import { LogOut, Menu } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { screenFor } from "../../app/screens";
import { useAuth } from "../../app/providers/auth-context";
import { displayName, initials, titleCase } from "../../utils/format";
import NotificationBell from "./NotificationBell";

export default function Navbar({ onMenu }) {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const screen = screenFor(pathname);

  return (
    <header className="navbar">
      <button className="icon-btn menu-btn" onClick={onMenu} aria-label="Open menu"><Menu size={20} /></button>
      <div className="crumbs">
        {screen?.group && <span className="muted">{screen.group} /</span>}
        <h1>{screen?.label ?? "OmniOS"}</h1>
      </div>
      <div className="spacer" />
      <NotificationBell />
      <div className="user-chip">
        <span className="avatar">{initials(user)}</span>
        <span className="user-meta">
          <strong>{displayName(user)}</strong>
          <small>{user.roles.map(titleCase).join(", ")}</small>
        </span>
      </div>
      <button className="btn btn-ghost sign-out" onClick={async () => { await logout(); navigate("/login"); }}>
        <LogOut size={16} /><span>Sign out</span>
      </button>
    </header>
  );
}