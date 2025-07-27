import {z} from "zod";

export const ruleTypes = [
    { value: "every_nth_part", label: "Every Nth Part" },
    { value: "percentage", label: "Percentage of Parts" },
    { value: "random", label: "Pure Random" },
    { value: "random_within_n", label: "Random Within N" },
    { value: "first_n_parts", label: "First N Parts" },
    { value: "last_n_parts", label: "Last N Parts" },
    // { value: "acceptance_lot", label: "Acceptance Lot" },
    // { value: "variables_sampling_plan", label: "Variables Plan" },
    // { value: "custom", label: "Custom Rule" },
];

export const ruleTypesEnum = z.enum(ruleTypes);