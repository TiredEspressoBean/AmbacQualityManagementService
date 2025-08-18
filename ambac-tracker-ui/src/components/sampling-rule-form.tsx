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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ruleTypes } from "@/lib/RuleTypesEnum.ts";

const samplingRuleSchema = z.object({
  rule_type: z.string().min(1, "Rule type is required"),
  value: z.number().nullable().optional(),
  order: z.number().min(0, "Order must be 0 or greater"),
});

type FormSchema = z.infer<typeof samplingRuleSchema>;

interface SamplingRuleFormProps {
  existingRule?: {
    id?: string;
    rule_type: string;
    value: number | null;
    order: number;
  };
  onSuccess?: (rule: FormSchema) => void;
  onCancel?: () => void;
}

export default function SamplingRuleForm({
  existingRule,
  onSuccess,
  onCancel,
}: SamplingRuleFormProps) {
  const isEditing = !!existingRule;
  
  const form = useForm<FormSchema>({
    resolver: zodResolver(samplingRuleSchema),
    defaultValues: {
      rule_type: existingRule?.rule_type || "",
      value: existingRule?.value || null,
      order: existingRule?.order || 1,
    },
  });

  function onSubmit(values: FormSchema) {
    onSuccess?.(values);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="rule_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Rule Type *</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select rule type" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {ruleTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Type of sampling rule to apply
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="value"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Value</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  placeholder="e.g. 10"
                  {...field}
                  value={field.value || ""}
                  onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                />
              </FormControl>
              <FormDescription>
                Numeric value for this rule
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="order"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Order</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  placeholder="1"
                  min="1"
                  {...field}
                  onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                />
              </FormControl>
              <FormDescription>
                Order in which this rule should be applied (1 = first)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end space-x-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit">
            {isEditing ? "Update" : "Create"}
          </Button>
        </div>
      </form>
    </Form>
  );
}