import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Clock, FolderKanban, ListChecks } from "lucide-react";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useBranchOptions } from "../../hooks/useBranchOptions";
import { parseApiError } from "../../utils/errors";
import { displayName, formatKpi, greeting, titleCase, todayLong } from "../../utils/format";
import ErrorBanner from "../../components/common/ErrorBanner";
import KpiCard, { KpiSkeleton } from "./KpiCard";
import DashboardSection from "./DashboardSection";

const DASHBOARDS = [
  { key: "executive", label: "Executive", endpoint: "/dashboard/executive/", roles: [] },
  { key: "hr", label: "HR", endpoint: "/dashboard/hr/", roles: ["hr"] },
  { key: "sales", label: "Sales", endpoint: "/dashboard/sales/", roles: ["sales"] },
  { key: "projects", label: "Projects", endpoint: "/dashboard/projects/", roles: ["project_manager"] },
  { key: "finance", label: "Finance", endpoint: "/dashboard/finance/", roles: ["finance"] },
];

// Status breakdowns are drawn as donuts. Money-by-stage stays a bar list.
const variantFor = (key) => (/(by_status|by_stage|pipeline|reconciliation_status)$/.test(key) && !/value/.test(key) ? "donut" : "bars");

function DashboardView({ endpoint, branch }) {
  const q = useQuery({
    queryKey: ["dashboard", endpoint, branch],
    queryFn: async () => unwrap(await api.get(endpoint, { params: branch ? { branch } : {} })),
    refetchInterval: 30000,          // dashboards stay live
    refetchOnWindowFocus: true,
  });
  if (q.isLoading) return <KpiSkeleton />;
  if (q.error) return <ErrorBanner message={parseApiError(q.error).message} onRetry={q.refetch} />;
  const { kpis, ...sections } = q.data;
  return (
    <>
      <div className="kpi-grid">
        {Object.entries(kpis).map(([k, v], i) => (
          <KpiCard key={k} name={k} index={i} label={titleCase(k)} value={formatKpi(v)} />
        ))}
      </div>
      <div className="section-grid">
        {Object.entries(sections).map(([k, v]) => (
          <DashboardSection key={k} title={titleCase(k)} data={v} variant={variantFor(k)} />
        ))}
      </div>
    </>
  );
}

function EmployeeHome({ user }) {
  const links = [
    ["/tasks", ListChecks, "My tasks", "Update progress on your assigned work"],
    ["/timesheets", Clock, "My timesheets", "Log hours and track approvals"],
    ["/projects", FolderKanban, "My projects", "See the projects you belong to"],
  ];
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">{todayLong()}</span>
          <h2>{greeting()}, {displayName(user)}</h2>
          <p className="muted">Your work at a glance.</p>
        </div>
      </section>
      <div className="kpi-grid">
        {links.map(([to, Icon, title, text], i) => (
          <Link key={to} to={to} className={`kpi-card link-card tone-${i}`}>
            <span className="kpi-icon"><Icon size={22} /></span>
            <div className="kpi-body"><strong className="small">{title}</strong><span>{text}</span></div>
          </Link>
        ))}
      </div>
    </>
  );
}

export default function DashboardPage() {
  const { user, hasRole } = useAuth();
  const available = DASHBOARDS.filter((d) => hasRole(...d.roles));
  const [activeKey, setActiveKey] = useState(available[0]?.key);
  const [branch, setBranch] = useState("");
  const branches = useBranchOptions();

  if (!available.length) return <EmployeeHome user={user} />;
  const active = available.find((d) => d.key === activeKey) ?? available[0];
  const branchName = branches.find((b) => b.id === branch)?.name;

  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">{todayLong()}</span>
          <h2>{greeting()}, {displayName(user)}</h2>
          <p className="muted">{active.label} overview for {branchName ?? (branches.length > 1 ? "all your branches" : "your branch")}. Figures update live.</p>
        </div>
        {branches.length > 1 && (
          <select className="input" aria-label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)}>
            <option value="">All branches</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        )}
      </section>
      {available.length > 1 && (
        <div className="tabs seg" role="tablist">
          {available.map((d) => (
            <button key={d.key} role="tab" aria-selected={d.key === active.key}
                    className={`tab ${d.key === active.key ? "active" : ""}`} onClick={() => setActiveKey(d.key)}>
              {d.label}
            </button>
          ))}
        </div>
      )}
      <DashboardView key={`${active.key}-${branch}`} endpoint={active.endpoint} branch={branch} />
    </>
  );
}