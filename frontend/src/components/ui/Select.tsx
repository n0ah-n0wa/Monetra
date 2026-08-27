import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  hasError?: boolean;
};

export function Select({ className, hasError, children, ...props }: SelectProps) {
  const ariaInvalid = hasError || props["aria-invalid"] ? true : props["aria-invalid"];

  return (
    <select
      className={cn("input select", hasError && "input--error", className)}
      {...props}
      aria-invalid={ariaInvalid}
    >
      {children}
    </select>
  );
}
