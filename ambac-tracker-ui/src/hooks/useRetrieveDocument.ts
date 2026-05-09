import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type DocumentResponse = Schema<"Documents">;

export function useRetrieveDocument(id?: string) {
    return useQuery<DocumentResponse | null>({
        queryKey: ["document", id],
        queryFn: () => id ? api.api_Documents_retrieve({params: {id}}) as Promise<DocumentResponse> : Promise.resolve(null),
        enabled: !!id,
    });
}