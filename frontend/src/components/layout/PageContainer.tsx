import type { ReactNode } from "react";

type PageContainerProps = {
  children: ReactNode;
  narrow?: boolean;
};

export function PageContainer({ children, narrow = false }: PageContainerProps) {
  return (
    <div
      className={narrow ? "page-container page-container--narrow" : "page-container"}
    >
      {children}
    </div>
  );
}
