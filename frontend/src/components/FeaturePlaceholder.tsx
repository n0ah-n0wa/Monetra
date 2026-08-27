import type { ReactNode } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";

type FeaturePlaceholderProps = {
  title: string;
  description: string;
  children?: ReactNode;
};

export function FeaturePlaceholder({
  title,
  description,
  children,
}: FeaturePlaceholderProps) {
  return (
    <PageContainer>
      <PageHeader title={title} description={description} />
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>
            This area is wired into routing and the API client. Detailed screens will be
            added in focused increments.
          </CardDescription>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </PageContainer>
  );
}
