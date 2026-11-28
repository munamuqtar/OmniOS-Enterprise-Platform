import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useFormState } from "../../hooks/useFormState";
import { CheckboxGroup } from "./fields";

function Harness() {
  const form = useFormState({ roles: ["hr"] });
  return (
    <>
      <CheckboxGroup form={form} name="roles" label="Roles"
                     options={[{ value: "hr", label: "HR" }, { value: "sales", label: "Sales" }]} />
      <output data-testid="value">{form.values.roles.join(",")}</output>
    </>
  );
}

describe("CheckboxGroup", () => {
  it("toggles values on and off", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByLabelText("Sales"));
    expect(screen.getByTestId("value")).toHaveTextContent("hr,sales");
    await userEvent.click(screen.getByLabelText("HR"));
    expect(screen.getByTestId("value")).toHaveTextContent("sales");
  });
});