import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { AuthLayout } from "@/components/layout/AuthLayout";
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
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
} from "@/features/auth/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function ForgotPasswordPage() {
  const form = useZodForm<ForgotPasswordFormValues>(forgotPasswordSchema, {
    defaultValues: { email: "" },
    mode: "onSubmit",
  });

  const mutation = useMutation({
    mutationFn: authApi.requestPasswordReset,
  });

  const onSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await mutation.mutateAsync(values);
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to request a password reset.");
    }
  });

  return (
    <AuthLayout pageTitle="Forgot password">
      <Card>
        <CardHeader>
          <CardTitle aria-hidden="true">Forgot password</CardTitle>
          <CardDescription>
            Request a password reset. Email delivery must be configured by the operator;
            otherwise use the reset token from server logs in development.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mutation.isSuccess ? (
            <Alert variant="success" title="Reset requested">
              If an account exists and email delivery is configured, reset instructions
              have been sent. Otherwise contact your administrator or check server logs
              in development.
            </Alert>
          ) : (
            <form
              className="stack"
              onSubmit={(event) => void onSubmit(event)}
              noValidate
              aria-busy={mutation.isPending}
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
              {form.formState.errors.root ? (
                <FormError>{form.formState.errors.root.message}</FormError>
              ) : null}
              <Button type="submit" loading={mutation.isPending}>
                Send reset link
              </Button>
            </form>
          )}
          <nav className="auth-links" aria-label="Account links">
            <Link to={routes.login}>Back to sign in</Link>
          </nav>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
