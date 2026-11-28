export const titleCase = (s) => String(s).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const formatNumber = (n) =>
  Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });

export const formatMoney = (amount, currency = "USD") =>
  `${currency} ${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;
export function formatDate(value) {
  if (!value) return "—";
  const m = DATE_ONLY.exec(value);
  const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(value);   // no timezone shift for plain dates
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export const formatDateTime = (value) =>
  value ? new Date(value).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" }) : "—";

/** Dashboard KPI values: plain numbers, decimal strings, or [{currency, amount}] lists. */
export function formatKpi(v) {
  if (Array.isArray(v)) return v.length ? v.map((r) => formatMoney(r.amount, r.currency)).join(" · ") : "0.00";
  if (v !== null && v !== "" && !Number.isNaN(Number(v))) return formatNumber(v);
  return String(v);
}


export function todayIso(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Value for <input type="datetime-local"> in the user's own time zone. */
export function nowLocalInput() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export const toIso = (localValue) => (localValue ? new Date(localValue).toISOString() : null);

export function greeting(date = new Date()) {
  const h = date.getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export const todayLong = (date = new Date()) =>
  date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });

export const currentYear = () => new Date().getFullYear();

export function displayName(user) {
  const full = `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim();
  return full || user?.username || "";
}

export function initials(user) {
  const parts = displayName(user).split(/\s+/).filter(Boolean);
  const letters = (parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "");
  return letters.toUpperCase() || "?";
}