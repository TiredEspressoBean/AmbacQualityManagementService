import { useAuthUser } from "@/hooks/useAuthUser";
import Login from "@/components/auth/Login";

export default function Home() {
    const { data: user, isLoading } = useAuthUser();

    if (isLoading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    // Logged-out: show login
    if (!user) {
        return <Login />;
    }

    // Logged-in: simple welcome
    return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center px-4">
            <div className="text-center space-y-4">
                <h1 className="text-3xl font-semibold">
                    Welcome back{user.first_name ? `, ${user.first_name}` : ""}
                </h1>
                <p className="text-muted-foreground">
                    Use the sidebar to navigate to your workflow.
                </p>
            </div>
        </div>
    );
}
