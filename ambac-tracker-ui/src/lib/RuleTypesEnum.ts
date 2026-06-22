import {z} from "zod";

// Must match backend SamplingRuleType choices in mes_standard.py
// (values are UPPERCASE — see RuleTypeEnum in the generated API schema).
export const ruleTypes = [
    { value: "EVERY_NTH_PART", label: "Every Nth Part" },
    { value: "PERCENTAGE", label: "Percentage of Parts" },
    { value: "RANDOM", label: "Pure Random" },
    { value: "FIRST_N_PARTS", label: "First N Parts" },
    { value: "LAST_N_PARTS", label: "Last N Parts" },
    { value: "EXACT_COUNT", label: "Exact Count (No Variance)" },
] as const;

// Extract just the values for zod enum validation
// ruleTypes is `as const` so values are string literals; z.enum needs a mutable tuple — use a cast here.
export const ruleTypesEnum = z.enum(
    // eslint-disable-next-line local/no-double-cast-via-unknown -- z.enum requires [string, ...string[]] tuple; Array.map returns string[] which is not assignable without this cast
    ruleTypes.map(rt => rt.value) as unknown as [string, ...string[]]
);