import { useNavigate } from "@tanstack/react-router"
import { useEffect } from "react"
import { useAuthQuery } from "@/hooks/useAuthQuery"

export function RequireStaff({ children }: { children: React.ReactNode }) {
    const { data: user, isLoading } = useAuthQuery()
    const navigate = useNavigate()

    useEffect(() => {
        if (!isLoading && !user?.is_staff) {
            navigate({ to: "/" }) // Or a 403 page
        }
    }, [isLoading, user, navigate])

    if (isLoading || !user) return null // or loading spinner
    return <>{children}</>
}
