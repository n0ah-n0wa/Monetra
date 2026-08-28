import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  archiveCategory,
  createCategory,
  fetchCategories,
  updateCategory,
  type CategoryCreatePayload,
  type CategoryListParams,
  type CategoryUpdatePayload,
} from "@/features/categories/api";
import { queryKeys } from "@/lib/query-client";

const REFERENCE_DATA_STALE_MS = 5 * 60_000;

export function useCategoriesQuery(
  params: CategoryListParams = { status: "active", page_size: 100 },
) {
  return useQuery({
    queryKey: queryKeys.categories.list(params),
    queryFn: () => fetchCategories(params),
    placeholderData: keepPreviousData,
    staleTime: REFERENCE_DATA_STALE_MS,
  });
}

export function useCreateCategoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreatePayload) => createCategory(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}

export function useUpdateCategoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CategoryUpdatePayload }) =>
      updateCategory(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}

export function useArchiveCategoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveCategory(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    },
  });
}
