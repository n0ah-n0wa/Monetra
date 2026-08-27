import { useQuery } from "@tanstack/react-query";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchCategories } from "@/features/categories/api";
import { queryKeys } from "@/lib/query-client";

export function CategoriesPage() {
  const query = useQuery({
    queryKey: queryKeys.categories.list(),
    queryFn: () => fetchCategories({ page: 1, page_size: 1 }),
  });

  return (
    <FeaturePlaceholder
      title="Categories"
      description="Organize spending and income with reusable categories."
    >
      {query.isPending ? <LoadingState title="Loading categories" /> : null}
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.total_items === 0 ? (
        <EmptyState
          title="No categories yet"
          description="Default and custom categories will be managed here."
        />
      ) : null}
      {query.isSuccess && query.data.total_items > 0 ? (
        <p>{query.data.total_items} category(ies) available.</p>
      ) : null}
    </FeaturePlaceholder>
  );
}
