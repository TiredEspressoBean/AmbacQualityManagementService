import { useState } from "react"
import {
    Collapsible,
    CollapsibleContent,
} from "@/components/ui/collapsible"
// import { Progress } from "@/components/ui/progress"
import {
    CheckCircle,
    Clock,
    Circle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { formatDistanceToNow, formatDistance } from "date-fns"
import {Link} from "@tanstack/react-router";
import ProgressLabel from "@/components/ProgressLabel.tsx";

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

type OrderTrackerProps = {
    orderNumber: string
    customerName?: string
    stages: OrderStage[]
    estimatedCompletion?: string | null // ISO timestamp
    gateInfo?: GateInfo | null
    customerNote?: string | null
}

export function ExpandableOrderTracker({orderNumber, customerName, stages, estimatedCompletion, gateInfo, customerNote}: OrderTrackerProps) {
    const [open, setOpen] = useState(false)

    const total = stages.length
    const completed = stages.filter(s => s.is_completed).length
    const progress = (completed / total) * 100
    const currentStage = stages.find(s => s.is_current)?.name || ""

    function getStatusIcon(stage: OrderStage) {
        if (stage.is_completed) {
            return <CheckCircle className="text-green-600 w-5 h-5 mt-1"/>
        } else if (stage.is_current) {
            return <Clock className="text-yellow-500 animate-pulse w-5 h-5 mt-1" />
        } else {
            return <Circle className="text-gray-300 w-5 h-5 mt-1" />
        }
    }

    return (
        <Collapsible open={open} onOpenChange={setOpen}>
            <div
                onClick={() => setOpen(prev => !prev)}
                className={cn(
                    "cursor-pointer select-none bg-gradient-to-br from-slate-50 to-slate-100 dark:from-zinc-900 dark:to-zinc-800",
                    "rounded-xl border shadow-sm transition-all duration-200 hover:shadow-md",
                    "p-4 w-full max-w-xl mx-auto mb-4"
                )}
                style={{ ['--progress-width' as string]: `${progress}%` }}
            >
                <div className="flex items-center justify-between mb-3">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Order #{orderNumber}</h3>
                        {customerName && (
                            <p className="text-sm text-muted-foreground">Customer: {customerName}</p>
                        )}
                        {estimatedCompletion && (
                            <p className="text-sm text-muted-foreground">
                                Estimated delivery in {formatDistance(new Date(), new Date(estimatedCompletion))}
                            </p>
                        )}
                    </div>
                    <Link
                        to={`/orders/$orderNumber`}
                        className="text-sm text-blue-600 hover:underline"
                        onClick={e => e.stopPropagation()}
                        params={{orderNumber}}
                    >
                        View details
                    </Link>
                </div>

                {stages.length > 0 && (
                    <>
                        <ProgressLabel currentStage={currentStage} progress={progress} />

                        <p className="text-sm text-muted-foreground mb-2">
                            {completed}/{total} stages completed
                        </p>
                    </>
                )}

                {/* HubSpot Gate Progress Section */}
                {gateInfo && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        {gateInfo.is_in_progress && gateInfo.current_position && gateInfo.total_gates ? (
                            <>
                                <p className="text-sm font-medium text-blue-700 dark:text-blue-400 mb-2">
                                    Order Stage: {gateInfo.current_gate_name}
                                </p>
                                <div className="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-2">
                                    <div
                                        className="bg-blue-500 h-2.5 rounded-full transition-all duration-300"
                                        style={{ width: `${gateInfo.progress_percent}%` }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Stage {gateInfo.current_position} of {gateInfo.total_gates} ({gateInfo.progress_percent?.toFixed(0)}%)
                                </p>
                            </>
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                Status: <span className="font-medium">{gateInfo.current_gate_full_name}</span>
                            </p>
                        )}
                    </div>
                )}

                <CollapsibleContent className="space-y-4 pt-2">
                    {/* Customer Note Section */}
                    {customerNote && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                            <p className="text-xs font-semibold text-blue-900 dark:text-blue-300 mb-1">Customer Note</p>
                            <p className="text-sm text-blue-800 dark:text-blue-200">{customerNote}</p>
                        </div>
                    )}

                    {/* HubSpot Gates Section */}
                    {gateInfo && gateInfo.gates && gateInfo.gates.length > 0 && (
                        <div className="mb-4">
                            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-3">Order Pipeline Stages</h4>
                            {gateInfo.gates.map((gate, idx) => (
                                <div key={idx} className="flex items-start gap-3 mb-3">
                                    {getStatusIcon({
                                        name: gate.name,
                                        is_current: gate.is_current,
                                        is_completed: gate.is_completed,
                                        timestamp: null
                                    })}
                                    <div>
                                        <p
                                            className={cn(
                                                "text-sm font-medium",
                                                gate.is_current ? "text-blue-800 dark:text-blue-300" :
                                                    gate.is_completed ? "text-green-700 dark:text-green-400" : "text-gray-700 dark:text-gray-300"
                                            )}
                                        >
                                            {gate.name}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {gate.is_completed ? "Completed" : gate.is_current ? "Current stage" : "Upcoming"}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Production Stages Section */}
                    {stages.length > 0 && (
                        <div>
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Production Progress</h4>
                            {stages.map((stage, idx) => (
                                <div key={idx} className="flex items-start gap-3 mb-3">
                                    {getStatusIcon(stage)}
                                    <div>
                                        <p
                                            className={cn(
                                                "text-sm font-medium",
                                                stage.is_current ? "text-yellow-800 dark:text-yellow-300" :
                                                    stage.is_completed ? "text-green-700 dark:text-green-400" : "text-gray-700 dark:text-gray-300"
                                            )}
                                        >
                                            {stage.name}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {stage.timestamp
                                                ? `Updated ${formatDistanceToNow(new Date(stage.timestamp), { addSuffix: true })}`
                                                : "Pending"}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CollapsibleContent>
            </div>
        </Collapsible>
    )
}
