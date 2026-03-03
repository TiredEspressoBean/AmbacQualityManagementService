
import { Outlet } from "@tanstack/react-router";

export default function RootLayout() {
    return (
        <div className="relative min-h-screen">
            <main className="relative z-10">
                <Outlet />
            </main>
        </div>
    );
}
