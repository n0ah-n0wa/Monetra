import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const CATEGORY_TYPES = ["income", "expense"] as const;

export type CategoryType = (typeof CATEGORY_TYPES)[number] | "universal";
export type CategoryStatus = "active" | "archived";

export type Category = {
  id: string;
  name: string;
  category_type: CategoryType;
  icon: string | null;
  color: string | null;
  is_system: boolean;
  status: CategoryStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CategoryListParams = {
  page?: number;
  page_size?: number;
  status?: CategoryStatus;
  category_type?: CategoryType;
  include_system?: boolean;
};

export type CategoryCreatePayload = {
  name: string;
  category_type: "income" | "expense";
  icon?: string | null;
  color?: string | null;
};

export type CategoryUpdatePayload = {
  name?: string;
  icon?: string | null;
  color?: string | null;
};

export async function fetchCategories(
  params: CategoryListParams = {},
): Promise<PaginatedResponse<Category>> {
  return apiClient.get<PaginatedResponse<Category>>(
    `/categories${toSearchParams(params)}`,
  );
}

export async function createCategory(
  payload: CategoryCreatePayload,
): Promise<Category> {
  return apiClient.post<Category>("/categories", payload);
}

export async function updateCategory(
  id: string,
  payload: CategoryUpdatePayload,
): Promise<Category> {
  return apiClient.patch<Category>(`/categories/${id}`, payload);
}

export async function archiveCategory(id: string): Promise<Category> {
  return apiClient.post<Category>(`/categories/${id}/archive`);
}

export function formatCategoryType(type: CategoryType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}
