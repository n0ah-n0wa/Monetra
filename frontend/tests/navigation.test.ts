import { describe, expect, it } from "vitest";
import { safeInternalPath } from "@/lib/navigation";

describe("safeInternalPath", () => {
  it("allows same-origin app paths", () => {
    expect(safeInternalPath("/transactions", "/dashboard")).toBe("/transactions");
    expect(safeInternalPath("/accounts/acc-1", "/dashboard")).toBe("/accounts/acc-1");
  });

  it("rejects external and protocol-relative paths", () => {
    expect(safeInternalPath("//evil.com", "/dashboard")).toBe("/dashboard");
    expect(safeInternalPath("https://evil.com", "/dashboard")).toBe("/dashboard");
    expect(safeInternalPath("transactions", "/dashboard")).toBe("/dashboard");
  });

  it("falls back when path is missing", () => {
    expect(safeInternalPath(undefined, "/dashboard")).toBe("/dashboard");
    expect(safeInternalPath("", "/dashboard")).toBe("/dashboard");
  });
});
