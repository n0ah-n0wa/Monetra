import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z
    .string()
    .min(1, "Password is required.")
    .max(128, "Password must be 128 characters or fewer."),
});

export const registerSchema = loginSchema;

export const forgotPasswordSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
});

export const resetPasswordSchema = z
  .object({
    token: z
      .string()
      .min(1, "Reset token is required.")
      .max(256, "Reset token is too long."),
    new_password: z
      .string()
      .min(1, "Password is required.")
      .max(128, "Password must be 128 characters or fewer."),
    confirm_password: z.string().min(1, "Confirm your password."),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: "Passwords must match.",
    path: ["confirm_password"],
  });

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;
