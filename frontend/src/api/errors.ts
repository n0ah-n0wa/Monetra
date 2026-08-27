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

export function getErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
