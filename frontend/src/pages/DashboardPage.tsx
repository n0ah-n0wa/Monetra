import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { BudgetUtilizationWidget } from "@/features/dashboard/components/BudgetUtilizationWidget";
import { FinancialGoalsWidget } from "@/features/dashboard/components/FinancialGoalsWidget";
import { FinancialInsightsWidget } from "@/features/dashboard/components/FinancialInsightsWidget";
import { RecentTransactionsWidget } from "@/features/dashboard/components/RecentTransactionsWidget";
import { SpendingByCategoryWidget } from "@/features/dashboard/components/SpendingByCategoryWidget";
import {
  SummaryStatsLinks,
  SummaryStatsRow,
} from "@/features/dashboard/components/SummaryStatsWidget";
import { useAuth } from "@/features/auth/hooks";

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description={
          user
            ? `Welcome back. Reporting in ${user.reporting_currency}.`
            : "Your financial overview."
        }
      />

      <SummaryStatsRow />
      <SummaryStatsLinks />

      <div className="dashboard-layout">
        <div className="dashboard-layout__primary">
          <SpendingByCategoryWidget />
          <RecentTransactionsWidget />
        </div>
        <div className="dashboard-layout__secondary">
          <FinancialInsightsWidget />
          <BudgetUtilizationWidget />
          <FinancialGoalsWidget />
        </div>
      </div>
    </PageContainer>
  );
}
