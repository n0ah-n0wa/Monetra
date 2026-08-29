import { Link, useNavigate } from "react-router-dom";
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
import { registerSchema, type RegisterFormValues } from "@/features/auth/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isRegistering } = useAuth();
  const form = useZodForm<RegisterFormValues>(registerSchema, {
    defaultValues: { email: "", password: "" },
    mode: "onSubmit",
  });

  const onSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await register(values);
      navigate(routes.dashboard, { replace: true });
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create account.");
    }
  });

  return (
    <AuthLayout pageTitle="Create account">
      <Card>
        <CardHeader>
          <CardTitle aria-hidden="true">Create account</CardTitle>
          <CardDescription>Start tracking your finances with Monetra.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="stack"
            onSubmit={(event) => void onSubmit(event)}
            noValidate
            aria-busy={isRegistering}
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
              description="At least 8 characters with one letter and one number."
              error={form.formState.errors.password}
            >
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                hasError={Boolean(form.formState.errors.password)}
                {...form.register("password")}
              />
            </FormField>
            {form.formState.errors.root ? (
              <FormError>{form.formState.errors.root.message}</FormError>
            ) : null}
            <Button type="submit" loading={isRegistering}>
              Create account
            </Button>
          </form>
          <nav className="auth-links" aria-label="Account links">
            <Link to={routes.login}>Already have an account? Sign in</Link>
          </nav>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
