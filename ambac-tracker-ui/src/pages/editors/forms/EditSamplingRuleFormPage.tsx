"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useParams } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Form,
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormDescription,
    FormMessage,
} from "@/components/ui/form";
import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectItem,
    SelectValue,
} from "@/components/ui/select";

import { useRetrieveSamplingRule } from "@/hooks/useRetrieveSamplingRule";
import { useCreateSamplingRule } from "@/hooks/useCreateSamplingRule";
import { useUpdateSamplingRule } from "@/hooks/useUpdateSamplingRule";
import { useRetrieveSamplingRulesSets } from "@/hooks/useRetrieveSamplingRulesSets";
import { useDebounce } from "@/hooks/useDebounce";
import {
    Popover,
    PopoverTrigger,
    PopoverContent,
} from "@/components/ui/popover";
import { Command, CommandInput, CommandEmpty, CommandGroup, CommandItem } from "@/components/ui/command";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {ruleTypes, ruleTypesEnum} from "@/lib/RuleTypesEnum.ts"
import {schemas} from "@/lib/api/generated";
import {isFieldRequired} from "@/lib/zod-config";

// Use generated schema for base fields, extend with form-specific validation
const samplingRuleFormSchema = schemas.SamplingRuleRequest.pick({
  ruleset: true,
  rule_type: true,
  order: true,
}).extend({
  // Override rule_type to use our local enum with labels
  rule_type: ruleTypesEnum,
  // Override value with form-specific validation (required with min/max)
  value: z
    .coerce.number()
    .min(1)
    .max(100),
});

export type SamplingRuleFormValues = z.infer<typeof samplingRuleFormSchema>;

const required = {
    ruleset: isFieldRequired(samplingRuleFormSchema.shape.ruleset),
    rule_type: isFieldRequired(samplingRuleFormSchema.shape.rule_type),
    value: isFieldRequired(samplingRuleFormSchema.shape.value),
};

export default function SamplingRuleFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const ruleId = params.id;

    const { data: rule } = useRetrieveSamplingRule(
        { params: { id: ruleId! } },
        { enabled: mode === "edit" && !!ruleId }
    );

    const [rulesetQuery, setRulesetQuery] = useState("");
    const debouncedQuery = useDebounce(rulesetQuery, 300);
    const { data: ruleSets = { results: [] } } = useRetrieveSamplingRulesSets({ search: debouncedQuery });

    const form = useForm<SamplingRuleFormValues>({
        resolver: zodResolver(samplingRuleFormSchema),
        defaultValues: {
            ruleset: undefined,
            rule_type: undefined,
            value: 1,
            order: undefined,
        },
    });

    useEffect(() => {
        if (mode === "edit" && rule) {
            form.reset({
                ruleset: rule.ruleset,
                rule_type: rule.rule_type,
                value: rule.value ?? 1,
                order: rule.order ?? undefined,
            });
        }
    }, [mode, rule, form]);

    const createSamplingRule = useCreateSamplingRule();
    const updateSamplingRule = useUpdateSamplingRule();

    const ruleTypeCode = form.watch("rule_type");

    function onSubmit(values: SamplingRuleFormValues) {
        const payload = {
            ruleset: values.ruleset,
            rule_type: values.rule_type,
            value: values.value,
            order: values.order,
        };

        if (mode === "edit" && ruleId) {
            updateSamplingRule.mutate(
                { id: ruleId, data: payload },
                {
                    onSuccess: () => toast.success("Sampling Rule updated successfully!"),
                    onError: (error) => {
                        console.error(error);
                        toast.error("Failed to update sampling rule.");
                    },
                }
            );
        } else {
            createSamplingRule.mutate(payload, {
                onSuccess: () => {
                    toast.success("Sampling Rule created successfully!");
                    form.reset();
                },
                onError: (error) => {
                    console.error(error);
                    toast.error("Failed to create sampling rule.");
                },
            });
        }
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                <FormField
                    control={form.control}
                    name="ruleset"
                    render={({ field }) => {
                        const selected = ruleSets.results.find(rs => rs.id === field.value);

                        return (
                            <FormItem>
                                <FormLabel required={required.ruleset}>Rule Set</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            className={cn("w-full justify-between", !selected && "text-muted-foreground")}
                                        >
                                            {selected ? selected.name : "Select Rule Set"}
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search rule sets..."
                                                value={rulesetQuery}
                                                onValueChange={setRulesetQuery}
                                            />
                                            <CommandEmpty>No rule sets found.</CommandEmpty>
                                            <CommandGroup>
                                                {ruleSets.results.map(rs => (
                                                    <CommandItem
                                                        key={rs.id}
                                                        value={rs.name}
                                                        onSelect={() => {
                                                            form.setValue("ruleset", rs.id);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                rs.id === field.value ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        {rs.name}
                                                    </CommandItem>
                                                ))}
                                            </CommandGroup>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Rule set this rule belongs to.</FormDescription>
                                <FormMessage />
                            </FormItem>
                        );
                    }}
                />

                <FormField
                    control={form.control}
                    name="rule_type"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel required={required.rule_type}>Rule Type</FormLabel>
                            <Select onValueChange={field.onChange} value={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Rule Type" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {ruleTypes.map((rt) => (
                                        <SelectItem key={rt.value} value={rt.value}>
                                            {rt.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormDescription>How this rule decides to sample.</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="value"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel required={required.value}>Sampling Rule Value</FormLabel>
                            <FormControl>
                                <Input type="number" {...field} />
                            </FormControl>
                            <FormDescription>
                                {ruleTypeCode === "percentage"
                                    ? "Percentage of parts to sample"
                                    : ruleTypeCode === "every_nth_part"
                                        ? "Fail threshold for escalation"
                                        : "Value of N for this rule"}
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
                            <FormLabel>Order (optional)</FormLabel>
                            <FormControl>
                                <Input type="number" placeholder="0" {...field} />
                            </FormControl>
                            <FormDescription>Determines evaluation priority. Lower = evaluated earlier.</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <Button type="submit" disabled={createSamplingRule.isPending || updateSamplingRule.isPending}>
                    {mode === "edit"
                        ? updateSamplingRule.isPending
                            ? "Saving..."
                            : "Save Changes"
                        : createSamplingRule.isPending
                            ? "Creating..."
                            : "Create Sampling Rule"}
                </Button>
            </form>
        </Form>
    );
}
