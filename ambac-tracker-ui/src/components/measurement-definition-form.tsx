"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCreateMeasurementDefinition } from "@/hooks/useCreateMeasurementDefinition";
import { useUpdateMeasurementDefinition } from "@/hooks/useUpdateMeasurementDefinition";
import { toast } from "sonner";

const measurementDefinitionSchema = z.object({
  label: z.string().min(1, "Label is required").max(100, "Label must be 100 characters or less"),
  type: z.enum(["NUMERIC", "PASS_FAIL"], { required_error: "Type is required" }),
  unit: z.string().max(50, "Unit must be 50 characters or less").optional(),
  nominal: z.string().nullable().optional(),
  upper_tol: z.string().nullable().optional(),
  lower_tol: z.string().nullable().optional(),
  required: z.boolean().default(true),
});

type FormSchema = z.infer<typeof measurementDefinitionSchema>;

interface MeasurementDefinitionFormProps {
  stepId: number;
  existingDefinition?: {
    id: number;
    label: string;
    type: "NUMERIC" | "PASS_FAIL";
    unit?: string;
    nominal?: string | null;
    upper_tol?: string | null;
    lower_tol?: string | null;
    required?: boolean;
  };
  onSuccess?: () => void;
  onCancel?: () => void;
}

export default function MeasurementDefinitionForm({
  stepId,
  existingDefinition,
  onSuccess,
  onCancel,
}: MeasurementDefinitionFormProps) {
  const isEditing = !!existingDefinition;
  
  const form = useForm<FormSchema>({
    resolver: zodResolver(measurementDefinitionSchema),
    defaultValues: {
      label: existingDefinition?.label || "",
      type: existingDefinition?.type || "NUMERIC",
      unit: existingDefinition?.unit || "",
      nominal: existingDefinition?.nominal || null,
      upper_tol: existingDefinition?.upper_tol || null,
      lower_tol: existingDefinition?.lower_tol || null,
      required: existingDefinition?.required ?? true,
    },
  });

  const createMutation = useCreateMeasurementDefinition();
  const updateMutation = useUpdateMeasurementDefinition();

  const watchedType = form.watch("type");
  const isNumeric = watchedType === "NUMERIC";

  function onSubmit(values: FormSchema) {
    const submitData = {
      ...values,
      step: stepId,
      // Clean up numeric fields for PASS_FAIL type
      ...(values.type === "PASS_FAIL" && {
        nominal: null,
        upper_tol: null,
        lower_tol: null,
        unit: "",
      }),
    };

    if (isEditing) {
      updateMutation.mutate(
        { params: { id: existingDefinition.id }, body: submitData },
        {
          onSuccess: () => {
            toast.success("Measurement definition updated successfully!");
            onSuccess?.();
          },
          onError: (error) => {
            console.error("Failed to update measurement definition:", error);
            toast.error("Failed to update measurement definition.");
          },
        }
      );
    } else {
      createMutation.mutate(
        { body: submitData },
        {
          onSuccess: () => {
            toast.success("Measurement definition created successfully!");
            form.reset();
            onSuccess?.();
          },
          onError: (error) => {
            console.error("Failed to create measurement definition:", error);
            toast.error("Failed to create measurement definition.");
          },
        }
      );
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="label"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Label *</FormLabel>
              <FormControl>
                <Input placeholder="e.g. Outer Diameter" {...field} />
              </FormControl>
              <FormDescription>
                Descriptive name for this measurement
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Type *</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select measurement type" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="NUMERIC">Numeric</SelectItem>
                  <SelectItem value="PASS_FAIL">Pass/Fail</SelectItem>
                </SelectContent>
              </Select>
              <FormDescription>
                Type of measurement to be taken
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {isNumeric && (
          <>
            <FormField
              control={form.control}
              name="unit"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Unit</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. mm, psi, °C" {...field} />
                  </FormControl>
                  <FormDescription>
                    Unit of measurement (optional)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="nominal"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nominal</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="any"
                        placeholder="0.00"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormDescription>Target value</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="upper_tol"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Upper Tolerance</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="any"
                        placeholder="0.00"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormDescription>Maximum value</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="lower_tol"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Lower Tolerance</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="any"
                        placeholder="0.00"
                        {...field}
                        value={field.value || ""}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormDescription>Minimum value</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </>
        )}

        <FormField
          control={form.control}
          name="required"
          render={({ field }) => (
            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
              <FormControl>
                <Checkbox checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel>Required</FormLabel>
                <FormDescription>
                  Must be measured to complete step
                </FormDescription>
              </div>
            </FormItem>
          )}
        />

        <div className="flex justify-end space-x-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
          >
            {isEditing
              ? updateMutation.isPending
                ? "Updating..."
                : "Update"
              : createMutation.isPending
              ? "Creating..."
              : "Create"}
          </Button>
        </div>
      </form>
    </Form>
  );
}