import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { LogOut } from "lucide-react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { api } from "@/lib/api/generated"
import { getCookie } from "@/lib/utils"

export function LogoutMenuItem() {
    const queryClient = useQueryClient()
    const navigate = useNavigate()

    const logout = useMutation({
        mutationFn: () =>
            api.auth_logout_create(undefined, {
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                withCredentials: true,
            }),
        onSuccess: () => {
            queryClient.clear()
            navigate({ to: "/login" })
        },
        onError: (err) => {
            console.error("Logout failed:", err)
        },
    })

    return (
        <DropdownMenuItem onClick={() => logout.mutate()} disabled={logout.isPending}>
            <LogOut className="mr-2 h-4 w-4" />
            Log out
        </DropdownMenuItem>
    )
}
