import { useQuery, queryOptions } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type DocumentResponse = Schema<"Documents">;

export const retrieveDocumentOptions = (id?: string) => queryOptions({
    queryKey: ["document", id] as const,
    queryFn: () => id ? api.api_Documents_retrieve({params: {id}}) as Promise<DocumentResponse> : Promise.resolve(null),
});

export function useRetrieveDocument(id?: string) {
    return useQuery({
        ...retrieveDocumentOptions(id),
        enabled: !!id,
    });
}
