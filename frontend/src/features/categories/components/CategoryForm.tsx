import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  CATEGORY_TYPES,
  formatCategoryType,
  type Category,
} from "@/features/categories/api";
import {
  categoryCreateSchema,
  categoryUpdateSchema,
  type CategoryCreateFormValues,
  type CategoryUpdateFormValues,
} from "@/features/categories/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

type CategoryCreateFormProps = {
  submitting?: boolean;
  onSubmit: (values: CategoryCreateFormValues) => Promise<void>;
  onCancel?: () => void;
};

export function CategoryCreateForm({
  submitting = false,
  onSubmit,
  onCancel,
}: CategoryCreateFormProps) {
  const form = useZodForm<CategoryCreateFormValues>(categoryCreateSchema, {
    defaultValues: {
      name: "",
      category_type: "expense",
      icon: "",
      color: "",
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(values);
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create category.");
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <FormField id="name" label="Name" required error={form.formState.errors.name}>
        <Input
          id="name"
          autoComplete="off"
          autoFocus
          hasError={Boolean(form.formState.errors.name)}
          {...form.register("name")}
        />
      </FormField>
      <FormField
        id="category_type"
        label="Type"
        required
        error={form.formState.errors.category_type}
      >
        <Select
          id="category_type"
          hasError={Boolean(form.formState.errors.category_type)}
          {...form.register("category_type")}
        >
          {CATEGORY_TYPES.map((type) => (
            <option key={type} value={type}>
              {formatCategoryType(type)}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField id="icon" label="Icon" error={form.formState.errors.icon}>
        <Input
          id="icon"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.icon)}
          {...form.register("icon")}
        />
      </FormField>
      <FormField
        id="color"
        label="Color"
        description="Optional CSS color value."
        error={form.formState.errors.color}
      >
        <Input
          id="color"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.color)}
          {...form.register("color")}
        />
      </FormField>
      {form.formState.errors.root ? (
        <FormError>{form.formState.errors.root.message}</FormError>
      ) : null}
      <div className="modal__actions">
        {onCancel ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" loading={submitting}>
          Create category
        </Button>
      </div>
    </form>
  );
}

type CategoryEditFormProps = {
  category: Category;
  submitting?: boolean;
  onSubmit: (values: CategoryUpdateFormValues) => Promise<void>;
  onCancel?: () => void;
};

export function CategoryEditForm({
  category,
  submitting = false,
  onSubmit,
  onCancel,
}: CategoryEditFormProps) {
  const form = useZodForm<CategoryUpdateFormValues>(categoryUpdateSchema, {
    defaultValues: {
      name: category.name,
      icon: category.icon ?? "",
      color: category.color ?? "",
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(values);
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to update category.");
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <FormField id="name" label="Name" required error={form.formState.errors.name}>
        <Input
          id="name"
          autoComplete="off"
          autoFocus
          hasError={Boolean(form.formState.errors.name)}
          {...form.register("name")}
        />
      </FormField>
      <FormField id="icon" label="Icon" error={form.formState.errors.icon}>
        <Input
          id="icon"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.icon)}
          {...form.register("icon")}
        />
      </FormField>
      <FormField id="color" label="Color" error={form.formState.errors.color}>
        <Input
          id="color"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.color)}
          {...form.register("color")}
        />
      </FormField>
      <p className="form-field__description">
        Category type is fixed after creation (
        {formatCategoryType(category.category_type)}
        ).
      </p>
      {form.formState.errors.root ? (
        <FormError>{form.formState.errors.root.message}</FormError>
      ) : null}
      <div className="modal__actions">
        {onCancel ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" loading={submitting}>
          Save changes
        </Button>
      </div>
    </form>
  );
}
