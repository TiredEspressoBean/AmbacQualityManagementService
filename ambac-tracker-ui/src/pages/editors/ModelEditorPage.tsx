import { useState, useEffect } from "react";
import {
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/useDebounce";

export type SortOption = { label: string; value: string };

export interface ModelEditorProps<T> {
    title: string;
    useList: (params: {
        offset: number;
        limit: number;
        ordering?: string;
        search?: string;
    }) => {
        data?: { results: T[]; count: number };
        isLoading: boolean;
        error: unknown;
    };
    sortOptions: SortOption[];
    columns: Array<{
        header: string;
        renderCell: (item: T) => React.ReactNode;
    }>;
    renderActions?: (item: T) => React.ReactNode;
    onCreate?: () => void;

    /** ✅ Optional injected toolbar content, e.g. file upload form */
    extraToolbarContent?: React.ReactNode;
}

export function ModelEditorPage<T extends { id: number }>({
                                                              title,
                                                              useList,
                                                              sortOptions,
                                                              columns,
                                                              renderActions,
                                                              onCreate,
                                                              extraToolbarContent,
                                                          }: ModelEditorProps<T>) {
    const [offset, setOffset] = useState(0);
    const [limit] = useState(25);
    const [ordering, setOrdering] = useState<string>();
    const [search, setSearch] = useState("");
    const debouncedSearch = useDebounce(search, 500);

    const { data, isLoading, error } = useList({
        offset,
        limit,
        ordering,
        search: debouncedSearch,
    });

    useEffect(() => {
        setOffset(0);
    }, [debouncedSearch, ordering]);

    if (isLoading) return <Skeleton className="h-32 w-full" />;
    if (error) return <p className="text-red-500">Error loading {title}</p>;

    const items = Array.isArray(data?.results) ? data.results : [];
    const total = data?.count || 0;
    const page = Math.floor(offset / limit) + 1;
    const pageCount = Math.ceil(total / limit);

    return (
        <div className="space-y-4">
            {/* Title */}
            <h2 className="text-xl font-semibold">{title}</h2>

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-4">
                <Input
                    placeholder={`Search ${title.toLowerCase()}...`}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="flex-1 min-w-[200px]"
                />
                <Select onValueChange={setOrdering} value={ordering}>
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Sort by..." />
                    </SelectTrigger>
                    <SelectContent>
                        {sortOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {onCreate && <Button onClick={onCreate}>New {title}</Button>}

                {/* ✅ Optional extra content */}
                {extraToolbarContent && (
                    <div className="ml-auto flex-shrink-0">{extraToolbarContent}</div>
                )}
            </div>

            {/* Table */}
            <Table>
                <TableCaption>{title} List</TableCaption>
                <TableHeader>
                    <TableRow>
                        {columns.map((col, i) => (
                            <TableHead key={i}>{col.header}</TableHead>
                        ))}
                        {renderActions && <TableHead>Actions</TableHead>}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {items.map((item) => (
                        <TableRow key={item.id}>
                            {columns.map((col, j) => (
                                <TableCell key={j}>{col.renderCell(item)}</TableCell>
                            ))}
                            {renderActions && (
                                <TableCell className="text-right space-x-2">
                                    {renderActions(item)}
                                </TableCell>
                            )}
                        </TableRow>
                    ))}
                </TableBody>
            </Table>

            {/* Pagination */}
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
        </div>
    );
}
