import {
    Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {useState} from "react";
import {Skeleton} from "@/components/ui/skeleton.tsx";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select.tsx";
import {Button} from "@/components/ui/button.tsx";
import {useRetrieveOrders} from "@/hooks/useRetrieveOrders.ts";
import {EditOrderActionsCell} from "@/components/edit-orders-action-cell.tsx";
import {Input} from "@/components/ui/input.tsx";
import {useDebounce} from "@/hooks/useDebounce.ts";
import {useNavigate} from "@tanstack/react-router";
import {ordersCreateFormRoute} from "@/router"

const SORT_OPTIONS = [{label: "Created (Newest)", value: "-created_at"}, {
    label: "Created (Oldest)",
    value: "created_at"
}, {label: "Name (A-Z)", value: "name"}, {label: "Name (Z-A)", value: "-name"},];

export default function OrdersEditorPage() {

    const navigate = useNavigate();

    // paging + sort + search state
    const [offset, setOffset] = useState(0);
    const [limit] = useState(10);
    const [ordering, setOrdering] = useState<string | undefined>(undefined);
    const [search, setSearch] = useState("");

  // Debounce the search term
  const debouncedSearch = useDebounce(search, 1000);

    const {data, isLoading, error} = useRetrieveOrders({
        queries: {
            offset: offset, ordering: ordering, archived: false, search:debouncedSearch
        }
    })

    if (isLoading) return <Skeleton className="h-32 w-full"/>;
    if (error) {
        console.error(error);
        return <p className="text-red-500">Error loading orders</p>;
    }

    const orders = data?.results ?? [];
    const total = data?.count ?? 0;
    const page = Math.floor(offset / limit) + 1;
    const pageCount = Math.ceil(total / limit);

    return (<div className="space-y-4">
            <div className="items-center space-x-2">
                <h2 className="text-xl font-semibold">Manage Orders</h2>
                <div className="flex justify-between my-4 gap-4">
                    <div className="flex-1">
                        <Input
                            placeholder="Search orders…"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>


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

                    <div>
                        {/* … your list UI … */}
                        <Button onClick={() => navigate({to:ordersCreateFormRoute.id})}>
                            New Order
                        </Button>
                    </div>
                </div>
            </div>
        <Table>
            <TableCaption>Orders List</TableCaption>
            <TableHeader>
                <TableRow>
                <TableHead>Name</TableHead>
                        <TableHead>Est. Completion</TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {orders.map((order) => (<TableRow key={order.id}>
                            <TableCell>{order.name}</TableCell>
                            <TableCell>{order.estimated_completion}</TableCell>
                            <TableCell>{order.company_name}</TableCell>
                            <TableCell>
                                {order.customer_first_name} {order.customer_last_name}
                            </TableCell>
                            <TableCell>
                                <EditOrderActionsCell orderId={order.id}/>
                            </TableCell>
                        </TableRow>))}
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
          Page {page} of {pageCount}
                </span>
                <Button
                    variant="secondary"
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                >
                    Next
                </Button>
            </div>
        </div>);
}
