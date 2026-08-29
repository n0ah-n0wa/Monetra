import { Link, useSearchParams } from "react-router-dom";
import { useEffect } from "react";
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
  resetPasswordSchema,
  type ResetPasswordFormValues,
} from "@/features/auth/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";
import { routes } from "@/lib/routes";

export function ResetPasswordPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tokenFromQuery = searchParams.get("token") ?? "";
  const hadTokenInUrl = tokenFromQuery.length > 0;

  const form = useZodForm<ResetPasswordFormValues>(resetPasswordSchema, {
    defaultValues: {
      token: tokenFromQuery,
      new_password: "",
      confirm_password: "",
    },
    mode: "onSubmit",
  });

  useEffect(() => {
    if (!tokenFromQuery) {
      return;
    }
    form.setValue("token", tokenFromQuery);
    setSearchParams({}, { replace: true });
  }, [form, setSearchParams, tokenFromQuery]);

  const mutation = useMutation({
    mutationFn: authApi.confirmPasswordReset,
  });

  const onSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await mutation.mutateAsync({
        token: values.token,
        new_password: values.new_password,
      });
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to reset password.");
    }
  });

  return (
    <AuthLayout pageTitle="Reset password">
      <Card>
        <CardHeader>
          <CardTitle aria-hidden="true">Choose a new password</CardTitle>
          <CardDescription>
            {hadTokenInUrl
              ? "Enter and confirm your new password."
              : "Paste your reset token, then choose a new password."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mutation.isSuccess ? (
            <div className="stack">
              <Alert variant="success" title="Password updated">
                Your password has been reset. You can now sign in.
              </Alert>
              <Link className="btn btn--primary btn--md" to={routes.login}>
                Go to sign in
              </Link>
            </div>
          ) : (
            <form
              className="stack"
              onSubmit={(event) => void onSubmit(event)}
              noValidate
              aria-busy={mutation.isPending}
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
                description="At least 8 characters with one letter and one number."
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
              {form.formState.errors.root ? (
                <FormError>{form.formState.errors.root.message}</FormError>
              ) : null}
              <Button type="submit" loading={mutation.isPending}>
                Update password
              </Button>
            </form>
          )}
          {!mutation.isSuccess ? (
            <nav className="auth-links" aria-label="Account links">
              <Link to={routes.login}>Back to sign in</Link>
            </nav>
          ) : null}
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
