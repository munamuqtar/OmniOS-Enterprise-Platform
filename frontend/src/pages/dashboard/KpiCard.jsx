import {
  Activity, Banknote, Building2, Clock, Flag, FolderKanban, FileText, Handshake, Hourglass,
  Layers, ListChecks, Receipt, Target, TrendingUp, Trophy, UserCheck, Users, Wallet,
} from "lucide-react";

// The first rule that matches the KPI's name decides its icon. The icons are created once, here,
// not while the component renders.
const RULES = [
  [/overdue/, Hourglass], [/won/, Trophy], [/lost/, Flag], [/employee/, Users], [/branch/, Building2],
  [/client/, Handshake], [/lead/, Target], [/opportunit/, TrendingUp], [/project/, FolderKanban],
  [/quotation|pending_approval/, FileText], [/invoice/, Receipt], [/outstanding|balance/, Wallet],
  [/payment|received/, Banknote], [/task/, ListChecks], [/timesheet|hours/, Clock], [/pipeline/, Layers],
  [/application|candidate|hired/, UserCheck],
];
const ICONS = RULES.map(([re, Icon]) => [re, <Icon size={22} />]);
const FALLBACK = <Activity size={22} />;
const iconFor = (name) => ICONS.find(([re]) => re.test(name))?.[1] ?? FALLBACK;

export default function KpiCard({ name, label, value, index = 0 }) {
  return (
    <div className={`kpi-card tone-${index % 6}`}>
      <span className="kpi-icon">{iconFor(name)}</span>
      <div className="kpi-body"><span>{label}</span><strong>{value}</strong></div>
    </div>
  );
}

export function KpiSkeleton() {
  return (
    <div className="kpi-grid" aria-busy="true" aria-label="Loading figures">
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i} className="kpi-card skeleton">
          <span className="kpi-icon" />
          <div className="kpi-body"><span /><strong /></div>
        </div>
      ))}
    </div>
  );
}