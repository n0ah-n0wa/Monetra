import { zodResolver } from "@hookform/resolvers/zod";
import type {
  FieldValues,
  Path,
  UseFormProps,
  UseFormReturn,
  UseFormSetError,
} from "react-hook-form";
import { useForm } from "react-hook-form";
import type { ZodType } from "zod";
import { getErrorMessage, getFieldErrors, isApiError } from "@/api/errors";

export function useZodForm<TFieldValues extends FieldValues>(
  schema: ZodType<TFieldValues>,
  options?: Omit<UseFormProps<TFieldValues>, "resolver">,
) {
  return useForm<TFieldValues>({
    ...options,
    resolver: zodResolver(schema),
  });
}

/**
 * Apply API errors to React Hook Form. Field-level when possible; otherwise root.
 */
export function applyApiErrorToForm<TFieldValues extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<TFieldValues>,
  fallbackMessage = "Something went wrong.",
): void {
  const fieldErrors = getFieldErrors(error);
  let appliedField = false;

  for (const [field, message] of Object.entries(fieldErrors)) {
    if (field === "root") {
      continue;
    }
    setError(field as Path<TFieldValues>, { type: "server", message });
    appliedField = true;
  }

  if (fieldErrors.root) {
    setError("root", { type: "server", message: fieldErrors.root });
    return;
  }

  if (!appliedField) {
    setError("root", {
      type: "server",
      message: getErrorMessage(error, fallbackMessage),
    });
  } else if (isApiError(error) && error.code === "VALIDATION_ERROR") {
    // Field errors already applied; keep a concise summary only when helpful.
  }
}

export type AuthFormReturn<T extends FieldValues> = UseFormReturn<T>;
