import { useUserOrders } from "@/hooks/useUserOrderTracker.ts"
import { ExpandableOrderTracker } from "@/components/TrackerCard"
import { Skeleton } from "@/components/ui/skeleton"
import { useEffect, useRef } from "react"

export default function TrackerPage() {
    const {
        data,
        isLoading,
        error,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage
    } = useUserOrders()

    const observerTarget = useRef<HTMLDivElement>(null)

    // Set up intersection observer for infinite scroll
    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
                    fetchNextPage()
                }
            },
            { threshold: 0.1 }
        )

        const currentTarget = observerTarget.current
        if (currentTarget) {
            observer.observe(currentTarget)
        }

        return () => {
            if (currentTarget) {
                observer.unobserve(currentTarget)
            }
        }
    }, [fetchNextPage, hasNextPage, isFetchingNextPage])

    if (isLoading) return <Skeleton className="h-32 w-full" />
    if (error) {
        console.log(error)
        return <p className="text-red-500">Error loading orders</p>
    }

    // Flatten all pages of data
    const allOrders = data?.pages.flatMap(page => page.results) ?? []

    // Filter orders to only show those with gate info or production stages
    const visibleOrders = allOrders.filter(order => {
        const hasGateInfo = order.gate_info !== null && order.gate_info !== undefined
        const hasProductionStages = order.process_stages && order.process_stages.length > 0
        return hasGateInfo || hasProductionStages
    })

    if (visibleOrders.length === 0 && !hasNextPage) {
        return (
            <div className="text-center py-10">
                <p className="text-muted-foreground">No active orders to display</p>
            </div>
        )
    }

    return (
        <>
            {visibleOrders.map((order) => (
                <ExpandableOrderTracker
                    key={order.id}
                    orderNumber={order.id.toString()}
                    customerName={order.company_info?.name ?? "Unknown Customer"}
                    estimatedCompletion={order.estimated_completion}
                    gateInfo={order.gate_info}
                    customerNote={order.customer_note}
                    stages={order.process_stages.map(stage => ({
                        name: stage.name,
                        timestamp: stage.timestamp,
                        is_completed: stage.is_completed,
                        is_current: stage.is_current,
                    }))}
                />
            ))}

            {/* Intersection observer target for infinite scroll */}
            <div ref={observerTarget} className="h-10 flex items-center justify-center">
                {isFetchingNextPage && <Skeleton className="h-32 w-full" />}
            </div>
        </>
    )
}
