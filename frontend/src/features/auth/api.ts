import { apiClient, requestWithoutAuth } from "@/api/client";
import type { AccessTokenResponse, PasswordResetAckResponse } from "@/types/auth";
import type { User } from "@/types/user";

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = LoginPayload;

export type PasswordResetRequestPayload = {
  email: string;
};

export type PasswordResetConfirmPayload = {
  token: string;
  new_password: string;
};

export async function login(payload: LoginPayload): Promise<AccessTokenResponse> {
  return requestWithoutAuth<AccessTokenResponse>("/auth/login", {
    method: "POST",
    body: payload,
  });
}

export async function register(payload: RegisterPayload): Promise<AccessTokenResponse> {
  return requestWithoutAuth<AccessTokenResponse>("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function refreshSession(): Promise<AccessTokenResponse> {
  return requestWithoutAuth<AccessTokenResponse>("/auth/refresh", {
    method: "POST",
  });
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function requestPasswordReset(
  payload: PasswordResetRequestPayload,
): Promise<PasswordResetAckResponse> {
  return requestWithoutAuth<PasswordResetAckResponse>("/auth/password-reset/request", {
    method: "POST",
    body: payload,
  });
}

export async function confirmPasswordReset(payload: PasswordResetConfirmPayload): Promise<void> {
  await requestWithoutAuth<void>("/auth/password-reset/confirm", {
    method: "POST",
    body: payload,
  });
}

export async function fetchCurrentUser(): Promise<User> {
  return apiClient.get<User>("/users/me");
}

export async function updateCurrentUser(payload: { reporting_currency: string }): Promise<User> {
  return apiClient.patch<User>("/users/me", payload);
}
