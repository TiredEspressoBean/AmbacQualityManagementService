// Hooks for authoring a part type's Bill of Materials inline on the Part Type form.
// Editing model (mirrors the backend): DRAFT BOMs edit in place; a RELEASED BOM is
// immutable — spin a new revision (a fresh DRAFT copy) to change it.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";

/** Pick the BOM to work on for a part type: an editable DRAFT if one exists, else the
 *  effective RELEASED, else the latest. (Same rule as the Part Type BOM panel.) */
function pickEffectiveBom(boms: any[]): any | undefined {
  if (!boms.length) return undefined;
  const byRevDesc = (a: any, b: any) =>
    (b.revision ?? "").localeCompare(a.revision ?? "", undefined, { numeric: true });
  const draft = boms.filter((b) => b.status === "DRAFT").sort(byRevDesc);
  if (draft.length) return draft[0];
  const released = boms.filter((b) => b.status === "RELEASED").sort(byRevDesc);
  if (released.length) return released[0];
  return [...boms].sort(byRevDesc)[0];
}

/** The effective BOM (with nested lines) for a part type — for allocating BOM lines to
 *  process steps from the flow editor. `isDraft` gates whether lines can be edited. */
export function useEffectiveBom(partTypeId?: string | null) {
  const list = useQuery({
    queryKey: ["BOMs", "list", { part_type: partTypeId }],
    enabled: !!partTypeId,
    queryFn: () =>
      api.api_BOMs_list({ queries: { part_type: partTypeId, limit: 100 } } as never) as Promise<any>,
  });
  const chosen = pickEffectiveBom((list.data as any)?.results ?? []);
  const detail = useQuery({
    queryKey: ["BOMs", "detail", chosen?.id],
    enabled: !!chosen?.id,
    queryFn: () => api.api_BOMs_retrieve({ params: { id: chosen.id } } as never) as Promise<any>,
  });
  return {
    bom: detail.data as any,
    chosen,
    isDraft: chosen?.status === "DRAFT",
    isLoading: list.isLoading || detail.isLoading,
  };
}

function useInvalidateBoms() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["BOMs"] });
}

/** Create a DRAFT ASSEMBLY BOM for a part type (when none exists yet). */
export function useCreateBom() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: (partTypeId: string) =>
      api.api_BOMs_create({
        part_type: partTypeId, bom_type: "ASSEMBLY", status: "DRAFT", revision: "A",
      } as never),
    onSuccess: () => { invalidate(); toast.success("Draft BOM created"); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't create BOM"),
  });
}

/** Release a DRAFT BOM for production use. */
export function useReleaseBom() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: (bomId: string) =>
      api.api_BOMs_release_create(undefined as never, { params: { id: bomId } } as never),
    onSuccess: () => { invalidate(); toast.success("BOM released"); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't release BOM"),
  });
}

/** Start a new DRAFT revision of a RELEASED/OBSOLETE BOM (copies its lines). */
export function useCreateBomRevision() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: (bomId: string) =>
      api.api_BOMs_revisions_create(
        { change_description: "Edited from Part Type form" } as never,
        { params: { id: bomId } } as never),
    onSuccess: () => { invalidate(); toast.success("New draft revision started"); },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't create revision"),
  });
}

/** Add a line to a DRAFT BOM. */
export function useCreateBomLine() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.api_BOMLines_create(body as never),
    onSuccess: () => { invalidate(); toast.success("Line added"); },
    onError: (e: any) => toast.error(bomLineError(e) ?? "Couldn't add line"),
  });
}

/** Edit a DRAFT BOM line. */
export function useUpdateBomLine() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_BOMLines_partial_update(body as never, { params: { id } } as never),
    onSuccess: () => { invalidate(); toast.success("Line updated"); },
    onError: (e: any) => toast.error(bomLineError(e) ?? "Couldn't update line"),
  });
}

/** Remove a line from a DRAFT BOM. */
export function useDeleteBomLine() {
  const invalidate = useInvalidateBoms();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_BOMLines_destroy(undefined as never, { params: { id } } as never),
    onSuccess: () => { invalidate(); toast.success("Line removed"); },
    onError: () => toast.error("Couldn't remove line"),
  });
}

/** Surface the "exactly one of component_type / material" validation message. */
function bomLineError(e: any): string | undefined {
  const d = e?.response?.data;
  if (!d) return undefined;
  if (typeof d.detail === "string") return d.detail;
  const firstArr = Object.values(d).find((v) => Array.isArray(v)) as string[] | undefined;
  return firstArr?.[0];
}
