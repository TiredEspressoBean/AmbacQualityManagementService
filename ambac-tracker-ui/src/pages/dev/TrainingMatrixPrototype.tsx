/**
 * DESIGN PROTOTYPE (mock data, /dev/training-matrix): the operator training /
 * competency matrix — the actual goal of the training-matrix feature.
 *
 * This is the "instrument" version, shaped by research into WHY a training
 * matrix gets requested. It shows the matrix not as a status board but as a
 * required-vs-held gap tool, with the lenses each triggering situation needs:
 *
 *   - Competency levels (4-level shop-floor scale) as quarter-pie cells:
 *       ○ none · ◔ L1 Trainee · ◑ L2 Assisted · ◕ L3 Qualified · ● L4 Expert
 *   - Required-BY-ROLE profiles → per-person gaps (audit / CAPA / onboarding /
 *     skills-gap "who to train next"). Each operator is judged against the
 *     competence profile of their role.
 *   - Coverage / single-point-of-failure footer (shift planning, cross-training):
 *     how many people are qualified per skill; flags 0–1 coverage.
 *   - Evidence in the cell popover (trainer sign-off + record) — turns a color
 *     into the auditable "competence evidence" clause 7.2 demands.
 *   - Configurable expiry lens (requalification / renewal planning).
 *
 * Hardcoded sample data — nothing is wired to the API. The real version reads
 * from a matrix endpoint over TrainingRecord / TrainingRequirement plus a new
 * role-requirement profile (see the training-matrix plan).
 */
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { FileText, AlertTriangle, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

// ---- Level scale -----------------------------------------------------------
//
// Colors reuse the app's semantic palette (see status-badge.tsx STATUS_COLORS):
// danger=red · warning=amber · success=green · info=blue. The pie fills with
// `currentColor`, so each level's text-color class drives the glyph — same hues
// as every StatusBadge, theme-aware in light/dark.

type Level = 0 | 1 | 2 | 3 | 4;

const LEVEL_META: Record<Level, { label: string; blurb: string; textClass: string }> = {
    0: { label: "None", blurb: "No training on record", textClass: "text-muted-foreground/40" },
    1: { label: "Trainee", blurb: "In training — supervised only", textClass: "text-red-500 dark:text-red-400" },
    2: { label: "Assisted", blurb: "Can work; output still checked", textClass: "text-amber-500 dark:text-amber-400" },
    3: { label: "Qualified", blurb: "Independent, to standard", textClass: "text-green-600 dark:text-green-400" },
    4: { label: "Expert", blurb: "Independent + can train/sign off others", textClass: "text-blue-500 dark:text-blue-400" },
};

/** Coverage bar: an operator counts as "qualified" on a skill at this level+. */
const QUALIFIED_AT: Level = 3;

// ---- Data model (mock) -----------------------------------------------------

interface HistoryEntry {
    level: Level;
    date: string; // ISO date the operator reached this level
    trainer?: string;
}

interface Cell {
    level: Level;
    completed?: string; // ISO date
    expires?: string | null;
    trainer?: string;
    evidence?: string; // mock filename of retained competence evidence
    history?: HistoryEntry[]; // level progression over time (audit / succession)
}

interface Skill {
    key: string;
    name: string;
}

/** A role's required competence profile: skill.key → required level. */
interface Role {
    key: string;
    name: string;
    required: Partial<Record<string, Level>>;
}

interface Operator {
    id: number;
    name: string;
    role: string; // role.key
    cells: Record<string, Cell>;
}

const SKILLS: Skill[] = [
    { key: "blueprint", name: "Blueprint Reading" },
    { key: "cmm", name: "CMM Operation" },
    { key: "solder", name: "Soldering IPC-A-610" },
    { key: "deburr", name: "Deburring" },
    { key: "torque", name: "Torque Spec" },
    { key: "heattreat", name: "Heat Treat" },
    { key: "final", name: "Final Inspection" },
];

const ROLES: Role[] = [
    { key: "machinist", name: "Machinist", required: { blueprint: 2, deburr: 3, torque: 3, cmm: 2 } },
    { key: "cmm_inspector", name: "CMM Inspector", required: { blueprint: 3, cmm: 3, final: 4 } },
    { key: "assembler", name: "Assembler", required: { blueprint: 2, solder: 3, torque: 2 } },
    { key: "quality_eng", name: "Quality Engineer", required: { blueprint: 3, cmm: 3, heattreat: 3, final: 4 } },
    { key: "heat_treat_op", name: "Heat Treat Operator", required: { heattreat: 4, deburr: 2 } },
];

const roleOf = (op: Operator): Role | undefined => ROLES.find((r) => r.key === op.role);

const cell = (
    level: Level,
    completed?: string,
    expires?: string | null,
    trainer?: string,
    evidence?: string,
    history?: HistoryEntry[],
): Cell => ({ level, completed, expires, trainer, evidence, history });

const OPERATORS: Operator[] = [
    {
        id: 1, name: "J. Rivera", role: "machinist",
        cells: {
            blueprint: cell(4, "2024-02-11", null, "Okafor", "cert-blueprint-riv.pdf"),
            cmm: cell(3, "2024-06-01", "2026-06-01", "Okafor", "cmm-signoff-riv.pdf", [
                { level: 1, date: "2023-06-01", trainer: "Okafor" },
                { level: 2, date: "2024-01-10", trainer: "Okafor" },
                { level: 3, date: "2024-06-01", trainer: "Okafor" },
            ]),
            solder: cell(3, "2025-01-15", "2027-01-15", "Petrov"),
            deburr: cell(4, "2023-09-01", null, "Okafor"),
            torque: cell(2, "2025-11-02", "2026-11-02", "Rivera"),
            heattreat: cell(3, "2024-08-19", "2026-08-19", "Kowalski"),
            final: cell(0),
        },
    },
    {
        id: 2, name: "M. Chen", role: "machinist",
        cells: {
            blueprint: cell(2, "2026-05-01", "2027-05-01", "Rivera", "chen-blueprint.pdf", [
                { level: 1, date: "2026-02-15", trainer: "Rivera" },
                { level: 2, date: "2026-05-01", trainer: "Rivera" },
            ]),
            cmm: cell(1, "2026-06-20", "2027-06-20", "Okafor"),
            solder: cell(0),
            deburr: cell(2, "2026-04-12", "2027-04-12", "Rivera"),
            torque: cell(1, "2026-07-01", "2027-07-01", "Rivera"),
            heattreat: cell(0),
            final: cell(0),
        },
    },
    {
        id: 3, name: "A. Okafor", role: "quality_eng",
        cells: {
            blueprint: cell(4, "2020-01-10", null, "—"),
            cmm: cell(4, "2021-03-05", null, "—"),
            solder: cell(4, "2021-07-22", null, "—"),
            deburr: cell(4, "2020-05-30", null, "—"),
            torque: cell(4, "2024-09-01", "2026-09-01", "—"),
            heattreat: cell(3, "2022-02-14", "2027-02-14", "—"),
            final: cell(4, "2021-11-08", null, "—", "okafor-final-cert.pdf"),
        },
    },
    {
        id: 4, name: "S. Petrov", role: "assembler",
        cells: {
            blueprint: cell(3, "2023-04-01", "2027-04-01", "Okafor"),
            cmm: cell(2, "2025-10-10", "2026-10-10", "Rivera"),
            solder: cell(3, "2024-01-20", "2027-01-20", "Okafor", "petrov-ipc610.pdf", [
                { level: 1, date: "2022-09-01", trainer: "Okafor" },
                { level: 2, date: "2023-05-12", trainer: "Okafor" },
                { level: 3, date: "2024-01-20", trainer: "Okafor" },
            ]),
            deburr: cell(4, "2022-06-15", null, "Okafor"),
            torque: cell(1, "2025-02-01", "2026-02-01", "Rivera"),
            heattreat: cell(2, "2023-03-01", "2025-03-01", "Kowalski"),
            final: cell(0),
        },
    },
    {
        id: 5, name: "L. Nguyen", role: "assembler",
        cells: {
            blueprint: cell(3, "2024-09-01", "2027-09-01", "Okafor"),
            cmm: cell(0),
            solder: cell(2, "2026-02-01", "2027-02-01", "Petrov"),
            deburr: cell(3, "2024-10-05", "2027-10-05", "Rivera"),
            torque: cell(3, "2025-05-05", "2027-05-05", "Rivera"),
            heattreat: cell(0),
            final: cell(0),
        },
    },
    {
        id: 6, name: "D. Kowalski", role: "heat_treat_op",
        cells: {
            blueprint: cell(2, "2025-06-01", "2027-06-01", "Okafor"),
            cmm: cell(0),
            solder: cell(0),
            deburr: cell(2, "2025-06-01", "2027-06-01", "Rivera"),
            torque: cell(2, "2024-09-15", "2026-09-15", "Rivera"),
            heattreat: cell(4, "2019-01-01", null, "—", "kowalski-ht-master.pdf"),
            final: cell(0),
        },
    },
    {
        id: 7, name: "R. Santos", role: "machinist",
        cells: {
            blueprint: cell(1, "2026-07-10", "2027-07-10", "Rivera"),
            cmm: cell(1, "2026-07-10", "2027-07-10", "Okafor"),
            solder: cell(0),
            deburr: cell(2, "2026-06-01", "2027-06-01", "Rivera"),
            torque: cell(0),
            heattreat: cell(0),
            final: cell(0),
        },
    },
    {
        id: 8, name: "T. Bergström", role: "quality_eng",
        cells: {
            blueprint: cell(4, "2021-05-01", null, "—"),
            cmm: cell(3, "2023-08-01", "2026-08-01", "Okafor"),
            solder: cell(4, "2022-02-01", null, "—"),
            deburr: cell(3, "2023-01-01", "2027-01-01", "Okafor"),
            torque: cell(3, "2024-04-01", "2027-04-01", "Rivera"),
            heattreat: cell(3, "2024-06-01", "2027-06-01", "Kowalski"),
            final: cell(3, "2024-09-01", "2027-09-01", "Okafor"),
        },
    },
];

// ---- Derivations -----------------------------------------------------------

type ExpiryStatus = "current" | "expiring" | "expired" | "none";

/** Effective expiry state given a configurable "expiring within N days" window. */
function expiryStatus(c: Cell, windowDays: number): ExpiryStatus {
    if (c.level === 0) return "none";
    if (!c.expires) return "current";
    const today = new Date();
    const exp = new Date(c.expires);
    const days = Math.ceil((exp.getTime() - today.getTime()) / 86_400_000);
    if (days < 0) return "expired";
    if (days <= windowDays) return "expiring";
    return "current";
}

/** Level a role requires for a skill (0 = not part of the role's profile). */
function requiredLevel(op: Operator, skillKey: string): Level {
    return (roleOf(op)?.required[skillKey] ?? 0) as Level;
}

/** Skills where the operator is below their role's required level. */
function roleGaps(op: Operator): string[] {
    return SKILLS.filter((s) => {
        const req = requiredLevel(op, s.key);
        return req > 0 && (op.cells[s.key]?.level ?? 0) < req;
    }).map((s) => s.key);
}

/** How many of the given operators are qualified (>= QUALIFIED_AT) on a skill. */
function coverage(skillKey: string, ops: Operator[]): number {
    return ops.filter((o) => (o.cells[skillKey]?.level ?? 0) >= QUALIFIED_AT).length;
}

// ---- Quarter-pie glyph -----------------------------------------------------

function LevelPie({ level, dim }: { level: Level; dim?: boolean }) {
    const frac = level / 4;
    return (
        <div
            className={`relative mx-auto h-6 w-6 rounded-full border border-border/60 transition-opacity ${LEVEL_META[level].textClass} ${dim ? "opacity-20" : ""}`}
        >
            {level > 0 && (
                <div
                    className="absolute inset-0 rounded-full"
                    style={{
                        background: `conic-gradient(currentColor 0 ${frac}turn, transparent ${frac}turn 1turn)`,
                    }}
                />
            )}
        </div>
    );
}

function ExpiryDot({ status }: { status: ExpiryStatus }) {
    if (status !== "expiring" && status !== "expired") return null;
    const cls = status === "expired" ? "bg-red-500" : "bg-amber-500";
    return (
        <span
            className={`absolute right-0 top-0 h-2 w-2 rounded-full ring-2 ring-background ${cls}`}
            title={status === "expired" ? "Expired" : "Expiring soon"}
        />
    );
}

// ---- Page ------------------------------------------------------------------

export function TrainingMatrixPrototype() {
    const [query, setQuery] = useState("");
    const [roleFilter, setRoleFilter] = useState<string>("all");
    const [highlightTrainees, setHighlightTrainees] = useState(false);
    const [expiryLens, setExpiryLens] = useState(false);
    const [expiryWindow, setExpiryWindow] = useState(60);

    const operators = useMemo(() => {
        const q = query.trim().toLowerCase();
        return OPERATORS.filter((o) => {
            if (roleFilter !== "all" && o.role !== roleFilter) return false;
            if (!q) return true;
            return o.name.toLowerCase().includes(q) || (roleOf(o)?.name.toLowerCase().includes(q) ?? false);
        });
    }, [query, roleFilter]);

    // Instrument summary (over the visible operators).
    const stats = useMemo(() => {
        const peopleWithGaps = operators.filter((o) => roleGaps(o).length > 0).length;
        const spofSkills = SKILLS.filter((s) => coverage(s.key, operators) <= 1).length;
        let expiringCells = 0;
        for (const o of operators) {
            for (const s of SKILLS) {
                const st = expiryStatus(o.cells[s.key] ?? cell(0), expiryWindow);
                if (st === "expiring" || st === "expired") expiringCells++;
            }
        }
        return { peopleWithGaps, spofSkills, expiringCells };
    }, [operators, expiryWindow]);

    const lensActive = highlightTrainees || expiryLens;

    return (
        <div className="container mx-auto p-6">
            <div className="mb-1 flex items-center gap-2">
                <h1 className="text-2xl font-bold">Training Matrix</h1>
                <Badge variant="outline" className="text-xs">/dev prototype · mock data</Badge>
                <div className="ml-auto flex items-center gap-1">
                    <span className="mr-1 text-xs text-muted-foreground">Export matrix:</span>
                    <Button size="sm" variant="outline" onClick={() => toast.success("Matrix exported (Excel) — mock")}>
                        <FileSpreadsheet className="mr-1 h-4 w-4" /> Excel
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => toast.success("Matrix exported (PDF) — mock")}>
                        <FileText className="mr-1 h-4 w-4" /> PDF
                    </Button>
                </div>
            </div>
            <p className="mb-4 max-w-3xl text-sm text-muted-foreground">
                Required-vs-held competence. Each operator is measured against their
                <span className="font-medium text-foreground"> role's</span> required profile;
                a red edge marks a skill below what the role needs. The footer shows how many
                people can cover each skill (single-coverage = staffing risk).
            </p>

            {/* Instrument summary */}
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <SummaryTile label="Operators" value={operators.length} />
                <SummaryTile label="People with role gaps" value={stats.peopleWithGaps} tone={stats.peopleWithGaps ? "warn" : "ok"} />
                <SummaryTile label="Skills at coverage risk" value={stats.spofSkills} tone={stats.spofSkills ? "danger" : "ok"} />
                <SummaryTile label={`Expiring ≤ ${expiryWindow}d`} value={stats.expiringCells} tone={stats.expiringCells ? "warn" : "ok"} />
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
                        {ROLES.map((r) => (
                            <SelectItem key={r.key} value={r.key}>{r.name}</SelectItem>
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
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    within
                    <Input
                        type="number"
                        value={expiryWindow}
                        onChange={(e) => setExpiryWindow(Math.max(0, Number(e.target.value) || 0))}
                        className="h-8 w-16"
                    />
                    days
                </label>
            </div>

            {/* Matrix */}
            <div className="max-h-[70vh] overflow-auto rounded-md border">
                <table className="border-collapse text-sm">
                    <thead>
                        <tr>
                            <th className="sticky left-0 top-0 z-30 min-w-[210px] border-b border-r bg-background p-3 text-left font-medium">
                                Operator · role
                            </th>
                            {SKILLS.map((s) => (
                                <th
                                    key={s.key}
                                    className="sticky top-0 z-20 min-w-[110px] border-b bg-background p-2 text-center align-bottom font-medium"
                                >
                                    <div className="leading-tight">{s.name}</div>
                                </th>
                            ))}
                            <th className="sticky top-0 z-20 min-w-[80px] border-b border-l bg-background p-2 text-center font-medium">
                                Role fit
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {operators.map((op) => {
                            const role = roleOf(op);
                            return (
                                <tr key={op.id} className="hover:bg-muted/30">
                                    <td className="sticky left-0 z-10 border-b border-r bg-background p-3">
                                        <Popover>
                                            <PopoverTrigger asChild>
                                                <button className="block text-left">
                                                    <div className="font-medium hover:underline">{op.name}</div>
                                                    <div className="text-xs text-muted-foreground">{role?.name ?? "—"}</div>
                                                </button>
                                            </PopoverTrigger>
                                            <PopoverContent align="start" className="w-96">
                                                <OperatorProfile op={op} windowDays={expiryWindow} />
                                            </PopoverContent>
                                        </Popover>
                                    </td>

                                    {SKILLS.map((s) => {
                                        const c = op.cells[s.key] ?? cell(0);
                                        const req = requiredLevel(op, s.key);
                                        const gap = req > 0 && c.level < req;
                                        const status = expiryStatus(c, expiryWindow);
                                        const emphasized =
                                            (highlightTrainees && (c.level === 1 || c.level === 2)) ||
                                            (expiryLens && (status === "expiring" || status === "expired"));
                                        const dim = lensActive && !emphasized;
                                        return (
                                            <td
                                                key={s.key}
                                                className={`border-b p-1 text-center ${gap ? "bg-red-500/5" : ""}`}
                                                style={gap ? { boxShadow: "inset 3px 0 0 0 rgb(239 68 68 / 0.55)" } : undefined}
                                            >
                                                <Popover>
                                                    <PopoverTrigger asChild>
                                                        <button
                                                            className="relative mx-auto flex h-9 w-9 items-center justify-center rounded hover:bg-muted"
                                                            aria-label={`${op.name} — ${s.name}: ${LEVEL_META[c.level].label}`}
                                                        >
                                                            <LevelPie level={c.level} dim={dim} />
                                                            <ExpiryDot status={status} />
                                                        </button>
                                                    </PopoverTrigger>
                                                    <PopoverContent className="w-72" align="center">
                                                        <div className="space-y-2">
                                                            <div className="flex items-center gap-2">
                                                                <LevelPie level={c.level} />
                                                                <div>
                                                                    <div className="font-medium">
                                                                        {LEVEL_META[c.level].label}
                                                                        {c.level > 0 && <span className="text-muted-foreground"> · L{c.level}</span>}
                                                                    </div>
                                                                    <div className="text-xs text-muted-foreground">{LEVEL_META[c.level].blurb}</div>
                                                                </div>
                                                            </div>

                                                            <div className="border-t pt-2 text-xs">
                                                                <div className="font-medium">{op.name} — {s.name}</div>
                                                                {req > 0 && (
                                                                    <div className={gap ? "text-red-600 dark:text-red-400" : "text-muted-foreground"}>
                                                                        {role?.name} requires {LEVEL_META[req].label} (L{req})
                                                                        {gap ? " — gap" : " — met"}
                                                                    </div>
                                                                )}
                                                            </div>

                                                            {c.level > 0 ? (
                                                                <div className="space-y-1 border-t pt-2 text-xs text-muted-foreground">
                                                                    <div>Completed: {c.completed ?? "—"}</div>
                                                                    <div>Expires: {c.expires ?? "never"}</div>
                                                                    <div>Trainer / sign-off: {c.trainer ?? "—"}</div>
                                                                    <div className="flex items-center gap-2 pt-1">
                                                                        <StatusBadge
                                                                            status={status === "none" ? "CURRENT" : status.toUpperCase()}
                                                                            size="sm"
                                                                        />
                                                                        {c.evidence && (
                                                                            <a className="inline-flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400" href="#">
                                                                                <FileText className="h-3 w-3" /> {c.evidence}
                                                                            </a>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            ) : (
                                                                <div className="border-t pt-2 text-xs text-muted-foreground">No training on record.</div>
                                                            )}

                                                            {c.history && c.history.length > 0 && (
                                                                <div className="border-t pt-2 text-xs">
                                                                    <div className="mb-1 font-medium">Progression</div>
                                                                    <ol className="space-y-1">
                                                                        {c.history.map((h, i) => (
                                                                            <li key={i} className="flex items-center gap-2 text-muted-foreground">
                                                                                <span className={`h-2 w-2 shrink-0 rounded-full ${LEVEL_META[h.level].textClass}`} style={{ backgroundColor: "currentColor" }} />
                                                                                <span>L{h.level} {LEVEL_META[h.level].label}</span>
                                                                                {h.trainer && <span>· {h.trainer}</span>}
                                                                                <span className="ml-auto tabular-nums">{h.date}</span>
                                                                            </li>
                                                                        ))}
                                                                    </ol>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </PopoverContent>
                                                </Popover>
                                            </td>
                                        );
                                    })}

                                    <td className="border-b border-l bg-background p-2 text-center">
                                        <RoleFitCell op={op} />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>

                    {/* Coverage / single-point-of-failure footer */}
                    <tfoot>
                        <tr>
                            <td className="sticky left-0 z-10 border-t-2 border-r bg-muted/50 p-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                Qualified (L{QUALIFIED_AT}+) · coverage
                            </td>
                            {SKILLS.map((s) => {
                                const n = coverage(s.key, operators);
                                const tone = n <= 1 ? "text-red-600 dark:text-red-400" : n === 2 ? "text-amber-600 dark:text-amber-400" : "text-foreground";
                                return (
                                    <td key={s.key} className="border-t-2 bg-muted/50 p-2 text-center">
                                        <div className={`flex items-center justify-center gap-1 font-semibold tabular-nums ${tone}`}>
                                            {n <= 1 && <AlertTriangle className="h-3 w-3" />}
                                            {n}
                                        </div>
                                        <div className="mx-auto mt-1 flex justify-center gap-0.5">
                                            {Array.from({ length: Math.min(operators.length, 6) }).map((_, i) => (
                                                <span
                                                    key={i}
                                                    className={`h-1.5 w-1.5 rounded-full ${i < n ? "bg-green-500" : "bg-muted-foreground/25"}`}
                                                />
                                            ))}
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

/** Per-person competence profile — the audit "packet" preview + mock export. */
function OperatorProfile({ op, windowDays }: { op: Operator; windowDays: number }) {
    const role = roleOf(op);
    const gaps = roleGaps(op);
    return (
        <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
                <div>
                    <div className="text-sm font-medium">{op.name}</div>
                    <div className="text-xs text-muted-foreground">
                        {role?.name ?? "—"} · {gaps.length === 0 ? "meets role" : `${gaps.length} gap${gaps.length > 1 ? "s" : ""}`}
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    <Button size="sm" variant="outline" onClick={() => toast.success(`${op.name} competence record exported (Excel) — mock`)}>
                        <FileSpreadsheet className="mr-1 h-3.5 w-3.5" /> Excel
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => toast.success(`${op.name} competence record exported (PDF) — mock`)}>
                        <FileText className="mr-1 h-3.5 w-3.5" /> PDF
                    </Button>
                </div>
            </div>
            <div className="space-y-1 border-t pt-2">
                {SKILLS.map((s) => {
                    const c = op.cells[s.key] ?? cell(0);
                    const req = requiredLevel(op, s.key);
                    const gap = req > 0 && c.level < req;
                    const status = expiryStatus(c, windowDays);
                    return (
                        <div key={s.key} className="flex items-center gap-2 text-xs">
                            <LevelPie level={c.level} />
                            <span className="w-28 shrink-0 truncate">{s.name}</span>
                            <span className="tabular-nums text-muted-foreground">L{c.level}</span>
                            {req > 0 && (
                                <span className={gap ? "text-red-600 dark:text-red-400" : "text-muted-foreground"}>
                                    / needs L{req}
                                </span>
                            )}
                            <div className="ml-auto flex items-center gap-1">
                                {(status === "expiring" || status === "expired") && (
                                    <StatusBadge status={status.toUpperCase()} size="sm" />
                                )}
                                {c.evidence && <FileText className="h-3 w-3 text-blue-600 dark:text-blue-400" />}
                            </div>
                        </div>
                    );
                })}
            </div>
            <p className="text-[10px] text-muted-foreground">
                Mock preview — real export uses the per-person training PDF + ExcelExportMixin.
            </p>
        </div>
    );
}

/** Role-fit drill-down: the operator's role profile, requirement by requirement. */
function RoleFitCell({ op }: { op: Operator }) {
    const role = roleOf(op);
    const reqs = (Object.entries(role?.required ?? {}) as [string, Level][])
        .map(([key, req]) => {
            const held = (op.cells[key]?.level ?? 0) as Level;
            return { key, name: SKILLS.find((s) => s.key === key)?.name ?? key, req, held, gap: held < req };
        })
        .sort((a, b) => Number(b.gap) - Number(a.gap));
    const gapCount = reqs.filter((r) => r.gap).length;

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
            <PopoverContent className="w-80" align="end">
                <div className="space-y-2">
                    <div>
                        <div className="text-sm font-medium">{op.name}</div>
                        <div className="text-xs text-muted-foreground">
                            {role?.name ?? "—"} · {gapCount === 0 ? "all requirements met" : `${gapCount} of ${reqs.length} not met`}
                        </div>
                    </div>
                    <div className="space-y-1 border-t pt-2">
                        {reqs.length === 0 && (
                            <div className="text-xs text-muted-foreground">Role has no required competencies.</div>
                        )}
                        {reqs.map((r) => (
                            <div key={r.key} className="flex items-center justify-between gap-2 text-xs">
                                <span className={r.gap ? "font-medium" : ""}>{r.name}</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">needs L{r.req}</span>
                                    <span className="inline-flex items-center gap-1 tabular-nums">
                                        <LevelPie level={r.held} />
                                        L{r.held}
                                    </span>
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
