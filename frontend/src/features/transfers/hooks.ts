import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTransfer,
  fetchTransfers,
  type TransferCreatePayload,
  type TransferListParams,
} from "@/features/transfers/api";
import { queryKeys } from "@/lib/query-client";

export function useTransfersQuery(params: TransferListParams = {}) {
  return useQuery({
    queryKey: queryKeys.transfers.list(params),
    queryFn: () => fetchTransfers(params),
  });
}

export function useCreateTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransferCreatePayload) => createTransfer(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.transfers.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all }),
        queryClient.invalidateQueries({ queryKey: queryKeys.analytics.root }),
      ]);
    },
  });
}
