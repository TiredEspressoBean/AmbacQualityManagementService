import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Receiving Inspection Plans (RIPs) — standalone, process-free RECEIVING steps for
 * purchased material. In-process RECEIVING steps (OSP returns, in-workflow receiving)
 * belong to their process and are NOT listed here. The paginated list is fetched in
 * the page via ModelEditorPage (Steps/receiving_plans); this hook owns the create.
 */
export const useCreateReceivingPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { part_type: string; name?: string }) =>
      api.api_Steps_create_receiving_plan_create(vars as never, {
        headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["receiving-plans"] }),
  });
};
