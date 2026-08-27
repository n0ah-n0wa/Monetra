import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  archiveAccount,
  createAccount,
  fetchAccount,
  fetchAccounts,
  updateAccount,
  type AccountCreatePayload,
  type AccountListParams,
  type AccountUpdatePayload,
} from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-client";

export function useAccountsQuery(params: AccountListParams = { status: "active" }) {
  return useQuery({
    queryKey: queryKeys.accounts.list(params),
    queryFn: () => fetchAccounts(params),
    placeholderData: keepPreviousData,
  });
}

export function useAccountQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.accounts.detail(id ?? ""),
    queryFn: () => fetchAccount(id!),
    enabled: Boolean(id),
  });
}

export function useCreateAccountMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountCreatePayload) => createAccount(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
    },
  });
}

export function useUpdateAccountMutation(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountUpdatePayload) => updateAccount(id, payload),
    onSuccess: async (account) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
      queryClient.setQueryData(queryKeys.accounts.detail(id), account);
    },
  });
}

export function useArchiveAccountMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveAccount(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all }),
      ]);
    },
  });
}
