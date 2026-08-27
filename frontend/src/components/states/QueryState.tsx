import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";

type QueryStateProps<T> = {
  query: UseQueryResult<T>;
  loadingTitle?: string;
  errorTitle?: string;
  children: (data: T) => ReactNode;
};

export function QueryState<T>({
  query,
  loadingTitle,
  errorTitle,
  children,
}: QueryStateProps<T>) {
  if (query.isPending) {
    return <LoadingState title={loadingTitle} />;
  }

  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        title={errorTitle}
        onRetry={() => void query.refetch()}
      />
    );
  }

  return <>{children(query.data)}</>;
}
