import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAccessToken, setAccessToken, setTokenRefreshHandler } from "@/api/client";
import * as authApi from "@/features/auth/api";
import type { LoginFormValues, RegisterFormValues } from "@/features/auth/schemas";
import { queryKeys } from "@/lib/query-client";
import type { User } from "@/types/user";

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (values: LoginFormValues) => Promise<void>;
  register: (values: RegisterFormValues) => Promise<void>;
  logout: () => Promise<void>;
  isLoggingIn: boolean;
  isRegistering: boolean;
  isLoggingOut: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export type { AuthContextValue };
export { AuthContext };

function applyAccessToken(token: string | null): void {
  setAccessToken(token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [bootstrapped, setBootstrapped] = useState(false);
  const refreshPromiseRef = useRef<Promise<string | null> | null>(null);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }

    refreshPromiseRef.current = (async () => {
      try {
        const response = await authApi.refreshSession();
        applyAccessToken(response.access_token);
        return response.access_token;
      } catch {
        applyAccessToken(null);
        return null;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    return refreshPromiseRef.current;
  }, []);

  useEffect(() => {
    setTokenRefreshHandler(refreshAccessToken);
    return () => setTokenRefreshHandler(null);
  }, [refreshAccessToken]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getAccessToken()) {
        await refreshAccessToken();
      }
      if (!cancelled) {
        setBootstrapped(true);
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [refreshAccessToken]);

  const userQuery = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: authApi.fetchCurrentUser,
    enabled: bootstrapped && Boolean(getAccessToken()),
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (response) => {
      applyAccessToken(response.access_token);
      await queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
    },
  });

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: async (response) => {
      applyAccessToken(response.access_token);
      await queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: async () => {
      applyAccessToken(null);
      await queryClient.clear();
    },
  });

  useEffect(() => {
    if (userQuery.isError) {
      applyAccessToken(null);
    }
  }, [userQuery.isError]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: userQuery.data ?? null,
      isAuthenticated: Boolean(getAccessToken()),
      isBootstrapping:
        !bootstrapped || (Boolean(getAccessToken()) && userQuery.isPending && !userQuery.isError),
      login: async (values) => {
        await loginMutation.mutateAsync(values);
      },
      register: async (values) => {
        await registerMutation.mutateAsync(values);
      },
      logout: async () => {
        await logoutMutation.mutateAsync();
      },
      isLoggingIn: loginMutation.isPending,
      isRegistering: registerMutation.isPending,
      isLoggingOut: logoutMutation.isPending,
    }),
    [
      bootstrapped,
      loginMutation,
      logoutMutation,
      registerMutation,
      userQuery.data,
      userQuery.isError,
      userQuery.isPending,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
