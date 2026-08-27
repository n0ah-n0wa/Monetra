import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  archiveBudget,
  createBudget,
  fetchBudget,
  fetchBudgets,
  updateBudget,
  type BudgetCreatePayload,
  type BudgetListParams,
  type BudgetUpdatePayload,
} from "@/features/budgets/api";
import { queryKeys } from "@/lib/query-client";

export function useBudgetsQuery(
  params: BudgetListParams = { include_utilization: true },
) {
  return useQuery({
    queryKey: queryKeys.budgets.list(params),
    queryFn: () => fetchBudgets(params),
    placeholderData: keepPreviousData,
  });
}

export function useBudgetQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.budgets.detail(id ?? ""),
    queryFn: () => fetchBudget(id!, { include_utilization: true }),
    enabled: Boolean(id),
  });
}

export function useCreateBudgetMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BudgetCreatePayload) => createBudget(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.budgets.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
    },
  });
}

export function useUpdateBudgetMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: BudgetUpdatePayload }) =>
      updateBudget(id, payload),
    onSuccess: async (budget) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.budgets.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
      queryClient.setQueryData(queryKeys.budgets.detail(budget.id), budget);
    },
  });
}

export function useArchiveBudgetMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveBudget(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.budgets.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
    },
  });
}
