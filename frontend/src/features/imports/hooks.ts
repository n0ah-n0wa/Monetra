import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  confirmImportJob,
  fetchImportJob,
  fetchImportJobs,
  uploadImportFile,
  type ImportConfirmPayload,
  type ImportListParams,
} from "@/features/imports/api";
import { queryKeys } from "@/lib/query-client";

export function useImportJobsQuery(
  params: ImportListParams = { page: 1, page_size: 10 },
) {
  return useQuery({
    queryKey: queryKeys.imports.list(params),
    queryFn: () => fetchImportJobs(params),
    placeholderData: keepPreviousData,
  });
}

export function useImportJobQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.imports.detail(id ?? ""),
    queryFn: () => fetchImportJob(id!),
    enabled: Boolean(id),
  });
}

export function useUploadImportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, file }: { accountId: string; file: File }) =>
      uploadImportFile(accountId, file),
    onSuccess: async (job) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.imports.all });
      queryClient.setQueryData(queryKeys.imports.detail(job.id), job);
    },
  });
}

export function useConfirmImportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload?: ImportConfirmPayload }) =>
      confirmImportJob(id, payload),
    onSuccess: async (job) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.imports.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
      queryClient.setQueryData(queryKeys.imports.detail(job.id), job);
    },
  });
}
