import type { LabelHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type LabelProps = LabelHTMLAttributes<HTMLLabelElement> & {
  children: ReactNode;
  required?: boolean;
};

export function Label({ children, required, className, ...props }: LabelProps) {
  return (
    <label className={cn("label", className)} {...props}>
      {children}
      {required ? <span className="label__required">*</span> : null}
    </label>
  );
}
