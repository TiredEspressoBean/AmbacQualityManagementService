/** Production › Orders — the staff order book (services/mes/order_book). */
import { queryOptions, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type OrderBook = Awaited<ReturnType<typeof api.api_OrderBook_book_retrieve>>;
export type OrderBookRow = OrderBook["rows"][number];
export type OrderDetail = Awaited<ReturnType<typeof api.api_OrderBook_retrieve>>;
export type OrderBlocker = OrderBookRow["blockers"][number];

export const orderBookOptions = () =>
    queryOptions({
        queryKey: ["order-book"] as const,
        queryFn: () => api.api_OrderBook_book_retrieve(),
    });

export const orderBookDetailOptions = (orderId: string) =>
    queryOptions({
        queryKey: ["order-book", orderId] as const,
        queryFn: () => api.api_OrderBook_retrieve({ params: { id: orderId } }),
    });

export const useOrderBook = () => useQuery(orderBookOptions());
export const useOrderBookDetail = (orderId: string) =>
    useQuery({ ...orderBookDetailOptions(orderId), enabled: !!orderId });
