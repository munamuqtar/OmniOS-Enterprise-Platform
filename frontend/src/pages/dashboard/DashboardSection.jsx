import EmptyState from "../../components/common/EmptyState";
import StatusBadge from "../../components/common/StatusBadge";
import { formatDateTime, formatNumber, titleCase } from "../../utils/format";

const COLORS = ["#1a8cff", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#64748b"];

export function DonutChart({ items }) {
  const data = items.map(([key, value]) => [key, Number(value) || 0]);
  const total = data.reduce((sum, [, v]) => sum + v, 0);
  if (!total) return <EmptyState title="Nothing yet" />;
  const R = 52;
  const C = 2 * Math.PI * R;
  const arcs = data.reduce((acc, [key, value], i) => {
    const start = acc.length ? acc[acc.length - 1].end : 0;
    acc.push({ key, value, i, start, end: start + (value / total) * C });
    return acc;
  }, []);
  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 140 140" role="img" aria-label="Breakdown chart">
        <circle cx="70" cy="70" r={R} fill="none" stroke="#edf0f7" strokeWidth="18" />
        {arcs.filter((a) => a.value > 0).map((a) => (
          <circle key={a.key} cx="70" cy="70" r={R} fill="none" stroke={COLORS[a.i % COLORS.length]} strokeWidth="18"
                  strokeDasharray={`${a.end - a.start} ${C - (a.end - a.start)}`} strokeDashoffset={-a.start}
                  transform="rotate(-90 70 70)" />
        ))}
        <text x="70" y="68" textAnchor="middle" className="donut-total">{total}</text>
        <text x="70" y="85" textAnchor="middle" className="donut-label">total</text>
      </svg>
      <ul className="legend">
        {data.map(([key, value], i) => (
          <li key={key}><i style={{ background: COLORS[i % COLORS.length] }} /> {titleCase(key)} <b>{value}</b></li>
        ))}
      </ul>
    </div>
  );
}

function BarList({ items }) {
  const max = Math.max(1, ...items.map(([, v]) => Number(v) || 0));
  return (
    <ul className="bars">
      {items.map(([label, value]) => (
        <li key={label}>
          <span>{titleCase(label)}</span>
          <div className="bar"><i style={{ width: `${((Number(value) || 0) / max) * 100}%` }} /></div>
          <b>{formatNumber(value)}</b>
        </li>
      ))}
    </ul>
  );
}

function ProgressList({ rows }) {
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.id}>
          <span>{r.project_code} · {r.name}</span>
          <div className="bar"><i style={{ width: `${r.progress}%` }} /></div>
          <b>{r.progress}%</b>
        </li>
      ))}
    </ul>
  );
}

function ActivityList({ rows }) {
  return (
    <ul className="activity">
      {rows.map((r, i) => (
        <li key={i}>
          <strong>{r.user}</strong> {r.action.replace("_", " ")} <em>{r.record}</em>
          <small className="muted">{titleCase(r.module)} · {formatDateTime(r.at)}</small>
        </li>
      ))}
    </ul>
  );
}

function MiniTable({ rows }) {
  const keys = Object.keys(rows[0]);
  const cell = (k, v) => (k === "status" ? <StatusBadge status={v} /> : /total|amount|balance/.test(k) ? formatNumber(v) : String(v ?? "—"));
  return (
    <div className="table-scroll">
      <table>
        <thead><tr>{keys.map((k) => <th key={k}>{titleCase(k)}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{keys.map((k) => <td key={k}>{cell(k, r[k])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function Body({ data, variant }) {
  if (Array.isArray(data)) {
    if (!data.length) return <EmptyState title="Nothing yet" />;
    if (data[0].progress !== undefined) return <ProgressList rows={data} />;
    if (data[0].action && data[0].module) return <ActivityList rows={data} />;
    if (data[0].branch !== undefined && data[0].count !== undefined) return <BarList items={data.map((r) => [r.branch, r.count])} />;
    return <MiniTable rows={data} />;
  }
  if (data && typeof data === "object") {
    return variant === "donut" ? <DonutChart items={Object.entries(data)} /> : <BarList items={Object.entries(data)} />;
  }
  return <span>{String(data)}</span>;
}

export default function DashboardSection({ title, data, variant = "bars" }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      <Body data={data} variant={variant} />
    </section>
  );
}