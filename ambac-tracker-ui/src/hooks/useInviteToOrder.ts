import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export function useInviteToOrder() {
    return useMutation({
        mutationFn: ({ orderId, email }: { orderId: string; email: string }) =>
            api.api_TrackerOrders_invite_create(
                { id: orderId },
                { email },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } }
            ),
        mutationKey: ["order", "invite"],
    });
}
