import * as React from "react"
import { useMemo } from "react"
import {
    Bot,
    CheckSquare,
    ClipboardList,
    ClipboardCheck,
    Database,
    Factory,
    FileSignature,
    Files,
    Flame,
    Gauge,
    GraduationCap,
    History,
    LineChart,
    MapPin,
    PackageSearch,
    Settings,
    ShieldCheck,
    Workflow,
} from "lucide-react"

import { NavPages, NavPagesCollapsible, type Page } from "@/components/nav-pages"
import { NavUser } from "@/components/nav-user"
import { AppSidebarHeader } from "@/components/app-sidebar-header"
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarRail,
} from "@/components/ui/sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAuthUser } from "@/hooks/useAuthUser"
import { LoginLink } from "@/components/login-link-sidebar"
import { useMyCapaTasks } from "@/hooks/useMyCapaTasks"
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals"
import { usePermissionSet } from "@/hooks/useMyPermissions"

// Portal - Customer-facing (available to all users, no header)
const portalPages: Page[] = [
    { name: "Tracker", url: "/tracker", icon: MapPin },
]

// Production - MES / shop floor (staff only, collapsible)
const productionPages = [
    { name: "Work Orders", url: "/production/work-orders", icon: Factory },
    { name: "Processes", url: "/editor/processes", icon: Workflow },
    { name: "Dispositions", url: "/production/dispositions", icon: PackageSearch },
]

// Quality - QMS (staff only, collapsible)
const qualityPages = [
    { name: "Dashboard", url: "/quality", icon: ShieldCheck },
    { name: "CAPAs", url: "/quality/capas", icon: ClipboardList },
    { name: "Quality Reports", url: "/editor/qualityReports", icon: ClipboardCheck },
    { name: "Training", url: "/quality/training", icon: GraduationCap },
    { name: "Calibrations", url: "/quality/calibrations", icon: Gauge },
    { name: "Heat Map", url: "/heatmap", icon: Flame },
]

// Tools - standalone links (no section header)
const toolsPages = [
    { name: "Documents", url: "/documents", icon: Files },
    { name: "Analytics", url: "/analysis", icon: LineChart },
    { name: "AI Chat", url: "/ai-chat", icon: Bot },
]

// Admin - Configuration/CRUD (staff only, collapsible)
const adminPages = [
    { name: "Settings", url: "/settings", icon: Settings },
    { name: "Data Management", url: "/Edit", icon: Database },
    { name: "Audit Log", url: "/admin/audit-log", icon: History },
]

export function AppSidebar({
    ...props
}: React.ComponentProps<typeof Sidebar>) {
    const { data: user } = useAuthUser()
    const { data: myTasks } = useMyCapaTasks()
    const { data: myApprovals } = useMyPendingApprovals()
    const { hasAny, isLoading: permissionsLoading } = usePermissionSet()

    const isAuthenticated = !!user

    // Permission-based visibility
    // Platform staff (your SaaS employees) bypass permission checks for support access
    const isPlatformStaff = user?.is_staff ?? false

    // Show sections based on effective permissions
    const showPersonal = isPlatformStaff || hasAny('respond_to_approval', 'view_approvalrequest')
    const showProduction = isPlatformStaff || hasAny('view_workorder', 'view_orders', 'view_processes')
    const showQuality = isPlatformStaff || hasAny('view_qualityreports', 'view_capa', 'view_trainingrecord')
    const showApprovals = isPlatformStaff || hasAny('view_approvalrequest', 'respond_to_approval')
    const showTools = isPlatformStaff || hasAny('view_documents', 'view_chatsession')
    const showAdmin = isPlatformStaff || hasAny('change_tenantgroup', 'add_user', 'change_user')

    // Calculate inbox badge count (pending tasks + pending approvals)
    const inboxCount = useMemo(() => {
        const taskCount = myTasks?.filter(t => t.status !== "COMPLETED").length ?? 0
        const approvalCount = myApprovals?.length ?? 0
        return taskCount + approvalCount
    }, [myTasks, myApprovals])

    // Build personal pages with dynamic badge
    const personalPagesWithBadge: Page[] = useMemo(() => [
        { name: "Inbox", url: "/inbox", icon: CheckSquare, badge: inboxCount || undefined },
    ], [inboxCount])

    // Build approvals pages with dynamic badge
    const approvalCount = myApprovals?.length ?? 0
    const approvalsPagesWithBadge: Page[] = useMemo(() => [
        { name: "Overview", url: "/approvals", icon: FileSignature, badge: approvalCount || undefined },
        { name: "History", url: "/approvals/history", icon: History },
    ], [approvalCount])

    // Don't render permission-gated sections while loading permissions
    const showPermissionGatedSections = isAuthenticated && !permissionsLoading

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader>
                <AppSidebarHeader />
            </SidebarHeader>
            <SidebarContent>
                <ScrollArea className="h-full">
                    {/* Portal - available to all authenticated users */}
                    {isAuthenticated && <NavPages pages={portalPages} />}

                    {showPermissionGatedSections && (
                        <>
                            {/* Personal - users who can respond to approvals */}
                            {showPersonal && (
                                <NavPages title="Personal" pages={personalPagesWithBadge} />
                            )}

                            {/* Production - users with production view permissions */}
                            {showProduction && (
                                <NavPagesCollapsible
                                    title="Production"
                                    pages={productionPages}
                                    defaultOpen={true}
                                />
                            )}

                            {/* Quality - users with quality view permissions */}
                            {showQuality && (
                                <NavPagesCollapsible
                                    title="Quality"
                                    pages={qualityPages}
                                    defaultOpen={true}
                                />
                            )}

                            {/* Approvals - users who can view/respond to approvals */}
                            {showApprovals && (
                                <NavPagesCollapsible
                                    title="Approvals"
                                    pages={approvalsPagesWithBadge}
                                    defaultOpen={false}
                                />
                            )}

                            {/* Tools - users with document/chat access */}
                            {showTools && (
                                <NavPages pages={toolsPages} />
                            )}

                            {/* Admin - tenant admins only */}
                            {showAdmin && (
                                <NavPagesCollapsible
                                    title="Admin"
                                    pages={adminPages}
                                    defaultOpen={false}
                                />
                            )}
                        </>
                    )}
                </ScrollArea>
            </SidebarContent>
            <SidebarFooter>
                {user ? <NavUser user={user} /> : <LoginLink />}
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>
    )
}