import { useUserOrders } from "@/hooks/useUserOrderTracker.ts"
import { ExpandableOrderTracker } from "@/components/TrackerCard"
import { Skeleton } from "@/components/ui/skeleton"

export default function TrackerPage() {
    const { data, isLoading, error } = useUserOrders()

    if (isLoading) return <Skeleton className="h-32 w-full" />
    if (error) {
        console.log(error)
        return <p className="text-red-500">Error loading orders</p>
    }

    return (
        <>
            {(data ?? []).map((order) => (
                <ExpandableOrderTracker
                    key={order.id}
                    orderNumber={order.id.toString()}
                    customerName={order.customer?.parent_company?.name ?? "Unknown Customer"}
                    estimatedCompletion={order.estimated_completion}
                    stages={order.stages.map(stage => ({
                        name: stage.name,
                        timestamp: stage.timestamp,
                        is_completed: stage.is_completed,
                        is_current: stage.is_current,
                    }))}
                />
            ))}
        </>
    )
}
