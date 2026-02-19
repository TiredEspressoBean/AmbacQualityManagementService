/**
 * Extended types for fields returned by backend but not fully typed in OpenAPI spec.
 * These typically are nested `*_info` objects that the generated schema types as `{}`.
 */

// Common user info pattern returned in *_info fields
export type UserInfo = {
    id: number;
    username: string;
    email?: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;
};

// Order detail info pattern
export type OrderDetailInfo = {
    id: string;
    name: string;
    company_name?: string;
    customer_name?: string;
};

// Parts summary for work orders
export type PartsSummary = {
    total: number;
    requiring_qa: number;
    passed: number;
    failed: number;
};

// Extended part fields for QA views
export type ExtendedPartFields = {
    step_name?: string;
    step_description?: string;
    process_name?: string;
    part_type_name?: string;
    is_batch_step?: boolean;
};

// Helper to safely access *_info fields
export function asUserInfo(info: unknown): UserInfo | null {
    if (!info || typeof info !== 'object') return null;
    return info as UserInfo;
}

export function asOrderDetailInfo(info: unknown): OrderDetailInfo | null {
    if (!info || typeof info !== 'object') return null;
    return info as OrderDetailInfo;
}

export function asPartsSummary(summary: unknown): PartsSummary | null {
    if (!summary || typeof summary !== 'object') return null;
    return summary as PartsSummary;
}

// Type guard for extended part fields
export function withExtendedPartFields<T>(part: T): T & ExtendedPartFields {
    return part as T & ExtendedPartFields;
}
