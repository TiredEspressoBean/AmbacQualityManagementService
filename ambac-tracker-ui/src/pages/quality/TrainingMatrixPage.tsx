/**
 * Operator training / competency matrix — the real, wired page.
 * Operators (rows) x training types (columns); each cell is the operator's
 * current competency level (max in-date level) on the 4-level scale.
 *
 * Data: GET /api/CompetenceMatrix/ (useTrainingMatrix) — a view gated on
 * view_training_matrix, so an unauthorized caller gets a 403 handled below.
 * Shows current levels, per-skill coverage, and — via JobRole profiles —
 * required-vs-held gaps (role filter, role-fit column, gap edges, train-next).
 */
import { useMemo, useState } from "react";
import type { Schema } from "@/lib/api/types";
import { useTrainingMatrix } from "@/hooks/useTrainingMatrix";
import { useTrainingRecords } from "@/hooks/useTrainingRecords";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/status-badge";
import { AlertTriangle, Loader2 } from "lucide-react";

type Level = 0 | 1 | 2 | 3 | 4;
type Cell = Schema<"TrainingMatrixCell">;
type Operator = Schema<"TrainingMatrixOperator">;
type Column = Schema<"TrainingMatrixColumn">;
type Coverage = Schema<"TrainingMatrixCoverage">;

const LEVEL_META: Record<Level, { label: string; textClass: string }> = {
    0: { label: "None", textClass: "text-muted-foreground/40" },
    1: { label: "Trainee", textClass: "text-red-500 dark:text-red-400" },
    2: { label: "Assisted", textClass: "text-amber-500 dark:text-amber-400" },
    3: { label: "Qualified", textClass: "text-green-600 dark:text-green-400" },
    4: { label: "Expert", textClass: "text-blue-500 dark:text-blue-400" },
};

function LevelPie({ level, dim }: { level: Level; dim?: boolean }) {
    const frac = level / 4;
    return (
        <div
            className={`relative mx-auto h-6 w-6 rounded-full border border-border/60 transition-opacity ${LEVEL_META[level].textClass} ${dim ? "opacity-20" : ""}`}
        >
            {level > 0 && (
                <div
                    className="absolute inset-0 rounded-full"
                    style={{ background: `conic-gradient(currentColor 0 ${frac}turn, transparent ${frac}turn 1turn)` }}
                />
            )}
        </div>
    );
}

function ExpiryDot({ status }: { status: string }) {
    if (status !== "EXPIRING_SOON" && status !== "EXPIRED") return null;
    const cls = status === "EXPIRED" ? "bg-red-500" : "bg-amber-500";
    return <span className={`absolute right-0 top-0 h-2 w-2 rounded-full ring-2 ring-background ${cls}`} />;
}

