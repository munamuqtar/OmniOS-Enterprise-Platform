import { describe, it, expect } from "vitest";
import { PAYMENT_ACTIONS, PROJECT_NEXT, RECRUIT_NEXT, groupHoursByTask, taskMoves } from "./workflow";

describe("task moves", () => {
  it("lets an employee start work and send it to review", () => {
    expect(taskMoves("todo", false)).toEqual(["in_progress"]);
    expect(taskMoves("in_progress", false)).toEqual(["todo", "review"]);
  });
  it("stops employees from completing or reopening tasks", () => {
    expect(taskMoves("review", false)).toEqual(["in_progress"]);
    expect(taskMoves("completed", false)).toEqual([]);
  });
  it("lets a project manager complete and reopen", () => {
    expect(taskMoves("review", true)).toEqual(["in_progress", "completed"]);
    expect(taskMoves("completed", true)).toEqual(["in_progress"]);
  });
});

describe("project and payment workflows", () => {
  it("offers no moves for closed projects", () => {
    expect(PROJECT_NEXT.completed).toEqual([]);
    expect(PROJECT_NEXT.cancelled).toEqual([]);
  });
  it("only lets pending and confirmed payments change", () => {
    expect(PAYMENT_ACTIONS.pending).toEqual(["confirm", "reject"]);
    expect(PAYMENT_ACTIONS.confirmed).toEqual(["reconcile", "reject"]);
    expect(PAYMENT_ACTIONS.reconciled).toEqual([]);
  });
});

describe("groupHoursByTask", () => {
  it("sums hours per task like the server's invoice lines", () => {
    const rows = [{ task_id: "a", hours: "8" }, { task_id: "a", hours: "2" }, { task_id: "b", hours: "5" }];
    expect(groupHoursByTask(rows)).toEqual([{ task_id: "a", hours: 10 }, { task_id: "b", hours: 5 }]);
  });
});

describe("recruitment stages", () => {
  it("cannot skip stages", () => {
    expect(RECRUIT_NEXT.applied).toEqual(["screening", "rejected"]);
    expect(RECRUIT_NEXT.applied).not.toContain("interview");
  });
  it("lets every open stage be rejected, and closes hired and rejected", () => {
    ["applied", "screening", "interview", "evaluation", "offered"].forEach((s) => expect(RECRUIT_NEXT[s]).toContain("rejected"));
    expect(RECRUIT_NEXT.hired).toEqual([]);
    expect(RECRUIT_NEXT.rejected).toEqual([]);
  });
});