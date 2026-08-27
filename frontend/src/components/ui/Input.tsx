import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  hasError?: boolean;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, hasError, ...props },
  ref,
) {
  const ariaInvalid = hasError || props["aria-invalid"] ? true : props["aria-invalid"];

  return (
    <input
      ref={ref}
      className={cn("input", hasError && "input--error", className)}
      {...props}
      aria-invalid={ariaInvalid}
    />
  );
});
