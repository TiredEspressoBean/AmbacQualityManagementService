/**
 * The NCRs you own and what each still needs from you: decisions to make, containment,
 * its CAPA call, decisions to close. Home's "My NCRs" (user go 2026-11-18).
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { myNcrsOptions } from "@/hooks/ncrs";
import { ncrCovers } from "@/components/quality/UnassignedDispositions";
import type { Schema } from "@/lib/api/types";

/** What an NCR still needs, as short chips (shared by every list that shows it). */
export function NcrTodoChips({ todo }: { todo: Schema<"NCR">["todo"] }) {
    const chips: { label: string; urgent?: boolean }[] = [];
    if (todo.awaiting_decision > 0) chips.push({ label: `${todo.awaiting_decision} to decide` });
    if (todo.containment_needed) chips.push({ label: "Containment needed", urgent: true });
    if (todo.capa_decision_needed) chips.push({ label: "CAPA call needed" });
    if (todo.decided_to_close > 0) chips.push({ label: `${todo.decided_to_close} to close` });
    if (chips.length === 0) return null;
    return (
        <span className="flex flex-wrap gap-1">
            {chips.map((c) => (
                <span key={c.label}
                      className={`rounded px-1.5 py-0.5 text-xs ${c.urgent ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"}`}>
                    {c.label}
                </span>
            ))}
        </span>
    );
}

export function MyNcrsList({ userPk, empty }: { userPk: number; empty?: React.ReactNode }) {
    const { data: rows = [] } = useQuery(myNcrsOptions(userPk));
    if (rows.length === 0) return <>{empty ?? null}</>;
    return (
        <div className="space-y-1">
            {rows.map((n) => (
                <Link key={n.id} to="/quality/ncrs/$ncrId" params={{ ncrId: String(n.id) }}
                      className="flex items-center gap-3 rounded-lg border p-2.5 hover:bg-muted/50">
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                            {[n.ncr_number, ncrCovers(n), n.severity_display, n.description].filter(Boolean).join(" · ")}
                        </span>
                        <NcrTodoChips todo={n.todo} />
                    </span>
                </Link>
            ))}
        </div>
    );
}
