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
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas";
import { useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoggingIn } = useAuth();
  const form = useZodForm<LoginFormValues>(loginSchema, {
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await login(values);
      navigate(routes.dashboard, { replace: true });
    } catch (error) {
      form.setError("root", { message: getErrorMessage(error, "Unable to sign in.") });
    }
  });

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Access your Monetra dashboard.</CardDescription>
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
          <p className="auth-links">
            <Link to={routes.forgotPassword}>Forgot password?</Link>
            <Link to={routes.register}>Create an account</Link>
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
