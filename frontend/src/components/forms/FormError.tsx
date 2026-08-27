import type { ReactNode } from "react";
import { getErrorMessage } from "@/api/errors";
import { Alert } from "@/components/ui/Alert";

type FormErrorProps = {
  error?: unknown;
  children?: ReactNode;
};

export function FormError({ error, children }: FormErrorProps) {
  if (!error && !children) {
    return null;
  }

  return (
    <Alert variant="error" title="Unable to submit form">
      {children ?? getErrorMessage(error)}
    </Alert>
  );
}
