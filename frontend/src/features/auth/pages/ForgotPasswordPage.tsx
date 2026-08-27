import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { AuthLayout } from "@/components/layout/AppShell";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import * as authApi from "@/features/auth/api";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "@/features/auth/schemas";
import { useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function ForgotPasswordPage() {
  const form = useZodForm<ForgotPasswordFormValues>(forgotPasswordSchema, {
    defaultValues: { email: "" },
  });

  const mutation = useMutation({
    mutationFn: authApi.requestPasswordReset,
  });

  const onSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync(values);
  });

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>Reset password</CardTitle>
          <CardDescription>We will email reset instructions if the account exists.</CardDescription>
        </CardHeader>
        <CardContent>
          {mutation.isSuccess ? (
            <Alert variant="success" title="Check your inbox">
              If an account exists for that email, reset instructions have been sent.
            </Alert>
          ) : (
            <form className="stack" onSubmit={(event) => void onSubmit(event)} noValidate>
              <FormField id="email" label="Email" required error={form.formState.errors.email}>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  hasError={Boolean(form.formState.errors.email)}
                  {...form.register("email")}
                />
              </FormField>
              <FormError error={mutation.error} />
              <Button type="submit" loading={mutation.isPending}>
                Send reset link
              </Button>
            </form>
          )}
          <p className="auth-links">
            <Link to={routes.login}>Back to sign in</Link>
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
