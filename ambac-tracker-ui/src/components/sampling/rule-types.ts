/** Sampling rule types, with their labels and the unit their value is in. */
export const RULE_TYPES = [
    { value: "EVERY_NTH_PART", label: "Every Nth part", unit: "N" },
    { value: "PERCENTAGE", label: "Percentage", unit: "%" },
    { value: "RANDOM", label: "Random", unit: "%" },
    { value: "FIRST_N_PARTS", label: "First N parts", unit: "N" },
    { value: "LAST_N_PARTS", label: "Last N parts", unit: "N" },
    { value: "EXACT_COUNT", label: "Exact count", unit: "N" },
    { value: "AQL", label: "Acceptance sampling (Z1.4)", unit: "" },
    { value: "C_ZERO", label: "Zero-acceptance (C=0)", unit: "" },
];
