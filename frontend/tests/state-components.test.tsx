import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
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
