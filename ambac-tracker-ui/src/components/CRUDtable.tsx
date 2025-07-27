// src/components/CrudTable.tsx
import {
    flexRender,
    getCoreRowModel,
    getSortedRowModel,
    useReactTable,
    type ColumnDef,
} from "@tanstack/react-table";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";

interface CrudTableProps<T> {
    modelName: string;
    columns: ColumnDef<T, any>[];
    data: T[];
    isLoading?: boolean;
    onEdit?: (row: T) => void;
    onDelete?: (row: T) => void;
    onCreate?: () => void;
    emptyMessage?: string;
    hideActions?: boolean;
    rowKey?: (row: T) => string;
    toolbar?: React.ReactNode;
    renderActions?: (row: T) => React.ReactNode;
}

export function CrudTable<T>({
                                 modelName,
                                 columns,
                                 data,
                                 isLoading,
                                 onEdit,
                                 onDelete,
                                 onCreate,
                                 emptyMessage = `No ${modelName.toLowerCase()} found.`,
                                 hideActions = false,
                                 rowKey = (row) => (row as any).id ?? JSON.stringify(row),
                                 toolbar,
                                 renderActions,
                             }: CrudTableProps<T>) {
    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        state: {},
    });

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold">{modelName}</h2>
                {onCreate && (
                    <Button onClick={onCreate}>Create {modelName}</Button>
                )}
            </div>

            {toolbar && <div>{toolbar}</div>}

            <div className="border rounded-md">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {flexRender(
                                            header.column.columnDef.header,
                                            header.getContext()
                                        )}
                                    </TableHead>
                                ))}
                                {!hideActions && <TableHead>Actions</TableHead>}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow>
                                <TableCell colSpan={columns.length + 1}>Loading...</TableCell>
                            </TableRow>
                        ) : table.getRowModel().rows.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={rowKey(row.original)}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                    {!hideActions && (
                                        <TableCell>
                                            {renderActions ? (
                                                renderActions(row.original)
                                            ) : (
                                                <div className="flex gap-2">
                                                    {onEdit && (
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => onEdit(row.original)}
                                                        >
                                                            Edit
                                                        </Button>
                                                    )}
                                                    {onDelete && (
                                                        <Button
                                                            variant="destructive"
                                                            size="sm"
                                                            onClick={() => onDelete(row.original)}
                                                        >
                                                            Delete
                                                        </Button>
                                                    )}
                                                </div>
                                            )}
                                        </TableCell>
                                    )}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={columns.length + 1}>{emptyMessage}</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
