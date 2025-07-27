
import { Outlet, useRouterState } from "@tanstack/react-router";

export default function RootLayout() {
    const pathname = useRouterState({ select: (s) => s.location.pathname });

    const isHome = pathname === "/";

    return (
        <div className="relative min-h-screen">
            {isHome && (
                <div className="absolute inset-0 z-0">
                    <img
                        src="https://transform.octanecdn.com/fit/1200x600/https://octanecdn.com/ambacinternationalcom/ambacinternationalcom_153271557.jpg"
                        alt="Hal"
                        className="h-full w-full object-cover grayscale opacity-20 pointer-events-none"
                    />
                </div>
            )}
            <main className="relative z-10">
                <Outlet />
            </main>
        </div>
    );
}
