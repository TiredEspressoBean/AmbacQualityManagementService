import { z } from "zod";

/**
 * Format a field path into a readable label
 * e.g., "hubspot_api_id" -> "Hubspot api id"
 */
function formatFieldName(path: (string | number)[]): string {
    const field = path[path.length - 1];
    if (typeof field !== "string") return "This field";

    return field
        .replace(/_/g, " ")
        .replace(/([A-Z])/g, " $1")
        .toLowerCase()
        .replace(/^\w/, (c) => c.toUpperCase())
        .trim();
}

/**
 * Custom Zod error map for user-friendly validation messages
 */
export const customErrorMap: z.ZodErrorMap = (issue, ctx) => {
    const fieldName = formatFieldName(issue.path);

    switch (issue.code) {
        case z.ZodIssueCode.too_small:
            if (issue.type === "string" && issue.minimum === 1) {
                return { message: `${fieldName} is required` };
            }
            if (issue.type === "string") {
                return { message: `${fieldName} must be at least ${issue.minimum} characters` };
            }
            if (issue.type === "number") {
                return { message: `${fieldName} must be at least ${issue.minimum}` };
            }
            if (issue.type === "array") {
                return { message: `${fieldName} must have at least ${issue.minimum} item(s)` };
            }
            break;

        case z.ZodIssueCode.too_big:
            if (issue.type === "string") {
                return { message: `${fieldName} must be ${issue.maximum} characters or less` };
            }
            if (issue.type === "number") {
                return { message: `${fieldName} must be ${issue.maximum} or less` };
            }
            if (issue.type === "array") {
                return { message: `${fieldName} must have ${issue.maximum} or fewer items` };
            }
            break;

        case z.ZodIssueCode.invalid_type:
            if (issue.received === "undefined" || issue.received === "null") {
                return { message: `${fieldName} is required` };
            }
            return { message: `${fieldName} must be a ${issue.expected}` };

        case z.ZodIssueCode.invalid_string:
            if (issue.validation === "email") {
                return { message: `${fieldName} must be a valid email address` };
            }
            if (issue.validation === "url") {
                return { message: `${fieldName} must be a valid URL` };
            }
            if (issue.validation === "uuid") {
                return { message: `${fieldName} must be a valid ID` };
            }
            break;

        case z.ZodIssueCode.invalid_enum_value:
            return { message: `${fieldName} has an invalid value` };

        case z.ZodIssueCode.custom:
            // Allow custom messages to pass through
            return { message: issue.message ?? `${fieldName} is invalid` };
    }

    // Fall back to default message
    return { message: ctx.defaultError };
};

/**
 * Check if a Zod schema field is required (not optional/nullable/nullish)
 */
export function isFieldRequired(schema: z.ZodTypeAny): boolean {
    // Unwrap ZodEffects (refinements, transforms)
    if (schema instanceof z.ZodEffects) {
        return isFieldRequired(schema.innerType());
    }

    // Check for optional/nullable wrappers
    if (schema instanceof z.ZodOptional) return false;
    if (schema instanceof z.ZodNullable) return false;

    // ZodDefault makes a field optional in forms
    if (schema instanceof z.ZodDefault) return false;

    return true;
}

/**
 * Initialize Zod with custom error map
 * Call this once at app startup
 */
export function initZodErrorMap() {
    z.setErrorMap(customErrorMap);
}
