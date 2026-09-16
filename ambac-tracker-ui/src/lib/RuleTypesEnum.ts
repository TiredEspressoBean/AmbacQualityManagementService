import {z} from "zod";

// A deliberate SUBSET of backend SamplingRuleType (mes_standard.py): the six
// per-part streaming rules, in UPPERCASE to match.
//
// AQL, C_ZERO and VARIABLES are missing on purpose — do not "complete" this
// list. They are lot-acceptance rules for RECEIVING steps: lot-terminal rather
// than per-part, evaluated by services.qms.acceptance_sampling, and
// parameterised on the RULESET (aql / level / severity / strategy, plus
// variables_characteristic for Z1.9) rather than on the rule row this editor
// writes. Offering them here would produce a rule the per-part evaluator
// (services/dwi/sampling_decisions.py) silently ignores, because it only
// branches on the six below.
export const ruleTypes = [
    { value: "EVERY_NTH_PART", label: "Every Nth Part" },
    { value: "PERCENTAGE", label: "Percentage of Parts" },
    { value: "RANDOM", label: "Pure Random" },
    { value: "FIRST_N_PARTS", label: "First N Parts" },
    { value: "LAST_N_PARTS", label: "Last N Parts" },
    { value: "EXACT_COUNT", label: "Exact Count (No Variance)" },
] as const;

// Extract just the values for zod enum validation.
//
// The tuple type keeps the literal union. Casting to `[string, ...string[]]`
// (as this did) widens it away, so the inferred `rule_type` became a bare
// `string` and every form payload built from it then needed its own cast at the
// call. The cast to a tuple is still needed -- z.enum wants a non-empty tuple
// and Array.map gives an array -- but it should not throw the literals away.
export type RuleTypeValue = (typeof ruleTypes)[number]["value"];

export const ruleTypesEnum = z.enum(
    // eslint-disable-next-line local/no-double-cast-via-unknown -- z.enum requires a [T, ...T[]] tuple; Array.map returns T[], which is not assignable without this cast
    ruleTypes.map(rt => rt.value) as unknown as [RuleTypeValue, ...RuleTypeValue[]]
);