import {useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger} from "@/components/ui/sheet";
import {
    AlertDialog,
    AlertDialogTrigger,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogCancel,
    AlertDialogAction,
    AlertDialogFooter
} from "@/components/ui/alert-dialog";
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from "@/components/ui/table";
import {useReactTable, getCoreRowModel, flexRender, type ColumnDef} from "@tanstack/react-table";
import {useRetrieveParts} from "@/hooks/useRetrieveParts";
import {useRemovePartsMutation} from "@/hooks/useRemovePartsMutation";
import {useQueryClient} from "@tanstack/react-query";
import {toast} from "sonner";
import {AddPartsForm} from "@/components/AddPartsForm";
import {Checkbox} from "@/components/ui/checkbox";
import {ArrowUpDown, Pencil} from "lucide-react";
import {Input} from "@/components/ui/input";
import {useParams} from "@tanstack/react-router";
import {useDebounce} from "@/hooks/useDebounce.ts";
import {useAddPartsMutation} from "@/hooks/useAddPartsMutation.ts";

export default function EditOrdersPartsPage() {
    const { orderId } = useParams({ from: "/editOrdersParts/$orderId" });

    const queryClient = useQueryClient();
    const [selectedPartIds, setSelectedPartIds] = useState<string[]>([]);
    const [isSheetOpen, setIsSheetOpen] = useState(false);
    const [isConfirmOpen, setIsConfirmOpen] = useState(false);
    const [filters, setFilters] = useState({ERP_id: "", ordering: ""});
    const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({});
    const debouncedFilters = useDebounce(filters, 100);

    const addParts = useAddPartsMutation(orderId, {
        onSuccess: () => {
            toast.success("Parts added");
            queryClient.invalidateQueries({ queryKey: ["parts"] });
            setIsSheetOpen(false);
        },
        onError: (error: unknown) => {
            console.error("Add parts failed:", error);

            // Optional: show error to user
            toast.error(
                error instanceof Error ? error.message : "Failed to add parts"
            );
        },
    });


    const partsQuery = useRetrieveParts({
        order: orderId,
        ...debouncedFilters,
    });

    const removeParts = useRemovePartsMutation({orderId,
        invalidateQueryKeys:["parts"]}, {
        onSuccess: () => {
            toast.success("Parts removed");
            queryClient.invalidateQueries({ queryKey: ["parts", orderId] });
            setSelectedPartIds([]);
            setIsConfirmOpen(false);
        },
    });

    const table = useReactTable({
        data: partsQuery.data?.results ?? [],
        columns: [
            {
                id: "select",
                header: ({ table }) => (
                    <Checkbox
                        checked={table.getIsAllPageRowsSelected()}
                        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
                    />
                ),
                cell: ({ row }) => (
                    <Checkbox
                        checked={row.getIsSelected()}
                        onCheckedChange={(value) => row.toggleSelected(!!value)}
                    />
                ),
                enableSorting: false,
                enableHiding: false,
            },
            {
                accessorKey: "id",
                header: "ID",
            },
            {
                accessorKey: "ERP_id",
                header: "ERP ID",
            },
            {
                accessorKey: "status",
                header: ({ column }) => (
                    <Button variant="ghost" onClick={() => column.toggleSorting()}>
                        Status <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                ),
            },
            {
                accessorKey: "archived",
                header: "Archived",
                cell: ({ getValue }) => (getValue() ? "Yes" : "No"),
            },
            {
                accessorKey: "step_description",
                header: "Step",
            },
            {
                accessorKey: "part_type_name",
                header: "Part Type",
            },
            {
                accessorKey: "work_order_id",
                header: "Work Order",
            },
            {
                id: "actions",
                header: "Actions",
                cell: ({ row }) => (
                    // TODO: Edit part for go here? Perhaps as a sheet as well, or a dialog?
                    <Button variant="outline" size="sm" onClick={() => console.log("edit", row.original.id)}>
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                    </Button>
                ),
            },
        ] as ColumnDef<any>[],
        getCoreRowModel: getCoreRowModel(),
        state: {
            rowSelection,
        },
        onRowSelectionChange: setRowSelection,
        getRowId: (row) => row.id.toString(),
    });


    useEffect(() => {
        const ids = Object.keys(rowSelection)
            .filter((key) => rowSelection[key]);
        setSelectedPartIds(ids);
    }, [rowSelection]);

    return (<div className="p-4 space-y-4">
            <div className="flex justify-between items-center">
                <h1 className="text-xl font-bold">Edit Parts</h1>
                <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
                    <SheetTrigger asChild>
                        <Button>Add Parts</Button>
                    </SheetTrigger>
                    <SheetContent>
                        <SheetHeader>
                            <SheetTitle>Add Parts</SheetTitle>
                        </SheetHeader>
                        <AddPartsForm onSubmit={(data) => addParts.mutate(data)} />
                    </SheetContent>
                </Sheet>
            </div>

            <div className="flex items-center gap-4">
                <Input
                    placeholder="Search ERP ID..."
                    value={filters.ERP_id}
                    onChange={(e) => setFilters((f) => ({...f, ERP_id: e.target.value}))}
                    className="max-w-sm"
                />
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map(headerGroup => (<TableRow key={headerGroup.id}>
                                {headerGroup.headers.map(header => (<TableHead key={header.id}>
                                        {flexRender(header.column.columnDef.header, header.getContext())}
                                    </TableHead>))}
                            </TableRow>))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows.map(row => (<TableRow key={row.id}>
                                {row.getVisibleCells().map(cell => (<TableCell key={cell.id}>
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </TableCell>))}
                            </TableRow>))}
                    </TableBody>
                </Table>
            </div>

            {selectedPartIds.length > 0 && (
                <div className="bottom-4 left-4 bg-background border p-4 rounded shadow flex gap-4 items-center">
                    <span>{selectedPartIds.length} selected</span>
                    <AlertDialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
                        <AlertDialogTrigger asChild>
                            <Button variant="destructive">Remove Selected</Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                            <AlertDialogHeader>
                                <AlertDialogTitle>Confirm Deletion</AlertDialogTitle>
                                <AlertDialogDescription>
                                    You are about to permanently remove {selectedPartIds.length} parts.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => removeParts.mutate(selectedPartIds)}>
                                    Confirm
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </div>)}
        </div>);
}
