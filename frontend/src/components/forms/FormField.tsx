import type { ReactNode } from "react";
import type { FieldError } from "react-hook-form";
import { Label } from "@/components/ui/Label";
import { cn } from "@/lib/utils";

type FormFieldProps = {
  id: string;
  label: string;
  error?: FieldError;
  required?: boolean;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function FormField({
  id,
  label,
  error,
  required,
  description,
  children,
  className,
}: FormFieldProps) {
  const errorId = error ? `${id}-error` : undefined;
  const descriptionId = description ? `${id}-description` : undefined;

  return (
    <div className={cn("form-field", className)}>
      <Label htmlFor={id} required={required}>
        {label}
      </Label>
      {description ? (
        <p id={descriptionId} className="form-field__description">
          {description}
        </p>
      ) : null}
      <div aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}>
        {children}
      </div>
      {error ? (
        <p id={errorId} className="form-field__error" role="alert">
          {error.message}
        </p>
      ) : null}
    </div>
  );
}
