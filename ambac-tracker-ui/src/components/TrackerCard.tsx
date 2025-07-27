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

type OrderTrackerProps = {
    orderNumber: string
    customerName?: string
    stages: OrderStage[]
    estimatedCompletion?: string | null // ISO timestamp
}

export function ExpandableOrderTracker({orderNumber, customerName, stages, estimatedCompletion}: OrderTrackerProps) {
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

                <ProgressLabel currentStage={currentStage} progress={progress} />

                <p className="text-sm text-muted-foreground mb-2">
                    {completed}/{total} stages completed
                </p>

                <CollapsibleContent className="space-y-4 pt-2">
                    {stages.map((stage, idx) => (
                        <div key={idx} className="flex items-start gap-3">
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
                </CollapsibleContent>
            </div>
        </Collapsible>
    )
}
