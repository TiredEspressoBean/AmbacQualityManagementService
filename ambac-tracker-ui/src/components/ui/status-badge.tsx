import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
    Clock,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    PlayCircle,
    PauseCircle,
    FileEdit,
    Send,
    Archive,
    Ban,
    UserPlus,
    ShieldCheck,
    ShieldX,
    Wrench,
    Gauge,
    CircleDot,
    CircleSlash,
    HelpCircle,
    type LucideIcon,
} from "lucide-react";

/**
 * Status configuration with colors, icons, and labels.
 * Colors use Tailwind classes with dark mode variants.
 */
interface StatusConfig {
    icon: LucideIcon;
    colorClass: string;
    label: string;
}

/**
 * Semantic color mappings - these define the visual meaning.
 * All colors include dark mode support.
 */
const COLORS = {
    // Success states (green)
    success: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800",
    successLight: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800",

    // Warning states (yellow/amber)
    warning: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800",
    warningLight: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",

    // Danger/Error states (red)
    danger: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
    dangerLight: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",

    // Info/Active states (blue)
    info: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
    infoLight: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800",

    // Purple states (verification, special)
    purple: "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
    purpleLight: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-800",

    // Orange states (hold, containment)
    orange: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",

    // Neutral/Gray states
    neutral: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700",
    neutralLight: "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800/50 dark:text-gray-400 dark:border-gray-700",
} as const;

/**
 * Master status configuration.
 * Keys are normalized to UPPERCASE for consistent lookup.
 */
