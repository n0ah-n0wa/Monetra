import { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/features/auth/hooks";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";
import { safeInternalPath } from "@/lib/navigation";
import { routes } from "@/lib/routes";

type LocationState = {
  from?: string;
  reason?: "session-expired";
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as LocationState | null) ?? null;
  const { login, isLoggingIn, sessionExpired, clearSessionExpired } = useAuth();
  const form = useZodForm<LoginFormValues>(loginSchema, {
    defaultValues: { email: "", password: "" },
    mode: "onSubmit",
  });

  useEffect(() => {
    return () => {
      clearSessionExpired();
    };
  }, [clearSessionExpired]);

  const showSessionExpired =
    sessionExpired || locationState?.reason === "session-expired";

  const onSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await login(values);
      const redirectTo = safeInternalPath(locationState?.from, routes.dashboard);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to sign in.");
    }
  });

  return (
    <AuthLayout pageTitle="Sign in">
      <Card>
        <CardHeader>
          <CardTitle aria-hidden="true">Sign in</CardTitle>
          <CardDescription>Access your Monetra dashboard.</CardDescription>
        </CardHeader>
        <CardContent>
          {showSessionExpired ? (
            <Alert variant="warning" title="Session expired" className="auth-alert">
              Your session ended. Sign in again to continue.
            </Alert>
          ) : null}
          <form
            className="stack"
            onSubmit={(event) => void onSubmit(event)}
            noValidate
            aria-busy={isLoggingIn}
          >
            <FormField
              id="email"
              label="Email"
              required
              error={form.formState.errors.email}
            >
              <Input
                id="email"
                type="email"
                autoComplete="email"
                inputMode="email"
                autoFocus
                hasError={Boolean(form.formState.errors.email)}
                {...form.register("email")}
              />
            </FormField>
            <FormField
              id="password"
              label="Password"
              required
              error={form.formState.errors.password}
            >
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                hasError={Boolean(form.formState.errors.password)}
                {...form.register("password")}
              />
            </FormField>
            {form.formState.errors.root ? (
              <FormError>{form.formState.errors.root.message}</FormError>
            ) : null}
            <Button type="submit" loading={isLoggingIn}>
              Sign in
            </Button>
          </form>
          <nav className="auth-links" aria-label="Account links">
            <Link to={routes.forgotPassword}>Forgot password?</Link>
            <Link to={routes.register}>Create an account</Link>
          </nav>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
