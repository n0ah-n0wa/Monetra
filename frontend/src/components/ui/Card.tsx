import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type CardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

export function Card({ children, className, ...props }: CardProps) {
  return (
    <section className={cn("card", className)} {...props}>
      {children}
    </section>
  );
}

export function CardHeader({ children, className, ...props }: CardProps) {
  return (
    <header className={cn("card__header", className)} {...props}>
      {children}
    </header>
  );
}

export function CardTitle({ children, className, ...props }: CardProps) {
  return (
    <h2 className={cn("card__title", className)} {...props}>
      {children}
    </h2>
  );
}

export function CardDescription({ children, className, ...props }: CardProps) {
  return (
    <p className={cn("card__description", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ children, className, ...props }: CardProps) {
  return (
    <div className={cn("card__content", className)} {...props}>
      {children}
    </div>
  );
}
