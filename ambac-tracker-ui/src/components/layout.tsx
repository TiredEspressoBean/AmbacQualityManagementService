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
                    <AppSidebar />

                    {/* Main Content */}
                    <div className="flex flex-1 flex-col w-0">
                        {/* Top chrome bar — sibling of main, not absolute-positioned,
                            so pages can use `sticky top-0` without fighting padding. */}
                        <div className="flex items-center justify-between px-3 py-2 border-b bg-background/95 backdrop-blur-sm shrink-0">
                            <SidebarTrigger className="h-8 w-8 hover:bg-accent" />
                            <ThemeToggle />
                        </div>

                        {/* Main has no padding — pages own their own gutters via
                            their container divs. Keeping main padding-free is
                            what allows `sticky top-0` on a page's header to
                            pin flush to the chrome bar. */}
                        <main className="flex-1 overflow-auto min-h-0">
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
