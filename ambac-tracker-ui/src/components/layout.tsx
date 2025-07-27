import { Outlet, useRouterState } from "@tanstack/react-router";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import {ThemeToggle} from "@/components/theme-toggle.tsx";

export default function Layout() {
    const { location } = useRouterState();
    const isHome = location.pathname === "/";

    return (
        <SidebarProvider>
            <div className={`flex w-full h-screen ${!isHome ? "bg-background" : ""}`}>

                {isHome && (
                    <div
                        className="pointer-events-none absolute inset-0 -z-10 opacity-5 grayscale"
                        style={{
                            backgroundImage: `url('https://transform.octanecdn.com/fit/1200x600/https://octanecdn.com/ambacinternationalcom/ambacinternationalcom_153271557.jpg')`,
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                        }}
                    />
                )}

                <AppSidebar />

                {/* Main Content */}
                <div className="flex flex-1 flex-col w-0">
                    <header className="h-16 border-b border-border px-6 flex items-center justify-between">
                        <SidebarTrigger />
                        <ThemeToggle/>
                    </header>

                    <main className="flex-1 overflow-auto p-6">
                        <div className="container mx-auto justify-center">
                            <Outlet />
                        </div>
                    </main>
                </div>
            </div>
        </SidebarProvider>
    );
}
