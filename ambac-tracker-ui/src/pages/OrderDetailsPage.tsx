import { useEffect, useRef } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { CheckCircle, Clock, Circle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import ProgressLabel from "@/components/ProgressLabel.tsx";
import { Link, useParams } from "@tanstack/react-router";
import { useOrderDetails } from "@/hooks/useOrderDetails.ts";
import { api } from '@/lib/api/generated'
import {Card, CardContent} from "@/components/ui/card.tsx";

function getStatusIcon(stage: any) {
    if (stage.is_completed) return <CheckCircle className="text-green-600 w-5 h-5 mt-1" />;
    if (stage.is_current) return <Clock className="text-yellow-500 animate-pulse w-5 h-5 mt-1" />;
    return <Circle className="text-gray-300 w-5 h-5 mt-1" />;
}

export function OrderDetailsPage() {
    const { orderNumber } = useParams({ from: "/orders/$orderNumber" });
    const loadRef = useRef<HTMLDivElement>(null);

    const { data, isLoading, error } = useOrderDetails(orderNumber);

    const {
        data: partsData,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
    } = useInfiniteQuery({
        queryKey: ["order-parts", orderNumber],
        initialPageParam: 0,
        queryFn: async ({ pageParam = 0 }) => {
            return await api.api_orders_parts_list({
                params: { order_id: Number(orderNumber) },
                queries: { offset: pageParam, limit: 25 },
            });
        },
        getNextPageParam: (lastPage, _pages) => {
            const { next, count, results } = lastPage;
            return next ? (results?.length ?? 0) + _pages.flat().length : undefined;
        },
    });

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
                fetchNextPage();
            }
        });
        if (loadRef.current) observer.observe(loadRef.current);
        return () => observer.disconnect();
    }, [loadRef, fetchNextPage, hasNextPage, isFetchingNextPage]);

    if (isLoading) return <p>Loading...</p>;
    if (error || !data) return <p className="text-red-500">Error loading order details.</p>;

    const { process_stages, customer_first_name, customer_last_name, estimated_completion } = data;
    const customerName = customer_first_name + " " + customer_last_name ?? "Unknown Customer";
    const currentStage = process_stages.find((s) => s.is_current)?.name || "";
    const completed = process_stages.filter((s) => s.is_completed).length;
    const progress = (completed / process_stages.length) * 100;

    return (
        <div className="max-w-3xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Order #{orderNumber}</h1>
            <p className="text-sm text-muted-foreground">Customer: {customerName}</p>
            <ProgressLabel currentStage={currentStage} progress={progress} />
            {estimated_completion && (
                <p className="text-sm text-muted-foreground mb-6">
                    {completed}/{process_stages.length} stages complete • Estimated delivery:{" "}
                    {formatDistanceToNow(new Date(estimated_completion), { addSuffix: true })}
                </p>
            )}
            {data.customer_note && (
            <Card className="mb-6 border-muted bg-muted/50">
                <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">Note:</span> {data.customer_note}
                    </p>
                </CardContent>
            </Card>
        )}

            <div className="space-y-4">
                {process_stages.map((stage, idx) => (
                    <div key={idx} className="flex items-start gap-3">
                        {getStatusIcon(stage)}
                        <div>
                            <p
                                className={cn(
                                    "text-sm font-medium",
                                    stage.is_current
                                        ? "text-yellow-800 dark:text-yellow-300"
                                        : stage.is_completed
                                            ? "text-green-700 dark:text-green-400"
                                            : "text-gray-700 dark:text-gray-300"
                                )}
                            >
                                {stage.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {stage.timestamp
                                    ? `Updated ${formatDistanceToNow(new Date(stage.timestamp), { addSuffix: true })}`
                                    : "Pending"}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-10 space-y-2">
                <h2 className="text-lg font-semibold mb-2">Parts</h2>
                <div className="grid grid-cols-1 gap-4">
                    {partsData?.pages.map((page) =>
                        page.results.map((part) => (
                            <Card key={part.id} className="p-4 text-sm w-full">
                                <Link
                                to={"/"}
                                >
                                <p className="font-medium">{part.part_type_name}</p>
                                <p className="text-muted-foreground text-xs">{part.step_description}</p>
                                <p className="text-muted-foreground text-xs">Status: {part.part_status}</p>
                                </Link>
                            </Card>
                        ))
                    )}
                </div>
                <div ref={loadRef} className="h-10 flex items-center justify-center">
                    {isFetchingNextPage && (
                        <span className="text-xs text-muted-foreground">Loading more parts...</span>
                    )}
                </div>
            </div>
        </div>
    );
}
