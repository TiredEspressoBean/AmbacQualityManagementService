"use client";

import { useState } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { useDebounce } from "@/hooks/useDebounce";
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { QaPartActionsCell } from "@/components/qa-parts-actions-cell";
import { schemas } from "@/lib/api/generated";
import { z } from "zod";

type WorkOrder = z.infer<typeof schemas.WorkOrder>;
type Part = z.infer<typeof schemas.Parts>;

const ITEMS_PER_PAGE = 20;

const sortOptions = [
    { label: "Due Date (Earliest)", value: "expected_completion" },
    { label: "Due Date (Latest)", value: "-expected_completion" },
    { label: "ERP ID (A-Z)", value: "ERP_id" },
    { label: "ERP ID (Z-A)", value: "-ERP_id" },
    { label: "Created (Newest)", value: "-created_at" },
    { label: "Created (Oldest)", value: "created_at" },
];

export default function QaWorkOrdersPage() {
    const [currentPage, setCurrentPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortBy, setSortBy] = useState("-expected_completion");
    const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    const debouncedSearch = useDebounce(searchTerm, 300);

    // Fetch work orders that have parts requiring QA
    const { data: workOrdersData, isLoading: isLoadingWorkOrders } = useRetrieveWorkOrders({
        queries: {
            offset: (currentPage - 1) * ITEMS_PER_PAGE,
            limit: ITEMS_PER_PAGE,
            search: debouncedSearch,
            ordering: sortBy,
            // Filter for work orders with parts needing QA
            // status__in: "IN_PROGRESS,PENDING_QA,READY_FOR_QA",
        },
    });

    // Fetch parts for the selected work order
    const { data: partsData, isLoading: isLoadingParts } = useRetrieveParts({
        queries: {
            work_order: selectedWorkOrder?.id,
            requires_sampling: true,
            part_status__in: "PENDING,IN_PROGRESS,REWORK_NEEDED,REWORK_IN_PROGRESS",
            limit: 100, // Get all parts for the work order
        },
    }, {
        enabled: !!selectedWorkOrder?.id,
    });

    const workOrders = workOrdersData?.results || [];
    const totalWorkOrders = workOrdersData?.count || 0;
    const totalPages = Math.ceil(totalWorkOrders / ITEMS_PER_PAGE);
    const parts = partsData?.results || [];

    const handleRowClick = (workOrder: WorkOrder) => {
        setSelectedWorkOrder(workOrder);
        setDrawerOpen(true);
    };

    const handleCloseDrawer = () => {
        setDrawerOpen(false);
        setSelectedWorkOrder(null);
    };

    const renderWorkOrdersTable = () => (
        <div className="space-y-4">
            <div className="flex gap-4 items-center">
                <Input
                    placeholder="Search work orders..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="max-w-sm"
                />
                <Select value={sortBy} onValueChange={setSortBy}>
                    <SelectTrigger className="w-64">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {sortOptions.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                                {option.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            <div className="border rounded-md">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Work Order</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Order</TableHead>
                            <TableHead>Company</TableHead>
                            <TableHead>Parts Needing QA</TableHead>
                            <TableHead>Quantity</TableHead>
                            <TableHead>Due Date</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoadingWorkOrders ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                </TableRow>
                            ))
                        ) : workOrders.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                                    No work orders requiring QA found
                                </TableCell>
                            </TableRow>
                        ) : (
                            workOrders.map((workOrder: WorkOrder) => (
                                <TableRow
                                    key={workOrder.id}
                                    className="cursor-pointer hover:bg-muted/50"
                                    onClick={() => handleRowClick(workOrder)}
                                >
                                    <TableCell className="font-medium">
                                        {workOrder.ERP_id}
                                    </TableCell>
                                    <TableCell>
                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                            workOrder.workorder_status === 'IN_PROGRESS' 
                                                ? 'bg-blue-100 text-blue-800' 
                                                : workOrder.workorder_status === 'READY_FOR_QA'
                                                ? 'bg-yellow-100 text-yellow-800'
                                                : 'bg-gray-100 text-gray-800'
                                        }`}>
                                            {workOrder.workorder_status?.replace('_', ' ') || 'Unknown'}
                                        </span>
                                    </TableCell>
                                    <TableCell>
                                        {(workOrder.related_order_detail as any)?.name || "-"}
                                    </TableCell>
                                    <TableCell>
                                        {(workOrder.related_order_detail as any)?.company_name || "-"}
                                    </TableCell>
                                    <TableCell>
                                        <span className="font-medium text-orange-600">
                                            {(workOrder as any).parts_summary?.requiring_qa || "Unknown"}
                                        </span>
                                        {(workOrder as any).parts_summary?.total && 
                                            ` / ${(workOrder as any).parts_summary.total}`
                                        }
                                    </TableCell>
                                    <TableCell>{workOrder.quantity}</TableCell>
                                    <TableCell>
                                        {workOrder.expected_completion
                                            ? new Date(workOrder.expected_completion).toLocaleDateString()
                                            : "-"
                                        }
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {totalPages > 1 && (
                <div className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                        Showing {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, totalWorkOrders)} to{" "}
                        {Math.min(currentPage * ITEMS_PER_PAGE, totalWorkOrders)} of {totalWorkOrders} work orders
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                            disabled={currentPage === 1}
                        >
                            Previous
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                            disabled={currentPage === totalPages}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );

    const renderPartsTable = () => (
        <div className="space-y-4">
            {isLoadingParts ? (
                <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex justify-between items-center p-4 border rounded">
                            <div className="space-y-2 flex-1">
                                <Skeleton className="h-4 w-32" />
                                <Skeleton className="h-3 w-48" />
                            </div>
                            <Skeleton className="h-8 w-20" />
                        </div>
                    ))}
                </div>
            ) : parts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                    No parts requiring QA found for this work order
                </div>
            ) : (
                <div className="space-y-2">
                    {parts.map((part: Part) => (
                        <div key={part.id} className="flex justify-between items-center p-4 border rounded hover:bg-muted/50">
                            <div className="space-y-1 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium">{part.ERP_id}</span>
                                    <span className={`px-2 py-1 text-xs rounded-full ${
                                        part.part_status === 'PENDING' 
                                            ? 'bg-yellow-100 text-yellow-800' 
                                            : part.part_status === 'IN_PROGRESS'
                                            ? 'bg-blue-100 text-blue-800'
                                            : part.part_status === 'REWORK_NEEDED'
                                            ? 'bg-red-100 text-red-800'
                                            : 'bg-gray-100 text-gray-800'
                                    }`}>
                                        {part.part_status.replace('_', ' ')}
                                    </span>
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    {(part as any).step_name || (part as any).step_description} • {(part as any).process_name} • {(part as any).part_type_name}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    Created: {new Date(part.created_at).toLocaleString()}
                                </div>
                            </div>
                            <div className="ml-4">
                                <QaPartActionsCell part={part} />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    const isBatchWorkOrder = selectedWorkOrder && parts.some(part => (part as any).is_batch_step);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Work Orders - Quality Assurance</h1>
                <p className="text-muted-foreground">
                    Click on a work order to review its parts requiring quality assurance
                </p>
            </div>

            {renderWorkOrdersTable()}

            <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
                <SheetContent side="right" className="w-full sm:w-3/4 lg:w-1/2">
                    <SheetHeader>
                        <SheetTitle>
                            {selectedWorkOrder?.ERP_id} - Quality Review
                            {isBatchWorkOrder && (
                                <span className="ml-2 text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                    Batch Process
                                </span>
                            )}
                        </SheetTitle>
                        {selectedWorkOrder && (
                            <div className="text-sm text-muted-foreground space-y-1">
                                <p><strong>Order:</strong> {(selectedWorkOrder.related_order_detail as any)?.name || "N/A"}</p>
                                <p><strong>Company:</strong> {(selectedWorkOrder.related_order_detail as any)?.company_name || "N/A"}</p>
                                <p><strong>Status:</strong> {selectedWorkOrder.workorder_status?.replace('_', ' ') || 'Unknown'}</p>
                                <p><strong>Quantity:</strong> {selectedWorkOrder.quantity}</p>
                                {selectedWorkOrder.notes && (
                                    <p><strong>Notes:</strong> {selectedWorkOrder.notes}</p>
                                )}
                            </div>
                        )}
                    </SheetHeader>

                    <div className="mt-6">
                        {isBatchWorkOrder ? (
                            <div className="space-y-4">
                                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                    <h3 className="font-medium text-blue-900 mb-2">Batch Processing Mode</h3>
                                    <p className="text-sm text-blue-700 mb-4">
                                        This work order contains parts from a batch step. You can either review individual parts 
                                        or perform bulk QA actions on the entire batch.
                                    </p>
                                    <div className="flex gap-2">
                                        <Button size="sm" className="bg-green-600 hover:bg-green-700">
                                            Pass Entire Batch
                                        </Button>
                                        <Button size="sm" variant="destructive">
                                            Report Batch Issues
                                        </Button>
                                    </div>
                                </div>
                                <div>
                                    <h4 className="font-medium mb-2">Individual Parts in Batch:</h4>
                                    {renderPartsTable()}
                                </div>
                            </div>
                        ) : (
                            <div>
                                <h4 className="font-medium mb-4">Parts Requiring QA ({parts.length})</h4>
                                {renderPartsTable()}
                            </div>
                        )}
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
}