const STATUS_CONFIG: Record<string, StatusConfig> = {
    // ═══════════════════════════════════════════════════════════════
    // APPROVAL STATUSES
    // ═══════════════════════════════════════════════════════════════
    APPROVED: { icon: CheckCircle2, colorClass: COLORS.success, label: "Approved" },
    REJECTED: { icon: XCircle, colorClass: COLORS.danger, label: "Rejected" },
    DELEGATED: { icon: UserPlus, colorClass: COLORS.info, label: "Delegated" },
    NOT_REQUIRED: { icon: CircleSlash, colorClass: COLORS.neutral, label: "Not Required" },

    // ═══════════════════════════════════════════════════════════════
    // DOCUMENT STATUSES
    // ═══════════════════════════════════════════════════════════════
    DRAFT: { icon: FileEdit, colorClass: COLORS.neutral, label: "Draft" },
    UNDER_REVIEW: { icon: Clock, colorClass: COLORS.warning, label: "Under Review" },
    RELEASED: { icon: Send, colorClass: COLORS.info, label: "Released" },
    OBSOLETE: { icon: Archive, colorClass: COLORS.danger, label: "Obsolete" },

    // ═══════════════════════════════════════════════════════════════
    // WORKFLOW/TASK STATUSES
    // ═══════════════════════════════════════════════════════════════
    PENDING: { icon: Clock, colorClass: COLORS.warning, label: "Pending" },
    IN_PROGRESS: { icon: PlayCircle, colorClass: COLORS.info, label: "In Progress" },
    COMPLETED: { icon: CheckCircle2, colorClass: COLORS.success, label: "Completed" },
    ON_HOLD: { icon: PauseCircle, colorClass: COLORS.orange, label: "On Hold" },
    CANCELLED: { icon: Ban, colorClass: COLORS.neutral, label: "Cancelled" },
    BLOCKED: { icon: XCircle, colorClass: COLORS.danger, label: "Blocked" },
    NOT_STARTED: { icon: CircleDot, colorClass: COLORS.neutral, label: "Not Started" },
    WAITING_FOR_OPERATOR: { icon: Clock, colorClass: COLORS.purple, label: "Waiting for Operator" },

    // ═══════════════════════════════════════════════════════════════
    // ORDER STATUSES
    // ═══════════════════════════════════════════════════════════════
    RFI: { icon: HelpCircle, colorClass: COLORS.neutral, label: "RFI" },

    // ═══════════════════════════════════════════════════════════════
    // CAPA STATUSES
    // ═══════════════════════════════════════════════════════════════
    OPEN: { icon: CircleDot, colorClass: COLORS.info, label: "Open" },
    PENDING_VERIFICATION: { icon: ShieldCheck, colorClass: COLORS.purple, label: "Pending Verification" },
    CLOSED: { icon: CheckCircle2, colorClass: COLORS.success, label: "Closed" },

    // ═══════════════════════════════════════════════════════════════
    // VERIFICATION STATUSES
    // ═══════════════════════════════════════════════════════════════
    UNVERIFIED: { icon: ShieldX, colorClass: COLORS.neutral, label: "Unverified" },
    VERIFIED: { icon: ShieldCheck, colorClass: COLORS.success, label: "Verified" },
    DISPUTED: { icon: AlertTriangle, colorClass: COLORS.danger, label: "Disputed" },

    // ═══════════════════════════════════════════════════════════════
    // EFFECTIVENESS RESULTS
    // ═══════════════════════════════════════════════════════════════
    CONFIRMED: { icon: CheckCircle2, colorClass: COLORS.success, label: "Effective" },
    NOT_EFFECTIVE: { icon: XCircle, colorClass: COLORS.danger, label: "Not Effective" },
    INCONCLUSIVE: { icon: HelpCircle, colorClass: COLORS.warning, label: "Inconclusive" },

    // ═══════════════════════════════════════════════════════════════
    // QUALITY REPORT STATUSES
    // ═══════════════════════════════════════════════════════════════
    PASS: { icon: CheckCircle2, colorClass: COLORS.success, label: "Pass" },
    FAIL: { icon: XCircle, colorClass: COLORS.danger, label: "Fail" },

    // ═══════════════════════════════════════════════════════════════
    // EQUIPMENT STATUSES
    // ═══════════════════════════════════════════════════════════════
    IN_SERVICE: { icon: CheckCircle2, colorClass: COLORS.success, label: "In Service" },
    OUT_OF_SERVICE: { icon: XCircle, colorClass: COLORS.danger, label: "Out of Service" },
    IN_CALIBRATION: { icon: Gauge, colorClass: COLORS.info, label: "In Calibration" },
    IN_MAINTENANCE: { icon: Wrench, colorClass: COLORS.warning, label: "In Maintenance" },
    RETIRED: { icon: Archive, colorClass: COLORS.neutral, label: "Retired" },

    // ═══════════════════════════════════════════════════════════════
    // TRAINING STATUSES
    // ═══════════════════════════════════════════════════════════════
    VALID: { icon: CheckCircle2, colorClass: COLORS.success, label: "Valid" },
    EXPIRING_SOON: { icon: Clock, colorClass: COLORS.warning, label: "Expiring Soon" },
    EXPIRED: { icon: XCircle, colorClass: COLORS.danger, label: "Expired" },

    // ═══════════════════════════════════════════════════════════════
    // CALIBRATION STATUSES & RESULTS
    // ═══════════════════════════════════════════════════════════════
    CURRENT: { icon: CheckCircle2, colorClass: COLORS.success, label: "Current" },
    DUE_SOON: { icon: Clock, colorClass: COLORS.warning, label: "Due Soon" },
    OVERDUE: { icon: XCircle, colorClass: COLORS.danger, label: "Overdue" },
    IN_TOLERANCE: { icon: CheckCircle2, colorClass: COLORS.success, label: "In Tolerance" },
    OUT_OF_TOLERANCE: { icon: XCircle, colorClass: COLORS.danger, label: "Out of Tolerance" },
    ADJUSTED: { icon: Wrench, colorClass: COLORS.warning, label: "Adjusted" },
    LIMITED: { icon: AlertTriangle, colorClass: COLORS.warning, label: "Limited Use" },

    // ═══════════════════════════════════════════════════════════════
    // SEVERITY LEVELS
    // ═══════════════════════════════════════════════════════════════
    CRITICAL: { icon: AlertTriangle, colorClass: COLORS.danger, label: "Critical" },
    MAJOR: { icon: AlertTriangle, colorClass: COLORS.orange, label: "Major" },
    MINOR: { icon: CircleDot, colorClass: COLORS.warning, label: "Minor" },

    // ═══════════════════════════════════════════════════════════════
    // PRIORITY LEVELS
    // ═══════════════════════════════════════════════════════════════
    LOW: { icon: CircleDot, colorClass: COLORS.neutral, label: "Low" },
    NORMAL: { icon: CircleDot, colorClass: COLORS.info, label: "Normal" },
    HIGH: { icon: AlertTriangle, colorClass: COLORS.orange, label: "High" },
    URGENT: { icon: AlertTriangle, colorClass: COLORS.danger, label: "Urgent" },

    // ═══════════════════════════════════════════════════════════════
    // TASK TYPES
    // ═══════════════════════════════════════════════════════════════
    CONTAINMENT: { icon: PauseCircle, colorClass: COLORS.orange, label: "Containment" },
    CORRECTIVE: { icon: Wrench, colorClass: COLORS.info, label: "Corrective" },
    PREVENTIVE: { icon: ShieldCheck, colorClass: COLORS.purple, label: "Preventive" },

    // ═══════════════════════════════════════════════════════════════
    // CLASSIFICATION LEVELS
    // ═══════════════════════════════════════════════════════════════
    PUBLIC: { icon: CircleDot, colorClass: COLORS.success, label: "Public" },
    INTERNAL: { icon: CircleDot, colorClass: COLORS.info, label: "Internal" },
    CONFIDENTIAL: { icon: ShieldCheck, colorClass: COLORS.danger, label: "Confidential" },

    // ═══════════════════════════════════════════════════════════════
    // NUMERIC ENUMS (from backend)
    // ═══════════════════════════════════════════════════════════════
    // Priority: 1=Urgent, 2=High, 3=Normal, 4=Low
    "1": { icon: AlertTriangle, colorClass: COLORS.danger, label: "Urgent" },
    "2": { icon: AlertTriangle, colorClass: COLORS.orange, label: "High" },
    "3": { icon: CircleDot, colorClass: COLORS.info, label: "Normal" },
    "4": { icon: CircleDot, colorClass: COLORS.neutral, label: "Low" },

    // Action: 0=Create, 1=Update, 2=Delete, 3=Access (audit log)
    "0": { icon: CircleDot, colorClass: COLORS.success, label: "Create" },
    // "1" already mapped to Urgent above - audit uses action_display instead
    // "2" would conflict - audit uses action_display instead
    // "3" would conflict - audit uses action_display instead
};

