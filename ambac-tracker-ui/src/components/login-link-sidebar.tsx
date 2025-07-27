import { Button } from "@/components/ui/button"
import { LogIn } from "lucide-react"
import { Link } from "@tanstack/react-router"

export function LoginLink() {
    return (
        <Button asChild variant="ghost" className="w-full justify-start">
            <Link to="/login" className="flex items-center gap-2">
                <LogIn className="h-4 w-4" />
                <span>Log in</span>
            </Link>
        </Button>
    )
}
