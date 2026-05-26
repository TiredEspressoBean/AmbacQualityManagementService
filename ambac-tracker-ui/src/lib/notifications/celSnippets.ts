/**
 * Curated CEL snippets shown in the "Insert pattern" popover on the
 * advanced-mode CEL editor. Static list — these are common patterns we
 * want first-class discoverability for, not user-authored library entries.
 */
export interface CelSnippet {
    label: string;
    expression: string;
}

export const CEL_SNIPPETS: CelSnippet[] = [
    { label: "Severity critical", expression: "payload.severity == 'critical'" },
    { label: "Assigned to me", expression: "payload.assigned_to_id == owner_user.id" },
    { label: "Late risk above 70", expression: "payload.risk_score > 70" },
    { label: "Major or critical", expression: "payload.severity in ['major', 'critical']" },
    { label: "Due within 3 days", expression: "payload.days_remaining <= 3" },
];
