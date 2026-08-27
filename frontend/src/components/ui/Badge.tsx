import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "neutral" | "success" | "warning" | "info";

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
};

export function Badge({ children, variant = "neutral", className }: BadgeProps) {
  return (
    <span className={cn("badge", `badge--${variant}`, className)}>{children}</span>
  );
}
