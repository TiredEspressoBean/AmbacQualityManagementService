import { useCapaStats } from "@/hooks/useCapaStats";
import { Skeleton } from "@/components/ui/skeleton";
import {
    FileText,
    Clock,
    CheckCircle2,
    AlertTriangle,
} from "lucide-react";

export function CapaStatsCards() {
    const { data: stats, isLoading, error } = useCapaStats();

    if (isLoading) {
        return <Skeleton className="h-5 w-96" />;
    }

    if (error || !stats) {
        return null;
    }

    const activeCount = stats.by_status.open + stats.by_status.in_progress;
    const pendingVerification = stats.by_status.pending_verification;

    const cards = [
        {
            label: "Active",
            value: activeCount,
            icon: FileText,
            color: "text-blue-600",
            bgColor: "bg-blue-50",
        },
        {
            label: "Pending Verification",
            value: pendingVerification,
            icon: Clock,
            color: "text-amber-600",
            bgColor: "bg-amber-50",
        },
        {
            label: "Overdue",
            value: stats.overdue,
            icon: AlertTriangle,
            color: stats.overdue > 0 ? "text-red-600" : "text-muted-foreground",
            bgColor: stats.overdue > 0 ? "bg-red-50" : "bg-muted/50",
        },
        {
            label: "Closed",
            value: stats.by_status.closed,
            icon: CheckCircle2,
            color: "text-green-600",
            bgColor: "bg-green-50",
        },
    ];

    const severityItems = [
        { label: "Critical", value: stats.by_severity.CRITICAL, color: "bg-red-500" },
        { label: "Major", value: stats.by_severity.MAJOR, color: "bg-orange-500" },
        { label: "Minor", value: stats.by_severity.MINOR, color: "bg-yellow-500" },
    ];

    const totalSeverity = severityItems.reduce((sum, item) => sum + item.value, 0);

    return (
        <div className="space-y-4">
            {/* Main stats - inline compact */}
            <div className="flex items-center gap-6 text-sm">
                {cards.map((card) => (
                    <div key={card.label} className="flex items-center gap-2">
                        <card.icon className={`h-4 w-4 ${card.color}`} />
                        <span className="font-medium">{card.value}</span>
                        <span className="text-muted-foreground">{card.label}</span>
                    </div>
                ))}
            </div>

            {/* Severity breakdown - compact bar */}
            {totalSeverity > 0 && (
                <div className="flex items-center gap-4 text-sm">
                    <span className="text-muted-foreground whitespace-nowrap">By Severity:</span>
                    <div className="flex-1 flex items-center gap-2">
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden flex">
                            {severityItems.map((item) => (
                                item.value > 0 && (
                                    <div
                                        key={item.label}
                                        className={`h-full ${item.color}`}
                                        style={{ width: `${(item.value / totalSeverity) * 100}%` }}
                                    />
                                )
                            ))}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            {severityItems.map((item) => (
                                <span key={item.label} className="flex items-center gap-1">
                                    <span className={`w-2 h-2 rounded-full ${item.color}`} />
                                    {item.label}: {item.value}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
