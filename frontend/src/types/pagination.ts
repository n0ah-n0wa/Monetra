export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type PaginationParams = {
  page?: number;
  page_size?: number;
};

export function toSearchParams(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
