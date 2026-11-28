export const PROJECT_NEXT = {
  draft: ["planned", "cancelled"],
  planned: ["active", "on_hold", "cancelled"],
  active: ["on_hold", "completed", "cancelled"],
  on_hold: ["active", "cancelled"],
  completed: [],
  cancelled: [],
};

export const TASK_NEXT = {
  todo: ["in_progress"],
  in_progress: ["todo", "review"],
  review: ["in_progress", "completed"],
  completed: ["in_progress"],
};

/** Employees can move their own work around, but only a project manager can complete or reopen a task. */
export function taskMoves(status, isManager) {
  return (TASK_NEXT[status] ?? []).filter((s) => isManager || (s !== "completed" && status !== "completed"));
}

export const PAYMENT_ACTIONS = {
  pending: ["confirm", "reject"],
  confirmed: ["reconcile", "reject"],
  reconciled: [],
  rejected: [],
};

/** Invoice lines are grouped per task, exactly like the server does. */
export function groupHoursByTask(rows) {
  const map = new Map();
  rows.forEach((r) => map.set(r.task_id, (map.get(r.task_id) ?? 0) + Number(r.hours)));
  return [...map].map(([task_id, hours]) => ({ task_id, hours }));
}

export const RECRUIT_NEXT = {
  applied: ["screening", "rejected"],
  screening: ["interview", "rejected"],
  interview: ["evaluation", "rejected"],
  evaluation: ["offered", "rejected"],
  offered: ["hired", "rejected"],
  hired: [],
  rejected: [],
};
