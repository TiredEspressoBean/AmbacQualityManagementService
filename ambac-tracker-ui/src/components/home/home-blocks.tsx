/**
 * Role-based home blocks — the "what needs me right now" landing surface.
 *
 * Model: a stack of SELF-GATING blocks (the sidebar pattern), not a single
 * persona switch — small-shop users wear multiple hats (a shift lead is an
 * operator plus quality oversight), and the permissive permission tiers can't
 * discriminate roles anyway. Each block declares which tenant groups it serves;
 * a user sees the union of their groups' blocks, ORDERED by their primary
 * (first-matched) persona so the top card is always their main job.
 *
 * ⚠ MOCK DATA phase: every block currently renders from `MOCK` below so the
 * layout/UX can be judged before backend wiring. The swap plan is one seam per
 * block: replace the MOCK read with the real query —
 *   - My work         → StepExecutions filtered to the current user + open status
 *   - Inspection queue → IncomingInspection list + QuarantineDispositions?current_state=OPEN
 *   - Decisions        → useMyPendingApprovals() + useMyCapaTasks() (already exist)
 */
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, CheckSquare, PackageSearch, Wrench } from "lucide-react";
import type { AuthUser } from "@/hooks/useAuthUser";

// ---------------------------------------------------------------------------
// MOCK DATA — replace per-block with real queries (see module docstring).
// Values mirror the seeded Demo tenant so the mock reads plausibly.
// ---------------------------------------------------------------------------
const MOCK = {
    myWork: [
        { id: "1", step: "Nozzle Inspection", subject: "INJ-2024-0042-017", status: "IN_PROGRESS" },
        { id: "2", step: "Final Test", subject: "INJ-2024-0042-009", status: "CLAIMED" },
        { id: "3", step: "Assembly", subject: "INJ-2024-0042-021", status: "PENDING" },
    ],
    inspection: {
        awaiting: 5,      // purchased lots + OSP returns awaiting inspection
        held: 1,          // soft-held (e.g. unqualified supplier)
        dispositionsOpen: 2,
    },
    decisions: {
        approvals: 2,
        capaTasks: 3,
    },
};

// ---------------------------------------------------------------------------
// Blocks
// ---------------------------------------------------------------------------

const STATUS_TONE: Record<string, string> = {
    IN_PROGRESS: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    CLAIMED: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    PENDING: "bg-muted text-muted-foreground",
};

function MyWorkBlock() {
    const rows = MOCK.myWork;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                    My work
                    <Badge variant="secondary" className="ml-1">{rows.length}</Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {rows.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nothing assigned — check the control center for queued work.</p>
                ) : (
                    rows.map((r) => (
                        <div key={r.id} className="flex items-center gap-3 rounded-md border p-2.5">
                            <div className="min-w-0 flex-1">
                                <div className="truncate text-sm font-medium">{r.step}</div>
                                <div className="truncate font-mono text-xs text-muted-foreground">{r.subject}</div>
                            </div>
                            <Badge className={STATUS_TONE[r.status] ?? ""} variant="outline">
                                {r.status.replace("_", " ").toLowerCase()}
                            </Badge>
                            {/* TODO(backend wiring): deep-link into the operator runtime for this execution */}
                            <Link to="/workorders">
                                <Button size="sm" variant="outline">Resume</Button>
                            </Link>
                        </div>
                    ))
                )}
            </CardContent>
        </Card>
    );
}

function CountStat({ label, value, tone }: { label: string; value: number; tone?: "warn" | "bad" }) {
    const color = tone === "bad" ? "text-destructive" : tone === "warn" ? "text-amber-600" : "";
    return (
        <div className="rounded-md border p-3">
            <div className={`text-2xl font-semibold tabular-nums ${color}`}>{value}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
        </div>
    );
}

function InspectionQueueBlock() {
    const d = MOCK.inspection;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <PackageSearch className="h-4 w-4 text-muted-foreground" />
                    Inspection queue
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                    <CountStat label="Awaiting inspection" value={d.awaiting} />
                    <CountStat label="Held" value={d.held} tone={d.held > 0 ? "warn" : undefined} />
                    <CountStat label="Open dispositions" value={d.dispositionsOpen} tone={d.dispositionsOpen > 0 ? "warn" : undefined} />
                </div>
                <div className="flex gap-2">
                    <Link to="/production/incoming" className="flex-1">
                        <Button className="w-full" variant="default">
                            Start inspecting <ArrowRight className="ml-1 h-4 w-4" />
                        </Button>
                    </Link>
                    <Link to="/production/dispositions" className="flex-1">
                        <Button className="w-full" variant="outline">Dispositions</Button>
                    </Link>
                </div>
            </CardContent>
        </Card>
    );
}

function DecisionsBlock() {
    const d = MOCK.decisions;
    const total = d.approvals + d.capaTasks;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <CheckSquare className="h-4 w-4 text-muted-foreground" />
                    Needs your decision
                    {total > 0 && <Badge variant="secondary" className="ml-1">{total}</Badge>}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                    {d.approvals} approval{d.approvals === 1 ? "" : "s"} waiting on you · {d.capaTasks} CAPA task{d.capaTasks === 1 ? "" : "s"} assigned
                </p>
                <Link to="/inbox">
                    <Button variant="outline">
                        Open inbox <ArrowRight className="ml-1 h-4 w-4" />
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Registry + persona resolution
// ---------------------------------------------------------------------------

type BlockDef = {
    id: string;
    /** Tenant-group names (GROUP_PRESETS display names) this block serves. */
    groups: string[];
    Component: () => React.ReactNode;
};

const BLOCKS: BlockDef[] = [
    { id: "my-work", groups: ["Operator", "Shift Lead"], Component: MyWorkBlock },
    { id: "inspection", groups: ["QA Inspector", "Shift Lead", "QA Manager"], Component: InspectionQueueBlock },
    { id: "decisions", groups: ["Operator", "Shift Lead", "QA Inspector", "QA Manager", "Production Manager", "Tenant Admin"], Component: DecisionsBlock },
];

/** Per-persona block ordering — the first matched persona wins, so the top
 *  card is the user's main job. Personas not listed fall back to registry order. */
const PERSONA_ORDER: Array<{ group: string; order: string[] }> = [
    { group: "Operator", order: ["my-work", "decisions", "inspection"] },
    { group: "Shift Lead", order: ["my-work", "inspection", "decisions"] },
    { group: "QA Inspector", order: ["inspection", "decisions", "my-work"] },
    { group: "QA Manager", order: ["inspection", "decisions", "my-work"] },
];

export function resolveHomeBlocks(user: AuthUser): BlockDef[] {
    // auth/user returns tenant-scoped groups (UserRole memberships) in `groups`
    // (TenantAwareUserDetailsSerializer) — the only group field on the payload.
    const names = new Set((user.groups ?? []).map((g) => g.name));
    // Platform staff / tenant admins see every block (support + demo view).
    const seesAll = user.is_staff || names.has("Tenant Admin") || names.has("System Admin");

    let visible = seesAll
        ? [...BLOCKS]
        : BLOCKS.filter((b) => b.groups.some((g) => names.has(g)));

    const persona = PERSONA_ORDER.find((p) => names.has(p.group));
    if (persona) {
        const rank = (id: string) => {
            const i = persona.order.indexOf(id);
            return i === -1 ? persona.order.length : i;
        };
        visible = [...visible].sort((a, b) => rank(a.id) - rank(b.id));
    }
    return visible;
}