// Default fallback for unknown statuses
const DEFAULT_CONFIG: StatusConfig = {
    icon: HelpCircle,
    colorClass: COLORS.neutral,
    label: "Unknown",
};

/**
 * Normalizes status string for lookup.
 * Converts to uppercase and replaces spaces/hyphens with underscores.
 * Handles non-string inputs gracefully.
 */
function normalizeStatus(status: unknown): string {
    if (status == null) return "UNKNOWN";
    const str = typeof status === "string" ? status : String(status);
    return str.toUpperCase().replace(/[\s-]/g, "_");
}

export interface StatusBadgeProps {
    /** The status value (case-insensitive, supports snake_case, SCREAMING_CASE, or spaces). Accepts non-string values which are converted to strings. */
    status: string | number | null | undefined;
    /** Optional display label override. If not provided, uses the configured label or formats the status. */
    label?: string;
    /** Whether to show the icon. Defaults to true. */
    showIcon?: boolean;
    /** Size variant */
    size?: "sm" | "default";
    /** Additional className */
    className?: string;
}

/**
 * Unified status badge component with consistent styling across the app.
 *
 * @example
 * // Basic usage
 * <StatusBadge status="APPROVED" />
 * <StatusBadge status="pending" />
 * <StatusBadge status="in_progress" />
 *
 * @example
 * // With custom label
 * <StatusBadge status="IN_PROGRESS" label="Working..." />
 *
 * @example
 * // Without icon
 * <StatusBadge status="COMPLETED" showIcon={false} />
 *
 * @example
 * // Small size
 * <StatusBadge status="APPROVED" size="sm" />
 */
export function StatusBadge({
    status,
    label,
    showIcon = true,
    size = "default",
    className,
}: StatusBadgeProps) {
    const normalizedStatus = normalizeStatus(status);
    const config = STATUS_CONFIG[normalizedStatus] || DEFAULT_CONFIG;

    // Use provided label, configured label, or format the status string
    const statusStr = status == null ? "Unknown" : String(status);
    const displayLabel = label ?? config.label ?? statusStr.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

    const Icon = config.icon;

    const sizeClasses = size === "sm"
        ? "text-xs px-1.5 py-0.5 gap-1"
        : "text-xs px-2 py-1 gap-1.5";

    const iconSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";

    return (
        <Badge
            variant="outline"
            className={cn(
                "inline-flex items-center font-medium",
                sizeClasses,
                config.colorClass,
                className
            )}
        >
            {showIcon && <Icon className={cn(iconSize, "shrink-0")} />}
            <span>{displayLabel}</span>
        </Badge>
    );
}

/**
 * Helper to get just the color classes for a status (useful for custom rendering).
 */
export function getStatusColors(status: string): string {
    const normalizedStatus = normalizeStatus(status);
    return STATUS_CONFIG[normalizedStatus]?.colorClass ?? COLORS.neutral;
}

/**
 * Helper to get the icon component for a status.
 */
export function getStatusIcon(status: string): LucideIcon {
    const normalizedStatus = normalizeStatus(status);
    return STATUS_CONFIG[normalizedStatus]?.icon ?? HelpCircle;
}

/**
 * Export the color constants for custom usage.
 */
export { COLORS as STATUS_COLORS };
