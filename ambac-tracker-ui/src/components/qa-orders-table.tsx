import {
    Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {useState} from "react";
import {Skeleton} from "@/components/ui/skeleton.tsx";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select.tsx";
import {Button} from "@/components/ui/button.tsx";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders.ts";
import {QAOrderActionsCell} from "@/components/qa_orders_action_cell.tsx";
// import {useDebounce} from "@/hooks/useDebounce.ts";

const SORT_OPTIONS = [
    { label: "Created (Newest)", value: "-created_at" },
    { label: "Created (Oldest)", value: "created_at" },
    { label: "Order # (A-Z)", value: "order_number" },
    { label: "Order # (Z-A)", value: "-order_number" },
    { label: "Name (A-Z)", value: "name" },
    { label: "Name (Z-A)", value: "-name" },
]

export default function QAOrdersTable() {
    const [offset, setOffset] = useState(0);
    const [limit] = useState(10);
    const [ordering, setOrdering] = useState<string | undefined>(undefined);

    // Debounce the search term
    // const debouncedSearch = useDebounce(filters, 300);

    const {data, isLoading, error} = useRetrieveOrders({
        offset: offset,
        ordering: ordering,
        archived: false,
    })

    if (isLoading) return <Skeleton className="h-32 w-full"/>;
    if (error) {
        console.log(error)
        return <p className="text-red-500">Error loading orders</p>;
    }

    const orders = data?.results ?? [];
    const total = data?.count ?? 0;


    return (<div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">Orders in Process</h2>
                <Select onValueChange={setOrdering} value={ordering}>
                    <SelectTrigger className="w-[220px]">
                        <SelectValue placeholder="Sort by..."/>
                    </SelectTrigger>
                    <SelectContent>
                        {SORT_OPTIONS.map((option) => (<SelectItem key={option.value} value={option.value}>
                                {option.label}
                            </SelectItem>))}
                    </SelectContent>
                </Select>
            </div>
            <Table>
                <TableCaption>Orders</TableCaption>
                <TableHeader>
                    <TableRow>
                        <TableHead>Order #</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Estimated Completion</TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {orders.map((order) => (
                        <TableRow key={order.id}>
                            <TableCell>
                                <span className="font-mono text-sm text-primary">{order.order_number || "—"}</span>
                            </TableCell>
                            <TableCell>{order.name}</TableCell>
                            <TableCell>{order.estimated_completion || "—"}</TableCell>
                            <TableCell>{order.company_name || "—"}</TableCell>
                            <TableCell>
                                {order.customer_first_name || order.customer_last_name
                                    ? `${order.customer_first_name || ""} ${order.customer_last_name || ""}`.trim()
                                    : "—"}
                            </TableCell>
                            <QAOrderActionsCell order={order} />
                        </TableRow>
                    ))}
                </TableBody>
            </Table>

            <div className="flex justify-between items-center">
                <Button
                    variant="secondary"
                    onClick={() => setOffset(Math.max(offset - limit, 0))}
                    disabled={offset === 0}
                >
                    Previous
                </Button>
                <span>
          Page {Math.floor(offset / limit) + 1} of {Math.ceil(total / limit)}
        </span>
                <Button
                    variant="secondary"
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                >
                    Next
                </Button>
            </div>
        </div>)
}