import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export type Category = {
  id: string;
  name: string;
  category_type: string;
  status: string;
};

export type CategoryListParams = {
  page?: number;
  page_size?: number;
};

export async function fetchCategories(
  params: CategoryListParams = {},
): Promise<PaginatedResponse<Category>> {
  return apiClient.get<PaginatedResponse<Category>>(`/categories${toSearchParams(params)}`);
}

export async function fetchCategory(id: string): Promise<Category> {
  return apiClient.get<Category>(`/categories/${id}`);
}
