import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;
  readonly body: unknown;

  constructor(
    message: string,
    status: number,
    body: unknown,
    code = "UNKNOWN_ERROR",
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.body = body;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function parseApiError(status: number, body: unknown): ApiError {
  const payload = body as ApiErrorBody;
  const error = payload?.error;

  if (error?.message) {
    return new ApiError(
      error.message,
      status,
      body,
      error.code,
      error.details ?? {},
      payload.request_id ?? null,
    );
  }

  if (typeof body === "string" && body.trim()) {
    return new ApiError(body, status, body);
  }

  return new ApiError("Request failed.", status, body);
}

export function getErrorMessage(
  error: unknown,
  fallback = "Something went wrong.",
): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

type ValidationIssue = {
  loc?: Array<string | number>;
  msg?: string;
  message?: string;
};

/**
 * Maps backend error payloads onto form field names.
 * Supports FastAPI validation `details.errors` and simple field maps.
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error)) {
    return {};
  }

  const fieldErrors: Record<string, string> = {};
  const details = error.details;

  if (error.code === "EMAIL_ALREADY_REGISTERED") {
    fieldErrors.email = error.message;
  }

  if (error.code === "WEAK_PASSWORD") {
    const weakErrors = details.errors;
    if (
      Array.isArray(weakErrors) &&
      weakErrors.every((item) => typeof item === "string")
    ) {
      const message = (weakErrors as string[]).join(" ");
      fieldErrors.password = message;
      fieldErrors.new_password = message;
    } else {
      fieldErrors.password = error.message;
      fieldErrors.new_password = error.message;
    }
  }

  if (error.code === "INVALID_CREDENTIALS") {
    fieldErrors.root = error.message;
  }

  if (error.code === "INVALID_RESET_TOKEN") {
    fieldErrors.token = error.message;
  }

  if (error.code === "CATEGORY_NAME_CONFLICT") {
    fieldErrors.name = error.message;
  }

  if (error.code === "CATEGORY_TYPE_MISMATCH") {
    fieldErrors.category_id = error.message;
  }

  if (error.code === "ACCOUNT_ARCHIVED" || error.code === "ACCOUNT_NOT_FOUND") {
    fieldErrors.account_id = error.message;
  }

  if (error.code === "CATEGORY_ARCHIVED" || error.code === "CATEGORY_NOT_FOUND") {
    fieldErrors.category_id = error.message;
  }

  if (error.code === "BUDGET_ARCHIVED" || error.code === "BUDGET_NOT_FOUND") {
    fieldErrors.root = error.message;
  }

  const rawErrors = details.errors;
  if (Array.isArray(rawErrors)) {
    for (const issue of rawErrors) {
      if (typeof issue === "string") {
        continue;
      }
      const validationIssue = issue as ValidationIssue;
      const loc = validationIssue.loc ?? [];
      const field = loc
        .filter((part): part is string => typeof part === "string")
        .filter((part) => part !== "body" && part !== "query" && part !== "path")
        .at(-1);
      const message = validationIssue.msg ?? validationIssue.message;
      if (field && message && !fieldErrors[field]) {
        fieldErrors[field] = message;
      }
    }
  }

  for (const [key, value] of Object.entries(details)) {
    if (key === "errors") {
      continue;
    }
    if (typeof value === "string" && !fieldErrors[key]) {
      fieldErrors[key] = value;
    }
  }

  return fieldErrors;
}

export function isUnauthorizedError(error: unknown): boolean {
  return isApiError(error) && error.status === 401;
}

export function isForbiddenError(error: unknown): boolean {
  return isApiError(error) && error.status === 403;
}

export function isAuthFailureError(error: unknown): boolean {
  return isUnauthorizedError(error) || isForbiddenError(error);
}

export class SessionExpiredError extends Error {
  constructor(message = "Session expired.") {
    super(message);
    this.name = "SessionExpiredError";
  }
}

export function isSessionExpiredError(error: unknown): error is SessionExpiredError {
  return error instanceof SessionExpiredError;
}
