import { describe, expect, it } from "vitest";
import { ApiError, getErrorMessage, getFieldErrors, parseApiError } from "@/api/errors";

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

describe("getFieldErrors", () => {
  it("maps FastAPI validation issues to fields", () => {
    const error = new ApiError(
      "Request validation failed.",
      422,
      {},
      "VALIDATION_ERROR",
      {
        errors: [
          { loc: ["body", "email"], msg: "value is not a valid email address" },
          { loc: ["body", "password"], msg: "Field required" },
        ],
      },
    );

    expect(getFieldErrors(error)).toEqual({
      email: "value is not a valid email address",
      password: "Field required",
    });
  });

  it("maps weak password details to password fields", () => {
    const error = new ApiError(
      "Password does not meet security requirements.",
      400,
      {},
      "WEAK_PASSWORD",
      {
        errors: [
          "Password must be at least 8 characters.",
          "Password must contain at least one digit.",
        ],
      },
    );

    expect(getFieldErrors(error).password).toContain("at least 8 characters");
    expect(getFieldErrors(error).new_password).toContain("one digit");
  });

  it("maps duplicate email registration to email", () => {
    const error = new ApiError(
      "Email is already registered.",
      409,
      {},
      "EMAIL_ALREADY_REGISTERED",
    );
    expect(getFieldErrors(error).email).toBe("Email is already registered.");
  });
});
