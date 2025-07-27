"use client"

import {
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useFieldArray, useFormContext } from "react-hook-form";
import { useEffect } from "react";
import { ruleTypes } from "@/lib/RuleTypesEnum.ts";

type SamplingRulesEditorProps = {
    name: string;   // e.g. "rules" or "fallback_rules"
    label?: string; // e.g. "Sampling Rules" or "Fallback Rules"
};

export default function SamplingRulesEditor({ name, label = "Sampling Rules" }: SamplingRulesEditorProps) {
    const { control, getValues, setValue } = useFormContext();

    const { fields, append, remove } = useFieldArray({ control, name });

    // Ensure initialized on mount
    useEffect(() => {
        const current = getValues(name);
        if (!Array.isArray(current)) {
            setValue(name, []);
        }
    }, [getValues, name, setValue]);

    return (
        <div className="space-y-4 border p-4 rounded-md">
            <h4 className="font-semibold">{label}</h4>

            {fields.map((field, index) => (
                <div key={field.id} className="grid grid-cols-3 gap-4 items-end">
                    <FormField
                        control={control}
                        name={`${name}.${index}.rule_type`}
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Type</FormLabel>
                                <Select
                                    onValueChange={field.onChange}
                                    value={field.value || ""}
                                >
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
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={control}
                        name={`${name}.${index}.value`}
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Value</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        value={field.value ?? ""}
                                        onChange={(e) => {
                                            const parsed = parseFloat(e.target.value);
                                            field.onChange(isNaN(parsed) ? null : parsed);
                                        }}
                                        placeholder="e.g. 10"
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <Button
                        type="button"
                        variant="destructive"
                        onClick={() => remove(index)}
                    >
                        Remove
                    </Button>
                </div>
            ))}

            <Button
                type="button"
                variant="outline"
                onClick={() => {
                    append({
                        rule_type: "",
                        value: null,
                        order: fields.length,
                    });
                }}
            >
                Add Rule
            </Button>
        </div>
    );
}
