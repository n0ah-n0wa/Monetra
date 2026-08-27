import {
  Children,
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
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
  const describedBy = [descriptionId, errorId].filter(Boolean).join(" ") || undefined;

  const enhancedChildren = Children.map(children, (child) => {
    if (!isValidElement(child)) {
      return child;
    }
    const element = child as ReactElement<{
      id?: string;
      "aria-invalid"?: boolean;
      "aria-describedby"?: string;
      "aria-required"?: boolean;
    }>;
    return cloneElement(element, {
      id: element.props.id ?? id,
      "aria-invalid": error ? true : undefined,
      "aria-required": required || undefined,
      "aria-describedby": describedBy,
    });
  });

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
      {enhancedChildren}
      {error ? (
        <p id={errorId} className="form-field__error" role="alert">
          {error.message}
        </p>
      ) : null}
    </div>
  );
}
