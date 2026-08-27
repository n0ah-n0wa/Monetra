export type ApiErrorBody = {
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  request_id?: string | null;
};
