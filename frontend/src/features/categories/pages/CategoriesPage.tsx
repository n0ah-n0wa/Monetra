import { useMemo, useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import {
  CategoryCreateForm,
  CategoryEditForm,
} from "@/features/categories/components/CategoryForm";
import {
  formatCategoryType,
  type Category,
  type CategoryStatus,
  type CategoryType,
} from "@/features/categories/api";
import {
  useArchiveCategoryMutation,
  useCategoriesQuery,
  useCreateCategoryMutation,
  useUpdateCategoryMutation,
} from "@/features/categories/hooks";

type DialogState =
  | { type: "create" }
  | { type: "edit"; category: Category }
  | { type: "archive"; category: Category }
  | null;

export function CategoriesPage() {
  const [statusFilter, setStatusFilter] = useState<CategoryStatus | "all">("active");
  const [typeFilter, setTypeFilter] = useState<CategoryType | "all">("all");
  const [dialog, setDialog] = useState<DialogState>(null);

  const listParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      status: statusFilter === "all" ? undefined : statusFilter,
      category_type: typeFilter === "all" ? undefined : typeFilter,
      include_system: true,
    }),
    [statusFilter, typeFilter],
  );

  const categoriesQuery = useCategoriesQuery(listParams);
  const createMutation = useCreateCategoryMutation();
  const updateMutation = useUpdateCategoryMutation();
  const archiveMutation = useArchiveCategoryMutation();

  const editingCategory = dialog?.type === "edit" ? dialog.category : null;

  return (
    <PageContainer>
      <PageHeader
        title="Categories"
        description="Organize income and expenses. System categories are read-only."
        actions={
          <Button onClick={() => setDialog({ type: "create" })}>Add category</Button>
        }
      />

      <div className="toolbar">
        <label className="toolbar__filter" htmlFor="category-status-filter">
          <span>Status</span>
          <Select
            id="category-status-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as CategoryStatus | "all")
            }
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </Select>
        </label>
        <label className="toolbar__filter" htmlFor="category-type-filter">
          <span>Type</span>
          <Select
            id="category-type-filter"
            value={typeFilter}
            onChange={(event) =>
              setTypeFilter(event.target.value as CategoryType | "all")
            }
          >
            <option value="all">All</option>
            <option value="income">Income</option>
            <option value="expense">Expense</option>
            <option value="universal">Universal</option>
          </Select>
        </label>
      </div>

      {categoriesQuery.isPending ? <LoadingState title="Loading categories" /> : null}
      {categoriesQuery.isError ? (
        <ErrorState
          error={categoriesQuery.error}
          title="Unable to load categories"
          onRetry={() => void categoriesQuery.refetch()}
        />
      ) : null}

      {categoriesQuery.isSuccess && categoriesQuery.data.items.length === 0 ? (
        <EmptyState
          title="No categories found"
          description="Create a category or adjust the filters."
        />
      ) : null}

      {categoriesQuery.isSuccess && categoriesQuery.data.items.length > 0 ? (
        <div className="data-list" role="list">
          {categoriesQuery.data.items.map((category) => {
            const canMutate = !category.is_system && category.status === "active";
            return (
              <article key={category.id} className="data-card" role="listitem">
                <div className="data-card__main">
                  <div className="data-card__title-row">
                    <h2 className="data-card__title">{category.name}</h2>
                    <Badge
                      variant={category.status === "active" ? "success" : "neutral"}
                    >
                      {category.status}
                    </Badge>
                    {category.is_system ? <Badge variant="info">System</Badge> : null}
                  </div>
                  <p className="data-card__meta">
                    {formatCategoryType(category.category_type)}
                    {category.color ? ` · ${category.color}` : ""}
                    {category.icon ? ` · ${category.icon}` : ""}
                  </p>
                </div>
                <div className="data-card__actions">
                  {canMutate ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setDialog({ type: "edit", category })}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setDialog({ type: "archive", category })}
                      >
                        Archive
                      </Button>
                    </>
                  ) : (
                    <span className="data-card__meta">
                      {category.is_system ? "Read-only" : "Archived"}
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      <Modal
        open={dialog?.type === "create"}
        title="Create category"
        description="User categories must be income or expense."
        onClose={() => setDialog(null)}
      >
        <CategoryCreateForm
          submitting={createMutation.isPending}
          onCancel={() => setDialog(null)}
          onSubmit={async (values) => {
            await createMutation.mutateAsync({
              name: values.name,
              category_type: values.category_type,
              icon: values.icon || null,
              color: values.color || null,
            });
            setDialog(null);
          }}
        />
      </Modal>

      <Modal
        open={dialog?.type === "edit"}
        title="Edit category"
        onClose={() => setDialog(null)}
      >
        {editingCategory ? (
          <CategoryEditForm
            category={editingCategory}
            submitting={updateMutation.isPending}
            onCancel={() => setDialog(null)}
            onSubmit={async (values) => {
              await updateMutation.mutateAsync({
                id: editingCategory.id,
                payload: {
                  name: values.name,
                  icon: values.icon || null,
                  color: values.color || null,
                },
              });
              setDialog(null);
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog?.type === "archive"}
        title="Archive category?"
        description={
          dialog?.type === "archive"
            ? `Archive “${dialog.category.name}”? Existing transactions keep their history.`
            : ""
        }
        confirmLabel="Archive category"
        loading={archiveMutation.isPending}
        error={archiveMutation.error}
        onCancel={() => {
          archiveMutation.reset();
          setDialog(null);
        }}
        onConfirm={() => {
          if (dialog?.type !== "archive") {
            return;
          }
          void archiveMutation.mutateAsync(dialog.category.id).then(() => {
            setDialog(null);
          });
        }}
      />
    </PageContainer>
  );
}
