import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConfirmDialog from "./ConfirmDialog";

const base = { open: true, title: "Reject", message: "Why?", confirmLabel: "Reject", onCancel: () => {} };

describe("ConfirmDialog", () => {
  it("renders nothing when closed", () => {
    render(<ConfirmDialog {...base} open={false} onConfirm={() => {}} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("blocks confirming until a reason is typed", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog {...base} requireReason onConfirm={onConfirm} />);
    const confirm = screen.getByRole("button", { name: "Reject" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox"), "Too expensive");
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith("Too expensive");
  });
  it("shows server errors inside the dialog", () => {
    render(<ConfirmDialog {...base} error="Only a manager can approve." onConfirm={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/only a manager/i);
  });
});