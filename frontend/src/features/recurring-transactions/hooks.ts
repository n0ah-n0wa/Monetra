import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  archiveRecurringTransaction,
  createRecurringTransaction,
  fetchRecurringTransaction,
  fetchRecurringTransactions,
  updateRecurringTransaction,
  type RecurringTransactionCreatePayload,
  type RecurringTransactionListParams,
  type RecurringTransactionUpdatePayload,
} from "@/features/recurring-transactions/api";
import { queryKeys } from "@/lib/query-client";

export function useRecurringTransactionsQuery(
  params: RecurringTransactionListParams = {},
) {
  return useQuery({
    queryKey: queryKeys.recurringTransactions.list(params),
    queryFn: () => fetchRecurringTransactions(params),
    placeholderData: keepPreviousData,
  });
}

export function useRecurringTransactionQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.recurringTransactions.detail(id ?? ""),
    queryFn: () => fetchRecurringTransaction(id!),
    enabled: Boolean(id),
  });
}

export function useCreateRecurringTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RecurringTransactionCreatePayload) =>
      createRecurringTransaction(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.recurringTransactions.all,
      });
    },
  });
}

export function useUpdateRecurringTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: RecurringTransactionUpdatePayload;
    }) => updateRecurringTransaction(id, payload),
    onSuccess: async (recurring) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.recurringTransactions.all,
      });
      queryClient.setQueryData(
        queryKeys.recurringTransactions.detail(recurring.id),
        recurring,
      );
    },
  });
}

export function useArchiveRecurringTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveRecurringTransaction(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.recurringTransactions.all,
      });
    },
  });
}

export function useSetRecurringTransactionActiveMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateRecurringTransaction(id, { is_active }),
    onSuccess: async (recurring) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.recurringTransactions.all,
      });
      queryClient.setQueryData(
        queryKeys.recurringTransactions.detail(recurring.id),
        recurring,
      );
    },
  });
}
