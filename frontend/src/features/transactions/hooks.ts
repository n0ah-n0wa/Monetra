import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  createTransaction,
  deleteTransaction,
  fetchTransaction,
  fetchTransactions,
  updateTransaction,
  type TransactionCreatePayload,
  type TransactionListParams,
  type TransactionUpdatePayload,
} from "@/features/transactions/api";
import { queryKeys } from "@/lib/query-client";

export function useTransactionsQuery(params: TransactionListParams) {
  return useQuery({
    queryKey: queryKeys.transactions.list(params),
    queryFn: () => fetchTransactions(params),
    placeholderData: keepPreviousData,
  });
}

export function useTransactionQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.transactions.detail(id ?? ""),
    queryFn: () => fetchTransaction(id!),
    enabled: Boolean(id),
  });
}

export function useCreateTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransactionCreatePayload) => createTransaction(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
    },
  });
}

export function useUpdateTransactionMutation(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransactionUpdatePayload) => updateTransaction(id, payload),
    onSuccess: async (transaction) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
      queryClient.setQueryData(queryKeys.transactions.detail(id), transaction);
    },
  });
}

export function useDeleteTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTransaction(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
    },
  });
}
