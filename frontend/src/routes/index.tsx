import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { GuestRoute, ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { AnalyticsRoute } from "@/routes/AnalyticsRoute";
import { AccountDetailPage } from "@/features/accounts/pages/AccountDetailPage";
import { AccountsPage } from "@/features/accounts/pages/AccountsPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { BudgetDetailPage } from "@/features/budgets/pages/BudgetDetailPage";
import { BudgetsPage } from "@/features/budgets/pages/BudgetsPage";
import { CategoriesPage } from "@/features/categories/pages/CategoriesPage";
import { GoalDetailPage } from "@/features/goals/pages/GoalDetailPage";
import { GoalsPage } from "@/features/goals/pages/GoalsPage";
import { ImportPage } from "@/features/imports/pages/ImportPage";
import { RecurringTransactionDetailPage } from "@/features/recurring-transactions/pages/RecurringTransactionDetailPage";
import { RecurringTransactionsPage } from "@/features/recurring-transactions/pages/RecurringTransactionsPage";
import { NotificationsPage } from "@/features/notifications/pages/NotificationsPage";
import { SettingsPage } from "@/features/settings/pages/SettingsPage";
import { TransfersPage } from "@/features/transfers/pages/TransfersPage";
import { TransactionCreatePage } from "@/features/transactions/pages/TransactionCreatePage";
import { TransactionDetailPage } from "@/features/transactions/pages/TransactionDetailPage";
import { TransactionsPage } from "@/features/transactions/pages/TransactionsPage";
import { routes } from "@/lib/routes";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to={routes.dashboard} replace />,
  },
  {
    element: <GuestRoute />,
    children: [
      { path: routes.login, element: <LoginPage /> },
      { path: routes.register, element: <RegisterPage /> },
      { path: routes.forgotPassword, element: <ForgotPasswordPage /> },
      { path: routes.resetPassword, element: <ResetPasswordPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: routes.dashboard, element: <DashboardPage /> },
          { path: routes.accounts, element: <AccountsPage /> },
          { path: "/accounts/:id", element: <AccountDetailPage /> },
          { path: routes.transactions, element: <TransactionsPage /> },
          { path: routes.transfers, element: <TransfersPage /> },
          { path: routes.transactionNew, element: <TransactionCreatePage /> },
          { path: "/transactions/:id", element: <TransactionDetailPage /> },
          { path: routes.recurring, element: <RecurringTransactionsPage /> },
          { path: "/recurring/:id", element: <RecurringTransactionDetailPage /> },
          { path: routes.categories, element: <CategoriesPage /> },
          { path: routes.budgets, element: <BudgetsPage /> },
          { path: "/budgets/:id", element: <BudgetDetailPage /> },
          { path: routes.goals, element: <GoalsPage /> },
          { path: "/goals/:id", element: <GoalDetailPage /> },
          { path: routes.analytics, element: <AnalyticsRoute /> },
          { path: routes.import, element: <ImportPage /> },
          { path: routes.notifications, element: <NotificationsPage /> },
          { path: routes.settings, element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
