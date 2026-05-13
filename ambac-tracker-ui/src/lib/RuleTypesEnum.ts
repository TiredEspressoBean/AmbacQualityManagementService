import {z} from "zod";

// Must match backend SamplingRuleType choices in mes_lite.py
export const ruleTypes = [
    { value: "every_nth_part", label: "Every Nth Part" },
    { value: "percentage", label: "Percentage of Parts" },
    { value: "random", label: "Pure Random" },
    { value: "first_n_parts", label: "First N Parts" },
    { value: "last_n_parts", label: "Last N Parts" },
    { value: "exact_count", label: "Exact Count (No Variance)" },
] as const;

// Extract just the values for zod enum validation
// ruleTypes is `as const` so values are string literals; z.enum needs a mutable tuple — use a cast here.
export const ruleTypesEnum = z.enum(
    // eslint-disable-next-line local/no-double-cast-via-unknown -- z.enum requires [string, ...string[]] tuple; Array.map returns string[] which is not assignable without this cast
    ruleTypes.map(rt => rt.value) as unknown as [string, ...string[]]
);