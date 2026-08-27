import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createMemoryRouter,
  RouterProvider,
  type InitialEntry,
} from "react-router-dom";
import { AuthProvider } from "@/features/auth/context";
import { setAccessToken } from "@/api/client";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function renderWithAuth(
  ui: ReactElement,
  options?: {
    initialEntries?: InitialEntry[];
    routes?: Array<{ path: string; element: ReactNode }>;
    authenticated?: boolean;
  },
) {
  setAccessToken(options?.authenticated ? "test-access-token" : null);
  const client = createTestQueryClient();
  const routes = options?.routes ?? [{ path: "*", element: ui }];
  const router = createMemoryRouter(routes, {
    initialEntries: options?.initialEntries ?? ["/"],
  });

  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    ),
  };
}
