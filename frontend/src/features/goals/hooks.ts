import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  archiveGoal,
  createGoal,
  fetchGoal,
  fetchGoals,
  updateGoal,
  type GoalCreatePayload,
  type GoalListParams,
  type GoalUpdatePayload,
} from "@/features/goals/api";
import { queryKeys } from "@/lib/query-client";

export function useGoalsQuery(params: GoalListParams = { include_progress: true }) {
  return useQuery({
    queryKey: queryKeys.goals.list(params),
    queryFn: () => fetchGoals(params),
    placeholderData: keepPreviousData,
  });
}

export function useGoalQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.goals.detail(id ?? ""),
    queryFn: () => fetchGoal(id!, { include_progress: true }),
    enabled: Boolean(id),
  });
}

export function useCreateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GoalCreatePayload) => createGoal(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals.all });
    },
  });
}

export function useUpdateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: GoalUpdatePayload }) =>
      updateGoal(id, payload),
    onSuccess: async (goal) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals.all });
      queryClient.setQueryData(queryKeys.goals.detail(goal.id), goal);
    },
  });
}

export function useArchiveGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveGoal(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.goals.all });
    },
  });
}
