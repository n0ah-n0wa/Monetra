import { z } from "zod";
import { CATEGORY_TYPES } from "@/features/categories/api";

export const categoryCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Category name is required.")
    .max(120, "Category name must be 120 characters or fewer."),
  category_type: z.enum(CATEGORY_TYPES, {
    required_error: "Select a category type.",
  }),
  icon: z.string().trim().max(64).optional().or(z.literal("")),
  color: z.string().trim().max(32).optional().or(z.literal("")),
});

export const categoryUpdateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Category name is required.")
    .max(120, "Category name must be 120 characters or fewer."),
  icon: z.string().trim().max(64).optional().or(z.literal("")),
  color: z.string().trim().max(32).optional().or(z.literal("")),
});

export type CategoryCreateFormValues = z.infer<typeof categoryCreateSchema>;
export type CategoryUpdateFormValues = z.infer<typeof categoryUpdateSchema>;