/** Lazy-loaded progression history for one (operator, training type) cell. */
function CellProgression({ userId, trainingType }: { userId: number; trainingType: string }) {
    const { data, isLoading } = useTrainingRecords({
        user: userId,
        training_type: trainingType,
        ordering: "completed_date",
    });
    const records = data?.results ?? [];
    if (isLoading) {
        return <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /> Loading history…</div>;
    }
    if (records.length === 0) return null;
    return (
        <div className="border-t pt-2 text-xs">
            <div className="mb-1 font-medium">Progression</div>
            <ol className="space-y-1">
                {records.map((r) => {
                    const lvl = (r.level ?? 3) as Level;
                    const trainer = r.trainer_info as { full_name?: string; username?: string } | null | undefined;
                    return (
                        <li key={r.id} className="flex items-center gap-2 text-muted-foreground">
                            <span className={`h-2 w-2 shrink-0 rounded-full ${LEVEL_META[lvl].textClass}`} style={{ backgroundColor: "currentColor" }} />
                            <span>L{lvl} {LEVEL_META[lvl].label}</span>
                            {trainer && <span>· {trainer.full_name || trainer.username}</span>}
                            <span className="ml-auto tabular-nums">{r.completed_date}</span>
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}

function CellButton({ op, column, cell }: { op: Operator; column: Column; cell: Cell | undefined }) {
    const level = (cell?.level ?? 0) as Level;
    const status = cell?.status ?? "";
    return (
        <Popover>
            <PopoverTrigger asChild>
                <button
                    className="relative mx-auto flex h-9 w-9 items-center justify-center rounded hover:bg-muted"
                    aria-label={`${op.name} — ${column.name}: ${LEVEL_META[level].label}`}
                >
                    <LevelPie level={level} />
                    <ExpiryDot status={status} />
                </button>
            </PopoverTrigger>
            <PopoverContent className="w-72" align="center">
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <LevelPie level={level} />
                        <div>
                            <div className="font-medium">
                                {LEVEL_META[level].label}
                                {level > 0 && <span className="text-muted-foreground"> · L{level}</span>}
                            </div>
                            <div className="text-xs text-muted-foreground">{op.name} — {column.name}</div>
                        </div>
                    </div>
                    {cell ? (
                        <div className="space-y-1 border-t pt-2 text-xs text-muted-foreground">
                            <div>Expires: {cell.expires_date ?? "never"}</div>
                            <div><StatusBadge status={status || "CURRENT"} size="sm" /></div>
                        </div>
                    ) : (
                        <div className="border-t pt-2 text-xs text-muted-foreground">No training on record.</div>
                    )}
                    <CellProgression userId={op.id} trainingType={column.id} />
                </div>
            </PopoverContent>
        </Popover>
    );
}

function OperatorProfile({ op, columns, cellsByType }: { op: Operator; columns: Column[]; cellsByType: Map<string, Cell> }) {
    return (
        <div className="space-y-2">
            <div className="text-sm font-medium">{op.name}</div>
            <div className="space-y-1 border-t pt-2">
                {columns.map((col) => {
                    const cell = cellsByType.get(col.id);
                    const level = (cell?.level ?? 0) as Level;
                    return (
                        <div key={col.id} className="flex items-center gap-2 text-xs">
                            <LevelPie level={level} />
                            <span className="w-32 shrink-0 truncate">{col.name}</span>
                            <span className="tabular-nums text-muted-foreground">L{level}</span>
                            {cell && (cell.status === "EXPIRING_SOON" || cell.status === "EXPIRED") && (
                                <span className="ml-auto"><StatusBadge status={cell.status} size="sm" /></span>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export function TrainingMatrixPage() {
    const { data, isLoading, isError, error } = useTrainingMatrix();
    const [query, setQuery] = useState("");
    const [highlightTrainees, setHighlightTrainees] = useState(false);
    const [expiryLens, setExpiryLens] = useState(false);
    const [roleFilter, setRoleFilter] = useState<string>("all");

    const columns: Column[] = data?.training_types ?? [];
    const qualifiedAt = data?.qualified_at ?? 3;
    const jobRoles = data?.job_roles ?? [];

    const colName = useMemo(() => {
        const m = new Map<string, string>();
        columns.forEach((c) => m.set(c.id, c.name));
        return m;
    }, [columns]);

    const coverageByType = useMemo(() => {
        const m = new Map<string, Coverage>();
        (data?.coverage ?? []).forEach((c) => m.set(c.training_type, c));
        return m;
    }, [data]);

    const operators = useMemo(() => {
        const q = query.trim().toLowerCase();
        let list = data?.operators ?? [];
        if (roleFilter !== "all") list = list.filter((o) => o.job_role === roleFilter);
        if (q) list = list.filter((o) => o.name.toLowerCase().includes(q) || (o.job_role_name ?? "").toLowerCase().includes(q));
        return list;
    }, [data, query, roleFilter]);

    const cellMaps = useMemo(() => {
        const m = new Map<number, Map<string, Cell>>();
        (data?.operators ?? []).forEach((o) => {
            const inner = new Map<string, Cell>();
            o.cells.forEach((c) => inner.set(c.training_type, c));
            m.set(o.id, inner);
        });
        return m;
    }, [data]);

    const stats = useMemo(() => {
        const spof = (data?.coverage ?? []).filter((c) => c.qualified_count <= 1).length;
        const expiring = (data?.coverage ?? []).reduce((n, c) => n + c.expiring_count, 0);
        return { spof, expiring };
    }, [data]);

    const lensActive = highlightTrainees || expiryLens;

    if (isLoading) {
        return (
            <div className="container mx-auto flex items-center gap-2 p-6 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" /> Loading training matrix…
            </div>
        );
    }

    if (isError) {
        const status = (error as { response?: { status?: number } })?.response?.status;
        return (
            <div className="container mx-auto p-6">
                <h1 className="mb-2 text-2xl font-bold">Training Matrix</h1>
                <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm">
                    {status === 403
                        ? "You don't have access to the training matrix. Ask an administrator for the appropriate access."
                        : "Could not load the training matrix. Please try again."}
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6">
            <h1 className="mb-1 text-2xl font-bold">Training Matrix</h1>
            <p className="mb-4 max-w-3xl text-sm text-muted-foreground">
                Operator competency across training types. Each cell is the current level
                (max in-date); a red edge marks a skill below the operator's role
                requirement. The footer shows how many people can cover each skill —
                single-coverage is a staffing risk.
            </p>

            {/* Summary */}
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <SummaryTile label="Operators" value={operators.length} />
                <SummaryTile label="People with role gaps" value={operators.filter((o) => o.gap_count > 0).length} tone={operators.some((o) => o.gap_count > 0) ? "warn" : "ok"} />
                <SummaryTile label="Skills at coverage risk" value={stats.spof} tone={stats.spof ? "danger" : "ok"} />
                <SummaryTile label="Expiring soon" value={stats.expiring} tone={stats.expiring ? "warn" : "ok"} />
            </div>

            {/* Controls */}
            <div className="mb-4 flex flex-wrap items-center gap-4">
                <Input
                    placeholder="Search operator or role…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="max-w-xs"
                />
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="All roles" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All roles</SelectItem>
                        {jobRoles.map((r) => (
                            <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <label className="flex items-center gap-2 text-sm">
                    <Switch checked={highlightTrainees} onCheckedChange={setHighlightTrainees} />
                    Highlight Level 1–2
                </label>
                <label className="flex items-center gap-2 text-sm">
                    <Switch checked={expiryLens} onCheckedChange={setExpiryLens} />
                    Expiry lens
                </label>
            </div>

            {/* Matrix */}
            <div className="max-h-[70vh] overflow-auto rounded-md border">
                <table className="border-collapse text-sm">
                    <thead>
                        <tr>
                            <th className="sticky left-0 top-0 z-30 min-w-[200px] border-b border-r bg-background p-3 text-left font-medium">
                                Operator
                            </th>
                            {columns.map((col) => (
                                <th key={col.id} className="sticky top-0 z-20 min-w-[110px] border-b bg-background p-2 text-center align-bottom font-medium">
                                    <div className="leading-tight">{col.name}</div>
                                </th>
                            ))}
                            <th className="sticky top-0 z-20 min-w-[90px] border-b border-l bg-background p-2 text-center font-medium">
                                Role fit
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {operators.map((op) => {
                            const cellsByType = cellMaps.get(op.id) ?? new Map<string, Cell>();
                            return (
                                <tr key={op.id} className="hover:bg-muted/30">
                                    <td className="sticky left-0 z-10 border-b border-r bg-background p-3">
                                        <Popover>
                                            <PopoverTrigger asChild>
                                                <button className="block text-left font-medium hover:underline">{op.name}</button>
                                            </PopoverTrigger>
                                            <PopoverContent align="start" className="w-80">
                                                <OperatorProfile op={op} columns={columns} cellsByType={cellsByType} />
                                            </PopoverContent>
                                        </Popover>
                                    </td>
                                    {columns.map((col) => {
                                        const cell = cellsByType.get(col.id);
                                        const level = (cell?.level ?? 0) as Level;
                                        const status = cell?.status ?? "";
                                        const gap = cell?.gap ?? false;
                                        const emphasized =
                                            (highlightTrainees && (level === 1 || level === 2)) ||
                                            (expiryLens && (status === "EXPIRING_SOON" || status === "EXPIRED"));
                                        const dim = lensActive && !emphasized;
                                        return (
                                            <td
                                                key={col.id}
                                                className={`border-b p-1 text-center ${gap ? "bg-red-500/5" : ""} ${dim ? "opacity-40" : ""}`}
                                                style={gap ? { boxShadow: "inset 3px 0 0 0 rgb(239 68 68 / 0.55)" } : undefined}
                                            >
                                                <CellButton op={op} column={col} cell={cell} />
                                            </td>
                                        );
                                    })}
                                    <td className="border-b border-l bg-background p-2 text-center">
                                        <RoleFitCell op={op} colName={colName} />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td className="sticky left-0 z-10 border-t-2 border-r bg-muted/50 p-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                Qualified (L{qualifiedAt}+) · coverage
                            </td>
                            {columns.map((col) => {
                                const cov = coverageByType.get(col.id);
                                const n = cov?.qualified_count ?? 0;
                                const tone = n <= 1 ? "text-red-600 dark:text-red-400" : n === 2 ? "text-amber-600 dark:text-amber-400" : "text-foreground";
                                return (
                                    <td key={col.id} className="border-t-2 bg-muted/50 p-2 text-center">
                                        <div className={`flex items-center justify-center gap-1 font-semibold tabular-nums ${tone}`}>
                                            {n <= 1 && <AlertTriangle className="h-3 w-3" />}
                                            {n}
                                        </div>
                                    </td>
                                );
                            })}
                            <td className="border-t-2 border-l bg-muted/50" />
                        </tr>
                    </tfoot>
                </table>
            </div>

            {/* Legend */}
            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                {([0, 1, 2, 3, 4] as Level[]).map((lvl) => (
                    <div key={lvl} className="flex items-center gap-2">
                        <LevelPie level={lvl} />
                        <span>{lvl === 0 ? "None" : `L${lvl} ${LEVEL_META[lvl].label}`}</span>
                    </div>
                ))}
                <div className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-full bg-amber-500" /><span>Expiring</span></div>
                <div className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-full bg-red-500" /><span>Expired</span></div>
                <div className="flex items-center gap-2"><span className="inline-block h-4 w-1 rounded bg-red-500/60" /><span>Below role requirement</span></div>
                <div className="flex items-center gap-2"><AlertTriangle className="h-3 w-3 text-red-600 dark:text-red-400" /><span>Single-point-of-failure (≤1 qualified)</span></div>
            </div>
        </div>
    );
}

/** Role-fit drill-down: the operator's role profile, requirement by requirement. */
function RoleFitCell({ op, colName }: { op: Operator; colName: Map<string, string> }) {
    if (!op.job_role) {
        return <span className="text-xs text-muted-foreground" title="No job role assigned">—</span>;
    }
    const reqs = op.cells
        .filter((c) => c.required_level > 0)
        .map((c) => ({
            name: colName.get(c.training_type) ?? c.training_type,
            required: c.required_level as Level,
            held: c.level as Level,
            gap: c.gap,
        }))
        .sort((a, b) => Number(b.gap) - Number(a.gap));
    const gapCount = op.gap_count;

    return (
        <Popover>
            <PopoverTrigger asChild>
                <button className="mx-auto block" aria-label={`Role fit for ${op.name}`}>
                    {gapCount === 0 ? (
                        <Badge variant="secondary" className="cursor-pointer bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">meets</Badge>
                    ) : (
                        <Badge variant="secondary" className="cursor-pointer bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                            {gapCount} gap{gapCount > 1 ? "s" : ""}
                        </Badge>
                    )}
                </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80">
                <div className="space-y-2">
                    <div>
                        <div className="text-sm font-medium">{op.name}</div>
                        <div className="text-xs text-muted-foreground">
                            {op.job_role_name} · {gapCount === 0 ? "all requirements met" : `${gapCount} of ${op.required_count} not met`}
                        </div>
                    </div>
                    <div className="space-y-1 border-t pt-2">
                        {reqs.length === 0 && <div className="text-xs text-muted-foreground">Role has no required competencies.</div>}
                        {reqs.map((r) => (
                            <div key={r.name} className="flex items-center justify-between gap-2 text-xs">
                                <span className={r.gap ? "font-medium" : ""}>{r.name}</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">needs L{r.required}</span>
                                    <span className="inline-flex items-center gap-1 tabular-nums"><LevelPie level={r.held} /> L{r.held}</span>
                                    {r.gap ? (
                                        <Badge variant="secondary" className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">gap</Badge>
                                    ) : (
                                        <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">met</Badge>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    {gapCount > 0 && (
                        <div className="border-t pt-2 text-xs text-muted-foreground">
                            Train next: {reqs.filter((r) => r.gap).map((r) => r.name).join(", ")}
                        </div>
                    )}
                </div>
            </PopoverContent>
        </Popover>
    );
}

function SummaryTile({ label, value, tone = "neutral" }: { label: string; value: number; tone?: "neutral" | "ok" | "warn" | "danger" }) {
    const toneClass =
        tone === "danger" ? "text-red-600 dark:text-red-400"
            : tone === "warn" ? "text-amber-600 dark:text-amber-400"
                : tone === "ok" ? "text-green-600 dark:text-green-400"
                    : "text-foreground";
    return (
        <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className={`text-2xl font-bold tabular-nums ${toneClass}`}>{value}</div>
        </div>
    );
}
