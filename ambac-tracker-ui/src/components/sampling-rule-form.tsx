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
import { isFieldRequired } from "@/lib/zod-config";

const samplingRuleSchema = z.object({
  rule_type: z.string().min(1, "Rule type is required"),
  value: z.number().nullable().optional(),
  order: z.number().min(0, "Order must be 0 or greater"),
});

type FormSchema = z.infer<typeof samplingRuleSchema>;

const required = {
  rule_type: isFieldRequired(samplingRuleSchema.shape.rule_type),
};

/** Configuration for each rule type */
const ruleTypeConfig: Record<string, {
  help: string;
  valueLabel: string;
  valuePlaceholder: string;
  valueRequired: boolean;
  valueMin?: number;
  valueMax?: number;
}> = {
  every_nth_part: {
    help: "Inspect every Nth part in sequence. E.g., value of 5 means parts 5, 10, 15... (20% coverage)",
    valueLabel: "Sample every N parts",
    valuePlaceholder: "5",
    valueRequired: true,
    valueMin: 1,
  },
  percentage: {
    help: "Randomly select X% of parts for inspection. Good for statistical sampling.",
    valueLabel: "Percentage (%)",
    valuePlaceholder: "10",
    valueRequired: true,
    valueMin: 0,
    valueMax: 100,
  },
  random: {
    help: "Pure random sampling - each part has an equal chance of being selected.",
    valueLabel: "Sample rate (%)",
    valuePlaceholder: "10",
    valueRequired: false,
    valueMin: 0,
    valueMax: 100,
  },
  random_within_n: {
    help: "Randomly select one part from each group of N consecutive parts.",
    valueLabel: "Group size (N)",
    valuePlaceholder: "10",
    valueRequired: true,
    valueMin: 1,
  },
  first_n_parts: {
    help: "Always inspect the first N parts of each batch. Useful for startup validation.",
    valueLabel: "Number of parts",
    valuePlaceholder: "5",
    valueRequired: true,
    valueMin: 1,
  },
  last_n_parts: {
    help: "Always inspect the last N parts of each batch. Useful for end-of-run validation.",
    valueLabel: "Number of parts",
    valuePlaceholder: "5",
    valueRequired: true,
    valueMin: 1,
  },
  all: {
    help: "100% inspection - every part is sampled. Use for critical processes.",
    valueLabel: "Value",
    valuePlaceholder: "",
    valueRequired: false,
  },
  none: {
    help: "Skip sampling at this step. Parts pass through without inspection.",
    valueLabel: "Value",
    valuePlaceholder: "",
    valueRequired: false,
  },
};

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

  const watchedRuleType = form.watch("rule_type");
  const config = ruleTypeConfig[watchedRuleType] || {
    help: "Select a rule type to see details",
    valueLabel: "Value",
    valuePlaceholder: "",
    valueRequired: false,
  };

  // Hide value field for rules that don't need it
  const showValueField = watchedRuleType !== "all" && watchedRuleType !== "none";

  function onSubmit(e: React.FormEvent, values: FormSchema) {
    e.stopPropagation();
    onSuccess?.(values);
  }

  return (
    <Form {...form}>
      <form
        onSubmit={(e) => {
          e.stopPropagation();
          form.handleSubmit((values) => onSubmit(e, values))(e);
        }}
        className="space-y-4"
      >
        <FormField
          control={form.control}
          name="rule_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel required={required.rule_type}>Rule Type</FormLabel>
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
              <FormDescription className="text-xs">
                {config.help}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {showValueField && (
          <FormField
            control={form.control}
            name="value"
            render={({ field }) => (
              <FormItem>
                <FormLabel required={config.valueRequired}>
                  {config.valueLabel}
                </FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    placeholder={config.valuePlaceholder}
                    min={config.valueMin}
                    max={config.valueMax}
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                  />
                </FormControl>
                {config.valueMin !== undefined && config.valueMax !== undefined && (
                  <FormDescription className="text-xs">
                    Range: {config.valueMin} - {config.valueMax}
                  </FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />
        )}

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