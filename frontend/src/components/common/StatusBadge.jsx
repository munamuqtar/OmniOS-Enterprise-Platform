import { titleCase } from "../../utils/format";

const TONES = {
  green: ["active", "approved", "paid", "completed", "won", "qualified", "converted", "confirmed", "reconciled", "hired", "open", "closed_won"],
  blue: ["issued", "in_progress", "contacted", "planned", "interview", "screening", "qualification", "proposal", "negotiation"],
  amber: ["pending", "pending_approval", "submitted", "review", "partially_paid", "on_hold", "evaluation", "offered", "on_leave"],
  red: ["rejected", "overdue", "cancelled", "lost", "unqualified", "terminated", "suspended"],
};

const toneOf = (status) =>
  Object.entries(TONES).find(([, list]) => list.includes(status))?.[0] ?? "gray";

export default function StatusBadge({ status }) {
  if (!status) return null;
  return <span className={`badge ${toneOf(status)}`}>{titleCase(status)}</span>;
}