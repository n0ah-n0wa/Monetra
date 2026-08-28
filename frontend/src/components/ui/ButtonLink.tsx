import type { ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";
import { cn } from "@/lib/utils";

type ButtonLinkVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonLinkSize = "sm" | "md" | "lg";

type ButtonLinkProps = LinkProps & {
  variant?: ButtonLinkVariant;
  size?: ButtonLinkSize;
  children: ReactNode;
};

export function ButtonLink({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={cn("btn", `btn--${variant}`, `btn--${size}`, className)}
      {...props}
    >
      {children}
    </Link>
  );
}
