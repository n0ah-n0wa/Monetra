import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { AuthLayout } from "@/components/layout/AppShell";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import * as authApi from "@/features/auth/api";
import {
  resetPasswordSchema,
  type ResetPasswordFormValues,
} from "@/features/auth/schemas";
import { useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const tokenFromQuery = searchParams.get("token") ?? "";

  const form = useZodForm<ResetPasswordFormValues>(resetPasswordSchema, {
    defaultValues: {
      token: tokenFromQuery,
      new_password: "",
      confirm_password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: authApi.confirmPasswordReset,
  });

  const onSubmit = form.handleSubmit(async (values) => {
    await mutation.mutateAsync({
      token: values.token,
      new_password: values.new_password,
    });
  });

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>Choose a new password</CardTitle>
          <CardDescription>
            Enter the reset token and your new password.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mutation.isSuccess ? (
            <Alert variant="success" title="Password updated">
              Your password has been reset. You can now sign in.
            </Alert>
          ) : (
            <form
              className="stack"
              onSubmit={(event) => void onSubmit(event)}
              noValidate
            >
              <FormField
                id="token"
                label="Reset token"
                required
                error={form.formState.errors.token}
              >
                <Input
                  id="token"
                  autoComplete="one-time-code"
                  hasError={Boolean(form.formState.errors.token)}
                  {...form.register("token")}
                />
              </FormField>
              <FormField
                id="new_password"
                label="New password"
                required
                error={form.formState.errors.new_password}
              >
                <Input
                  id="new_password"
                  type="password"
                  autoComplete="new-password"
                  hasError={Boolean(form.formState.errors.new_password)}
                  {...form.register("new_password")}
                />
              </FormField>
              <FormField
                id="confirm_password"
                label="Confirm password"
                required
                error={form.formState.errors.confirm_password}
              >
                <Input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  hasError={Boolean(form.formState.errors.confirm_password)}
                  {...form.register("confirm_password")}
                />
              </FormField>
              <FormError error={mutation.error} />
              <Button type="submit" loading={mutation.isPending}>
                Update password
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
