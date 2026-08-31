// Hooks for purchased-material master data (Materials) — the BUY side of a BOM.
// PartTypes stay in-house SKUs; purchased components (O-rings, seals, coils) are Materials.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

type PaginatedMaterialList = components["schemas"]["PaginatedMaterialList"];

/** Paginated list for the Materials editor table (ModelEditorPage shape). */
export function useMaterialsList(params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) {
  const { offset, limit, ordering, search, filters } = params;
  return useQuery({
    queryKey: ["materials", { offset, limit, ordering, search, filters }],
    queryFn: () =>
      api.api_Materials_list({
        queries: { offset, limit, ordering, search, ...(filters ?? {}) },
      } as never) as Promise<PaginatedMaterialList>,
  });
}

/** All active materials (for pickers — BOM BUY lines, receiving lots). */
export function useMaterialOptions() {
  return useQuery({
    queryKey: ["materials", "options"],
    queryFn: () =>
      api.api_Materials_list({
        queries: { is_active: true, ordering: "name", limit: 1000 },
      } as never) as Promise<PaginatedMaterialList>,
  });
}

/** One material (for the edit form). */
export function useRetrieveMaterial(id?: string) {
  return useQuery({
    queryKey: ["material", id],
    enabled: !!id,
    queryFn: () => api.api_Materials_retrieve({ params: { id } } as never),
  });
}

/** Create a material. */
export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.api_Materials_create(body as never),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["materials"] }),
  });
}

/** Update a material. */
export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_Materials_partial_update(body as never, { params: { id } } as never),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["materials"] }),
  });
}

/** Remove a material. */
export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_Materials_destroy(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      toast.success("Material removed");
    },
    onError: () => toast.error("Couldn't remove material"),
  });
}
