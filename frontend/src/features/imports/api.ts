import { apiClient } from "@/api/client";
import type { PaginatedResponse } from "@/types/pagination";
import { toSearchParams } from "@/types/pagination";

export const IMPORT_JOB_STATUSES = [
  "pending",
  "preview",
  "processing",
  "completed",
  "failed",
] as const;

export type ImportJobStatus = (typeof IMPORT_JOB_STATUSES)[number];

export type ImportJobStats = {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  imported_rows: number;
  skipped_rows: number;
  duplicate_rows: number;
};

export type ImportRowError = {
  row_number: number;
  code: string;
  message: string;
  raw: Record<string, string>;
};

export type ImportPreviewRow = {
  row_number: number;
  transaction_date: string;
  transaction_type: string;
  amount: string;
  description: string;
  category: string;
  category_id: string | null;
  external_reference: string | null;
  notes: string | null;
  is_duplicate: boolean;
  duplicate_reason: string | null;
};

export type ImportJob = {
  id: string;
  target_account_id: string | null;
  original_filename: string;
  content_type: string | null;
  status: ImportJobStatus;
  stats: ImportJobStats;
  preview_rows: ImportPreviewRow[];
  errors: ImportRowError[];
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ImportListParams = {
  page?: number;
  page_size?: number;
};

export type ImportConfirmPayload = {
  skip_duplicates?: boolean;
};

export function formatImportStatus(status: ImportJobStatus): string {
  const labels: Record<ImportJobStatus, string> = {
    pending: "Pending",
    preview: "Preview",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  };
  return labels[status];
}

export function importStatusVariant(
  status: ImportJobStatus,
): "success" | "warning" | "neutral" | "info" {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed") {
    return "warning";
  }
  if (status === "preview" || status === "processing") {
    return "info";
  }
  return "neutral";
}

export function canConfirmImport(job: ImportJob): boolean {
  return job.status === "preview" && job.stats.valid_rows > 0;
}

export function requiresInvalidRowAcknowledgment(job: ImportJob): boolean {
  return job.stats.invalid_rows > 0;
}

export async function uploadImportFile(
  accountId: string,
  file: File,
): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("account_id", accountId);
  formData.append("file", file);
  return apiClient.postForm<ImportJob>("/imports", formData);
}

export async function fetchImportJobs(
  params: ImportListParams = {},
): Promise<PaginatedResponse<ImportJob>> {
  return apiClient.get<PaginatedResponse<ImportJob>>(
    `/imports${toSearchParams(params)}`,
  );
}

export async function fetchImportJob(id: string): Promise<ImportJob> {
  return apiClient.get<ImportJob>(`/imports/${id}`);
}

export async function confirmImportJob(
  id: string,
  payload: ImportConfirmPayload = { skip_duplicates: true },
): Promise<ImportJob> {
  return apiClient.post<ImportJob>(`/imports/${id}/confirm`, payload);
}
