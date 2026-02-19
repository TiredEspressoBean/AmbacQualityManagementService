import { useState } from "react"
import {
    Collapsible,
    CollapsibleContent,
} from "@/components/ui/collapsible"
import {
    CheckCircle,
    Clock,
    Circle,
    Building2,
    User,
    ChevronDown,
    ExternalLink,
    Timer,
    MessageSquare,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { formatDistanceToNow, format, differenceInDays } from "date-fns"
import { Link } from "@tanstack/react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

type OrderStage = {
    name: string
    timestamp: string | null
    is_current: boolean
    is_completed: boolean
}

type HubSpotGate = {
    name: string
    full_name: string
    is_current: boolean
    is_completed: boolean
}

type GateInfo = {
    current_gate_name: string
    current_gate_full_name: string
    is_in_progress: boolean
    current_position?: number
    total_gates?: number
    progress_percent?: number
    gates: HubSpotGate[]
}

type NoteEntry = {
    timestamp: string | null
    user: string
    visibility: string
    message: string
}

type OrderTrackerProps = {
    orderId: string
    orderName?: string
    customerName?: string
    companyName?: string
    stages: OrderStage[]
    estimatedCompletion?: string | null
    gateInfo?: GateInfo | null
    latestNote?: NoteEntry | null
}

function getStatusIcon(stage: { is_completed: boolean; is_current: boolean }, size: "sm" | "md" = "md") {
    const sizeClass = size === "sm" ? "w-4 h-4" : "w-5 h-5"
    if (stage.is_completed) {
        return <CheckCircle className={cn("text-green-500", sizeClass)} />
    } else if (stage.is_current) {
        return <Clock className={cn("text-yellow-500 animate-pulse", sizeClass)} />
    } else {
        return <Circle className={cn("text-muted-foreground/40", sizeClass)} />
    }
}

export function ExpandableOrderTracker({
    orderId,
    orderName,
    customerName,
    companyName,
    stages,
    estimatedCompletion,
    gateInfo,
    latestNote
}: OrderTrackerProps) {
    const [open, setOpen] = useState(false)

    const total = stages.length
    const completed = stages.filter(s => s.is_completed).length
    const progress = total > 0 ? (completed / total) * 100 : 0
    const currentStage = stages.find(s => s.is_current)?.name || ""

    // Calculate days until delivery
    const daysUntilDelivery = estimatedCompletion
        ? differenceInDays(new Date(estimatedCompletion), new Date())
        : null

    const displayName = orderName || `Order #${orderId}`

    return (
        <Collapsible open={open} onOpenChange={setOpen}>
            <div
                onClick={() => setOpen(prev => !prev)}
                className={cn(
                    "cursor-pointer select-none",
                    "bg-card border rounded-xl shadow-sm transition-all duration-200 hover:shadow-md",
                    "p-5 w-full max-w-2xl mx-auto mb-4",
                    open && "ring-1 ring-primary/20"
                )}
            >
                {/* Header Row */}
                <div className="flex items-start justify-between gap-4 mb-4">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-lg font-semibold truncate">{displayName}</h3>
                            <ChevronDown className={cn(
                                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                                open && "rotate-180"
                            )} />
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                            {companyName && (
                                <span className="flex items-center gap-1">
                                    <Building2 className="h-3.5 w-3.5" />
                                    {companyName}
                                </span>
                            )}
                            {customerName && (
                                <span className="flex items-center gap-1">
                                    <User className="h-3.5 w-3.5" />
                                    {customerName}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Delivery Date Badge */}
                    {estimatedCompletion && (
                        <div className="text-right shrink-0">
                            <p className="text-xs text-muted-foreground mb-1">Delivery</p>
                            <p className="text-sm font-semibold">
                                {format(new Date(estimatedCompletion), "MMM d, yyyy")}
                            </p>
                            {daysUntilDelivery !== null && daysUntilDelivery >= 0 && (
                                <Badge variant="outline" className="mt-1 text-xs">
                                    <Timer className="h-3 w-3 mr-1" />
                                    {daysUntilDelivery === 0 ? "Today" : `${daysUntilDelivery}d`}
                                </Badge>
                            )}
                        </div>
                    )}
                </div>

                {/* Progress Section */}
                {stages.length > 0 && (
                    <div className="mb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                            <span>{currentStage ? `Current: ${currentStage}` : "Not started"}</span>
                            <span>{completed}/{total} stages</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                            <div
                                className="bg-primary h-2 rounded-full transition-all duration-500"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* HubSpot Gate Progress (collapsed view) */}
                {gateInfo && gateInfo.is_in_progress && !open && (
                    <div className="pt-3 border-t">
                        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                            <span className="text-blue-600 dark:text-blue-400 font-medium">
                                {gateInfo.current_gate_name}
                            </span>
                            <span>Stage {gateInfo.current_position}/{gateInfo.total_gates}</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-1.5">
                            <div
                                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${gateInfo.progress_percent}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Expanded Content */}
                <CollapsibleContent className="space-y-4 pt-4">
                    {/* Latest Note */}
                    {latestNote && (
                        <div className="p-3 bg-muted/50 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                                <MessageSquare className="h-3 w-3 text-muted-foreground" />
                                <span className="text-xs font-medium">{latestNote.user}</span>
                                {latestNote.timestamp && (
                                    <span className="text-xs text-muted-foreground">
                                        {formatDistanceToNow(new Date(latestNote.timestamp), { addSuffix: true })}
                                    </span>
                                )}
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{latestNote.message}</p>
                        </div>
                    )}

                    {/* HubSpot Gates (expanded) */}
                    {gateInfo && gateInfo.gates && gateInfo.gates.length > 0 && (
                        <div>
                            <h4 className="text-xs font-medium text-muted-foreground mb-2">Pipeline Stages</h4>
                            <div className="space-y-1.5">
                                {gateInfo.gates.map((gate, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        {getStatusIcon(gate, "sm")}
                                        <span
                                            className={cn(
                                                "text-xs",
                                                gate.is_current
                                                    ? "font-medium text-blue-600 dark:text-blue-400"
                                                    : gate.is_completed
                                                        ? "text-green-600 dark:text-green-400"
                                                        : "text-muted-foreground"
                                            )}
                                        >
                                            {gate.name}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Production Stages (expanded) */}
                    {stages.length > 0 && (
                        <div>
                            <h4 className="text-xs font-medium text-muted-foreground mb-2">Production Progress</h4>
                            <div className="space-y-1.5">
                                {stages.map((stage, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        {getStatusIcon(stage, "sm")}
                                        <span
                                            className={cn(
                                                "text-xs flex-1",
                                                stage.is_current
                                                    ? "font-medium text-yellow-600 dark:text-yellow-400"
                                                    : stage.is_completed
                                                        ? "text-green-600 dark:text-green-400"
                                                        : "text-muted-foreground"
                                            )}
                                        >
                                            {stage.name}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            {stage.timestamp
                                                ? formatDistanceToNow(new Date(stage.timestamp), { addSuffix: true })
                                                : ""}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* View Details Link */}
                    <div className="pt-2 border-t">
                        <Link
                            to={`/orders/$orderNumber`}
                            params={{ orderNumber: orderId }}
                            onClick={e => e.stopPropagation()}
                        >
                            <Button variant="outline" size="sm" className="w-full">
                                View Full Details
                                <ExternalLink className="h-3.5 w-3.5 ml-2" />
                            </Button>
                        </Link>
                    </div>
                </CollapsibleContent>
            </div>
        </Collapsible>
    )
}
