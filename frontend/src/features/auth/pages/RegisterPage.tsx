import { Link, useNavigate } from "react-router-dom";
import { getErrorMessage } from "@/api/errors";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { AuthLayout } from "@/components/layout/AppShell";
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
import { useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isRegistering } = useAuth();
  const form = useZodForm<RegisterFormValues>(registerSchema, {
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await register(values);
      navigate(routes.dashboard, { replace: true });
    } catch (error) {
      form.setError("root", {
        message: getErrorMessage(error, "Unable to create account."),
      });
    }
  });

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>Create account</CardTitle>
          <CardDescription>Start tracking your finances with Monetra.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="stack" onSubmit={(event) => void onSubmit(event)} noValidate>
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
          <p className="auth-links">
            <Link to={routes.login}>Already have an account?</Link>
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
