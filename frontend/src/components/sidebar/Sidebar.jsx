import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Activity, ChevronDown, FolderKanban, Layers, LayoutDashboard, Settings, Target, TrendingUp, Users, Wallet } from "lucide-react";
import { SCREENS, screenFor } from "../../app/screens";
import { useAuth } from "../../app/providers/auth-context";
import { displayName, initials, titleCase } from "../../utils/format";
import Logo from "../common/Logo";

const GROUP_ICONS = {
  HR: Users, CRM: Target, Sales: TrendingUp, Projects: FolderKanban,
  Finance: Wallet, Settings, System: Activity,
};

export default function Sidebar({ open, onNavigate }) {
  const { user, hasRole } = useAuth();
  const { pathname } = useLocation();
  const [toggled, setToggled] = useState({});            // groups the user opened or closed by hand
  const activeGroup = screenFor(pathname)?.group;

  const visible = SCREENS.filter((s) => !s.roles || hasRole(...s.roles));
  const topLevel = visible.filter((s) => !s.group);
  const groups = [];
  visible.filter((s) => s.group).forEach((s) => {
    let g = groups.find((x) => x.name === s.group);
    if (!g) { g = { name: s.group, items: [] }; groups.push(g); }
    g.items.push(s);
  });

  const isOpen = (name) => toggled[name] ?? name === activeGroup;
  const toggle = (name) => setToggled((t) => ({ ...t, [name]: !(t[name] ?? name === activeGroup) }));

  return (
    <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-brand"><Logo className="sidebar-logo" height={40} /></div>
      <nav>
        {topLevel.map((s) => (
          <NavLink key={s.path} to={s.path} onClick={onNavigate}
                   className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            <LayoutDashboard size={18} aria-hidden="true" />
            <span>{s.label}</span>
          </NavLink>
        ))}
        {groups.map((g) => {
          const GroupIcon = GROUP_ICONS[g.name] ?? Layers;
          const expanded = isOpen(g.name);
          const id = `nav-${g.name.toLowerCase()}`;
          return (
            <div key={g.name} className={`nav-group ${expanded ? "open" : ""} ${g.name === activeGroup ? "current" : ""}`}>
              <button type="button" className="nav-group-btn" aria-expanded={expanded} aria-controls={id}
                      onClick={() => toggle(g.name)}>
                <GroupIcon size={18} aria-hidden="true" />
                <span>{g.name}</span>
                <ChevronDown size={16} className="chev" aria-hidden="true" />
              </button>
              <div id={id} className="nav-sub">
                <div>
                  {g.items.map((s) => (
                    <NavLink key={s.path} to={s.path} onClick={onNavigate}
                             className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                      <span>{s.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <span className="avatar sm">{initials(user)}</span>
        <div><strong>{displayName(user)}</strong><small>{user.roles.map(titleCase).join(", ")}</small></div>
      </div>
    </aside>
  );
}