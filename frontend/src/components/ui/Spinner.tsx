import { cn } from "@/lib/utils";

type SpinnerProps = {
  className?: string;
  size?: "sm" | "md" | "lg";
};

export function Spinner({ className, size = "md" }: SpinnerProps) {
  return (
    <div className={cn("spinner", `spinner--${size}`, className)} aria-hidden="true">
      <span className="spinner__circle" />
    </div>
  );
}
