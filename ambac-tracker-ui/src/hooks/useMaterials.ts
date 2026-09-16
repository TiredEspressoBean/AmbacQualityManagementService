// Hooks for purchased-material master data (Materials) — the BUY side of a BOM.
// PartTypes stay in-house SKUs; purchased components (O-rings, seals, coils) are Materials.
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

type PaginatedMaterialList = components["schemas"]["PaginatedMaterialList"];

/** Paginated list for the Materials editor table (ModelEditorPage shape). */
export const materialsListOptions = (params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) => {
  const { offset, limit, ordering, search, filters } = params;
  return queryOptions({
    queryKey: ["materials", { offset, limit, ordering, search, filters }] as const,
    queryFn: () =>
      api.api_Materials_list({
        queries: { offset, limit, ordering, search, ...(filters ?? {}) },
      }) as Promise<PaginatedMaterialList>,
  });
};

export function useMaterialsList(params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) {
  return useQuery(materialsListOptions(params));
}

/** All active materials (for pickers — BOM BUY lines, receiving lots). */
export const materialOptionsOptions = () =>
  queryOptions({
    queryKey: ["materials", "options"] as const,
    queryFn: () =>
      api.api_Materials_list({
        queries: { is_active: true, ordering: "name", limit: 1000 },
      }) as Promise<PaginatedMaterialList>,
  });

export function useMaterialOptions() {
  return useQuery(materialOptionsOptions());
}

/** One material (for the edit form). */
export const retrieveMaterialOptions = (id?: string) =>
  queryOptions({
    queryKey: ["material", id] as const,
    // `id!` rather than a cast: the hook below guards with `enabled: !!id`, so
    // the query never runs without one. The cast hid that the guard and the
    // type were out of step.
    queryFn: () => api.api_Materials_retrieve({ params: { id: id! } }),
  });

export function useRetrieveMaterial(id?: string) {
  return useQuery({ ...retrieveMaterialOptions(id), enabled: !!id });
}

/** Create a material. */
export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.api_Materials_create>[0]) =>
      api.api_Materials_create(body),
    onSuccess: () => qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "materials" || q.queryKey[0] === "material" }),
  });
}

/** Update a material. */
export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_Materials_partial_update(body, { params: { id } }),
    onSuccess: () => qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "materials" || q.queryKey[0] === "material" }),
  });
}

/** Remove a material. */
export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_Materials_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "materials" || q.queryKey[0] === "material" });
      toast.success("Material removed");
    },
    onError: () => toast.error("Couldn't remove material"),
  });
}
