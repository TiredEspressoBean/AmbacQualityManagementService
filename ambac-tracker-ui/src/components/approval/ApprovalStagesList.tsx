import { User, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

/** One stage of a sequential request, as the server describes it
 *  (ApprovalRequestSerializer.stages → services/core/approval_stages.describe). */
export type ApprovalStageView = {
    number: number;
    open: boolean;
    done: boolean;
    members: {
        kind: "user" | "group";
        id: string;
        name: string;
        status: string;            // a user's decision, PENDING; a group's COVERED / PENDING
        for_group: string | null;  // the group a user claimed, if any
    }[];
};

/** A sequential request's approvers grouped by stage, the open stage marked. */
export function ApprovalStagesList({ stages }: { stages: ApprovalStageView[] }) {
    return (
        <div className="space-y-2">
            {stages.map((st) => (
                <div key={st.number}
                     className={cn("rounded-lg border p-2", st.open && "border-primary/50 bg-primary/5")}>
                    <div className="mb-1 flex items-center gap-2 text-xs font-medium">
                        Stage {st.number}
                        {st.open && <Badge variant="default" className="text-[10px]">Waiting on this stage</Badge>}
                        {st.done && <Badge variant="outline" className="text-[10px]">Done</Badge>}
                    </div>
                    <div className="space-y-1">
                        {st.members.map((m) => (
                            <div key={`${m.kind}-${m.id}`} className="flex items-center justify-between text-sm">
                                <span className="flex items-center gap-2">
                                    {m.kind === "user" ? <User className="h-4 w-4" /> : <Users className="h-4 w-4" />}
                                    {m.name}
                                    {m.for_group && <span className="text-xs text-muted-foreground">for {m.for_group}</span>}
                                </span>
                                {m.kind === "group" ? (
                                    <Badge variant="outline" className="text-[10px]">
                                        {m.status === "COVERED" ? "Covered" : "Any one member"}
                                    </Badge>
                                ) : (
                                    <StatusBadge status={m.status}
                                                 label={m.status === "PENDING" ? "Pending" : m.status.charAt(0) + m.status.slice(1).toLowerCase()} />
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
