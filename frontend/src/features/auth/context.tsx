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
import { isAuthFailureError } from "@/api/errors";
import {
  getAccessToken,
  setAccessToken,
  setSessionExpiredHandler,
  setTokenRefreshHandler,
} from "@/api/client";
import * as authApi from "@/features/auth/api";
import type { LoginFormValues, RegisterFormValues } from "@/features/auth/schemas";
import { queryKeys } from "@/lib/query-client";
import type { User } from "@/types/user";

export type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  profileLoadError: unknown | null;
  retryProfileLoad: () => void;
  sessionExpired: boolean;
  clearSessionExpired: () => void;
  login: (values: LoginFormValues) => Promise<void>;
  register: (values: RegisterFormValues) => Promise<void>;
  logout: () => Promise<void>;
  isLoggingIn: boolean;
  isRegistering: boolean;
  isLoggingOut: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export { AuthContext };

function applyAccessToken(token: string | null): void {
  setAccessToken(token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [bootstrapped, setBootstrapped] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [hasToken, setHasToken] = useState(() => Boolean(getAccessToken()));
  const refreshPromiseRef = useRef<Promise<string | null> | null>(null);

  const syncTokenState = useCallback((token: string | null) => {
    applyAccessToken(token);
    setHasToken(Boolean(token));
  }, []);

  const clearSession = useCallback(
    async (markExpired: boolean) => {
      syncTokenState(null);
      await queryClient.clear();
      if (markExpired) {
        setSessionExpired(true);
      }
    },
    [queryClient, syncTokenState],
  );

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }

    refreshPromiseRef.current = (async () => {
      try {
        const response = await authApi.refreshSession();
        syncTokenState(response.access_token);
        return response.access_token;
      } catch {
        syncTokenState(null);
        return null;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    return refreshPromiseRef.current;
  }, [syncTokenState]);

  useEffect(() => {
    setTokenRefreshHandler(refreshAccessToken);
    return () => setTokenRefreshHandler(null);
  }, [refreshAccessToken]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      void clearSession(true);
    });
    return () => setSessionExpiredHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getAccessToken()) {
        await refreshAccessToken();
      }
      if (!cancelled) {
        setHasToken(Boolean(getAccessToken()));
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
    enabled: bootstrapped && hasToken,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (response) => {
      syncTokenState(response.access_token);
      setSessionExpired(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
    },
  });

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: async (response) => {
      syncTokenState(response.access_token);
      setSessionExpired(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      try {
        await authApi.logout();
      } catch {
        // Always clear local session even if the network call fails.
      }
    },
    onSettled: async () => {
      await clearSession(false);
      setSessionExpired(false);
    },
  });

  useEffect(() => {
    if (userQuery.isError && hasToken && isAuthFailureError(userQuery.error)) {
      void clearSession(true);
    }
  }, [clearSession, hasToken, userQuery.error, userQuery.isError]);

  const profileLoadError =
    hasToken && userQuery.isError && !isAuthFailureError(userQuery.error)
      ? userQuery.error
      : null;

  const {
    data: user,
    isPending: isUserPending,
    isError: isUserError,
    refetch: refetchUser,
  } = userQuery;
  const { mutateAsync: loginAsync, isPending: isLoggingIn } = loginMutation;
  const { mutateAsync: registerAsync, isPending: isRegistering } = registerMutation;
  const { mutateAsync: logoutAsync, isPending: isLoggingOut } = logoutMutation;

  const value = useMemo<AuthContextValue>(
    () => ({
      user: user ?? null,
      isAuthenticated: hasToken,
      isBootstrapping: !bootstrapped || (hasToken && isUserPending && !isUserError),
      profileLoadError,
      retryProfileLoad: () => {
        void refetchUser();
      },
      sessionExpired,
      clearSessionExpired: () => setSessionExpired(false),
      login: async (values) => {
        await loginAsync(values);
      },
      register: async (values) => {
        await registerAsync(values);
      },
      logout: async () => {
        await logoutAsync();
      },
      isLoggingIn,
      isRegistering,
      isLoggingOut,
    }),
    [
      bootstrapped,
      hasToken,
      isLoggingIn,
      isLoggingOut,
      isRegistering,
      isUserError,
      isUserPending,
      loginAsync,
      logoutAsync,
      profileLoadError,
      refetchUser,
      registerAsync,
      sessionExpired,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
