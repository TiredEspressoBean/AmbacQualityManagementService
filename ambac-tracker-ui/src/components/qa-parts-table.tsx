import {
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { useState } from "react";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { QaPartActionsCell } from "@/components/qa-parts-actions-cell.tsx";
import { z } from "zod";
import { schemas } from "@/lib/api/generated";
import {useDebounce} from "@/hooks/useDebounce.ts";

const SORT_OPTIONS = [
    { label: "Created (Newest)", value: "-created_at" },
    { label: "Created (Oldest)", value: "created_at" },
    { label: "ERP ID (A-Z)", value: "ERP_id" },
    { label: "ERP ID (Z-A)", value: "-ERP_id" },
    { label: "Status", value: "status" },
];

type PartStatus = z.infer<typeof schemas.PartsStatusEnum>;

function formatStatusLabel(status: string | null | undefined): string {
    if (!status) return "—";

    return status
        .toLowerCase()
        .split("_")
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export default function QaPartsTable() {
    const [offset, setOffset] = useState(0);
    const [limit] = useState(25);
    const [ordering, setOrdering] = useState<string | undefined>(undefined);
    const [filters, setFilters] = useState<{ ERP_id?: string; status?: PartStatus }>({});
    const STATUS_OPTIONS = schemas.PartsStatusEnum.options

    // Debounce the search term
    const debouncedSearch = useDebounce(filters, 300);

    const { data, isLoading, error } = useRetrieveParts({
        offset,
        limit,
        ordering,
        archived: false,
        requires_sampling: true,
        ...debouncedSearch,
    });

    if (isLoading) return <Skeleton className="h-32 w-full" />;
    if (error) {
        return <p className="text-red-500">Error loading parts</p>;
    }

    const parts = data?.results ?? [];
    const total = data?.count ?? 0;

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap justify-between items-center gap-2">
                <h2 className="text-xl font-semibold">Parts in Process</h2>
                <div className="flex flex-wrap gap-2 items-center">
                    <Select onValueChange={setOrdering} value={ordering}>
                        <SelectTrigger className="w-[220px]">
                            <SelectValue placeholder="Sort by..." />
                        </SelectTrigger>
                        <SelectContent>
                            {SORT_OPTIONS.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <Select
                        onValueChange={(value) =>
                            setFilters((prev) => ({ ...prev, status: value as PartStatus }))
                        }
                        value={filters.status}
                    >
                        <SelectTrigger className="w-[160px]">
                            <SelectValue placeholder="Filter by Status" />
                        </SelectTrigger>
                        <SelectContent>
                            {STATUS_OPTIONS.map((status) => (
                                <SelectItem key={status} value={status}>
                                    {formatStatusLabel(status)}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <Input
                        type="text"
                        placeholder="ERP ID"
                        className="w-[160px]"
                        value={filters.ERP_id ?? ""}
                        onChange={(e) =>
                            setFilters((prev) => ({ ...prev, ERP_id: e.target.value }))
                        }
                    />
                </div>
            </div>

            <Table>
                <TableCaption>
                    {parts.length === 0 ? "No parts found." : "Parts in Process"}
                </TableCaption>
                <TableHeader>
                    <TableRow>
                        <TableHead>ERP ID</TableHead>
                        <TableHead>Part Type</TableHead>
                        <TableHead>Current Step</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {parts.map((part) => (
                        <TableRow key={part.id}>
                            <TableCell>{part.ERP_id}</TableCell>
                            <TableCell>{part.part_type_name ?? "—"}</TableCell>
                            <TableCell>{part.step_description ?? "—"}</TableCell>
                            <TableCell>
                                {formatStatusLabel(part.part_status)}
                            </TableCell>
                            <QaPartActionsCell part={part} />
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
        </div>
    );
}