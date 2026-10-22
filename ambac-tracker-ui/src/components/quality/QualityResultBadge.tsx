/** An inspection result as a chip: PASS, FAIL, or REPAIR ("Needs repair") in its own
 *  neutral colour — planned repair work at a rebuild check, not a failure — so it never
 *  falls through to the red fail branch. */
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export const REPAIR_TONE = "border-sky-500/50 bg-sky-50 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300";

export function QualityResultBadge({ status, prefix = "", className, superseded = false }: {
    status: string; prefix?: string; className?: string;
    /** Withdrawn by a voided capture: still shown as recorded, struck through. */
    superseded?: boolean;
}) {
    if (superseded) {
        return (
            <Badge variant="outline" className={cn("text-muted-foreground", className)} title="Superseded: its capture was voided and taken again">
                <span className="line-through">{prefix}{status === "REPAIR" ? "Needs repair" : status}</span>
                <span className="ml-1">· superseded</span>
            </Badge>
        );
    }
    if (status === "REPAIR") {
        return <Badge variant="outline" className={cn(REPAIR_TONE, className)}>{prefix}Needs repair</Badge>;
    }
    return (
        <Badge variant={status === "PASS" ? "default" : "destructive"} className={className}>
            {prefix}{status}
        </Badge>
    );
}
