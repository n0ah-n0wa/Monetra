import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { FormField } from "@/components/forms/FormField";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/api/errors";

describe("state components", () => {
  it("renders loading state", () => {
    render(<LoadingState title="Loading data" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading data")).toBeInTheDocument();
  });

  it("renders error state with retry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ErrorState error={new ApiError("Failed", 500, {})} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders empty state", () => {
    render(<EmptyState title="Nothing here" description="Add your first item." />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Add your first item.")).toBeInTheDocument();
  });
});

describe("FormField accessibility", () => {
  it("wires label, describedby, and invalid state", () => {
    render(
      <FormField
        id="email"
        label="Email"
        required
        description="Use your work email."
        error={{ type: "manual", message: "Enter a valid email address." }}
      >
        <Input id="email" />
      </FormField>,
    );

    const input = screen.getByLabelText(/email/i);
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-required", "true");
    expect(input.getAttribute("aria-describedby")).toContain("email-description");
    expect(input.getAttribute("aria-describedby")).toContain("email-error");
    expect(screen.getByText("Enter a valid email address.")).toHaveAttribute(
      "role",
      "alert",
    );
  });
});
