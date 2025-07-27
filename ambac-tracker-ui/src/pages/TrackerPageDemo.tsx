// import { useUserOrders } from "@/hooks/useUserOrderTracker.ts"
import { ExpandableOrderTracker } from "@/components/TrackerCard"
import { Skeleton } from "@/components/ui/skeleton"

const mockData = [
    {
        id: 1,
        order_number: "AMBAC-2025-0931",
        customer: {
            parent_company: { name: "Acme Corp" },
        },
        estimated_completion: "2025-07-29T00:00:00Z",
        stages: [
            {
                name: "Order Received",
                timestamp: "2025-06-21T08:00:00Z",
                is_completed: true,
                is_current: false,
            },
            {
                name: "Manufacturing",
                timestamp: "2025-06-22T12:00:00Z",
                is_completed: true,
                is_current: false,
            },
            {
                name: "Quality Check",
                timestamp: null,
                is_completed: false,
                is_current: true,
            },
            {
                name: "Packing",
                timestamp: null,
                is_completed: false,
                is_current: false,
            },
            {
                name: "Shipping",
                timestamp: null,
                is_completed: false,
                is_current: false,
            },
        ],
    },
    {
        id: 2,
        order_number: "AMBAC-2025-0932",
        customer: {
            parent_company: { name: "Umbrella Industries" },
        },
        estimated_completion: "2025-08-03T00:00:00Z",
        stages: [
            {
                name: "Order Received",
                timestamp: "2025-06-20T09:30:00Z",
                is_completed: true,
                is_current: false,
            },
            {
                name: "Manufacturing",
                timestamp: null,
                is_completed: false,
                is_current: true,
            },
            {
                name: "Quality Check",
                timestamp: null,
                is_completed: false,
                is_current: false,
            },
            {
                name: "Packing",
                timestamp: null,
                is_completed: false,
                is_current: false,
            },
            {
                name: "Shipping",
                timestamp: null,
                is_completed: false,
                is_current: false,
            },
        ],
    },
]


export default function TrackerPage() {
    const data = mockData
    const isLoading = false
    const error = null

    console.log(data)

    if (isLoading) return <Skeleton className="h-32 w-full" />
    if (error) return <p className="text-red-500">Error loading orders</p>

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
