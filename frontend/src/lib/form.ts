import { zodResolver } from "@hookform/resolvers/zod";
import type { FieldValues, UseFormProps } from "react-hook-form";
import { useForm } from "react-hook-form";
import type { ZodType } from "zod";

export function useZodForm<TFieldValues extends FieldValues>(
  schema: ZodType<TFieldValues>,
  options?: Omit<UseFormProps<TFieldValues>, "resolver">,
) {
  return useForm<TFieldValues>({
    ...options,
    resolver: zodResolver(schema),
  });
}
