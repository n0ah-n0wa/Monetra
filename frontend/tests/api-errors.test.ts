import { describe, expect, it } from "vitest";
import { ApiError, getErrorMessage, parseApiError } from "@/api/errors";

describe("parseApiError", () => {
  it("extracts structured API errors", () => {
    const error = parseApiError(400, {
      error: {
        code: "VALIDATION_ERROR",
        message: "Invalid email.",
        details: { field: "email" },
      },
      request_id: "req-1",
    });

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Invalid email.");
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.details).toEqual({ field: "email" });
    expect(error.requestId).toBe("req-1");
  });

  it("falls back to generic message", () => {
    const error = parseApiError(500, null);
    expect(error.message).toBe("Request failed.");
  });
});

describe("getErrorMessage", () => {
  it("returns api error message", () => {
    const error = new ApiError("Denied", 403, {}, "FORBIDDEN");
    expect(getErrorMessage(error)).toBe("Denied");
  });
});
