import { Outlet, useRouterState } from "@tanstack/react-router";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { TrialBanner } from "@/components/trial-banner";

export default function Layout() {
    const { location } = useRouterState();
    const isHome = location.pathname === "/";

    // Fullscreen routes - no sidebar/header (kiosk mode, print pages)
    const isFullscreen = location.pathname === "/big-screen" || location.pathname.endsWith("/print");

    // Render fullscreen pages without any chrome
    if (isFullscreen) {
        const isPrint = location.pathname.endsWith("/print");
        return (
            <div className={isPrint ? "bg-background" : "h-screen w-screen overflow-hidden bg-background"}>
                <Outlet />
            </div>
        );
    }

    return (
        <SidebarProvider>
            <div className={`flex flex-col w-full h-screen ${!isHome ? "bg-background" : ""}`}>
                {/* Trial banner - appears at very top */}
                <TrialBanner />

                <div className="flex flex-1 min-h-0">
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
                    <div className="flex flex-1 flex-col w-0 relative">
                        {/* Floating controls */}
                        <div className="absolute top-3 left-3 z-10">
                            <SidebarTrigger className="h-8 w-8 bg-background/80 backdrop-blur-sm border shadow-sm hover:bg-accent" />
                        </div>
                        <div className="absolute top-3 right-6 z-10">
                            <ThemeToggle />
                        </div>

                        <main className="flex-1 overflow-auto p-6 pt-14">
                            <div className="container mx-auto justify-center h-full">
                                <Outlet />
                            </div>
                        </main>
                    </div>
                </div>
            </div>
        </SidebarProvider>
    );
}
