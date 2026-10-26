const LABEL: Record<string, string> = {
    APPROVED: "Approved", REJECTED: "Rejected", DELEGATED: "Delegated", WITHDRAWN: "Withdrawn",
};

type Correction = { field: string; old_value: string; new_value: string; reason: string; by: string | null; at: string };

/**
 * What happened to an approver's answer while the request was open: withdrawn (what it
 * was, and why), then answered again. Read from the response's correction records, so
 * the row shows the change rather than only the latest answer (Corrections #17).
 */
export function ResponseCorrections({ corrections }: { corrections?: Correction[] | null }) {
    const rows = (corrections ?? []).filter((c) => c.field === "decision");
    if (rows.length === 0) return null;
    return (
        <ul className="mt-2 space-y-1 border-l-2 border-amber-300 pl-2 text-xs text-muted-foreground">
            {rows.map((c, i) => (
                <li key={i}>
                    {c.new_value === "WITHDRAWN"
                        ? <>Withdrew <strong>{LABEL[c.old_value] ?? c.old_value}</strong></>
                        : <>Answered again: <strong>{LABEL[c.new_value] ?? c.new_value}</strong></>}
                    {c.reason ? ` — ${c.reason}` : ""}
                    {" "}<span>({c.by ? `${c.by}, ` : ""}{new Date(c.at).toLocaleString()})</span>
                </li>
            ))}
        </ul>
    );
}
