import * as React from "react"
import { useMemo } from "react"
import {
    BookOpen,
    Bot,
    CalendarDays,
    CalendarRange,
    CheckSquare,
    ClipboardList,
    ClipboardCheck,
    Clock,
    Database,
    Factory,
    FileCheck,
    FileSignature,
    Files,
    Flame,
    Gauge,
    Grid3x3,
    GraduationCap,
    History,
    Home,
    LayoutDashboard,
    LineChart,
    MapPin,
    Package,
    PackageSearch,
    BadgeCheck,
    Recycle,
    Settings,
    ShieldCheck,
    Truck,
    Users,
    Wrench,
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

// Home - the landing page (available to all authenticated users, no header)
const homePages: Page[] = [
    { name: "Home", url: "/", icon: Home },
]

// Portal - Customer-facing (available to all users, no header)
const portalPages: Page[] = [
    { name: "Tracker", url: "/tracker", icon: MapPin },
]

// Production - MES / shop floor (staff only, collapsible)
const productionPages = [
    { name: "Work Orders", url: "/production/work-orders", icon: Factory },
    { name: "WO Control Center", url: "/workorders", icon: LayoutDashboard },
    { name: "Processes", url: "/editor/processes", icon: Workflow },
]

// Scheduling - APS planning surfaces (staff only, collapsible). The Gantt is the
// board; calendar drives working windows; capacity is the coarse long-range layer
// above it; labor hours + requirements are its reports.
const schedulingPages = [
    { name: "Schedule (Gantt)", url: "/production/schedule", icon: CalendarRange },
    { name: "Calendar", url: "/production/calendar", icon: CalendarDays },
    { name: "Capacity Planning", url: "/production/capacity", icon: Grid3x3 },
    { name: "Labor Hours", url: "/production/labor-hours", icon: Clock },
    { name: "Requirements", url: "/production/requirements", icon: ClipboardList },
]

// Supply - inbound material + suppliers (staff only, collapsible). "Materials"
// is the status-segmented hub that absorbs the old "Material Lots" + "Receiving
// Inspection" entries (lots are one lifecycle; the inspection queue is its
// "Awaiting inspection" lens).
const inventoryPages = [
    { name: "Incoming Inspection", url: "/production/incoming", icon: PackageSearch },
    { name: "Outside Processing", url: "/production/outside-processing", icon: Truck },
    { name: "Materials", url: "/production/material-lots", icon: Package },
    { name: "Receiving Inspection Plans", url: "/production/receiving-plans", icon: ClipboardCheck },
    { name: "Supplier Quality", url: "/production/supplier-quality", icon: ShieldCheck },
    { name: "Approved Suppliers", url: "/production/supplier-qualifications", icon: BadgeCheck },
    { name: "Part Approvals", url: "/production/part-approvals", icon: FileCheck },
]

// Reman - Remanufacturing operations (staff only, collapsible)
const remanPages = [
    { name: "Dashboard", url: "/reman", icon: Recycle },
    { name: "Cores", url: "/reman/cores", icon: Package },
    { name: "Components", url: "/reman/components", icon: Wrench },
]

// Quality - QMS (staff only, collapsible)
const qualityPages = [
    { name: "Dashboard", url: "/quality", icon: ShieldCheck },
    { name: "CAPAs", url: "/quality/capas", icon: ClipboardList },
    { name: "Quality Reports", url: "/editor/qualityReports", icon: ClipboardCheck },
    { name: "Change Control", url: "/quality/change-control", icon: FileSignature },
    { name: "Dispositions", url: "/production/dispositions", icon: PackageSearch },
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

// Admin - Configuration/CRUD (collapsible). Items are individually
// permission-gated in the component — e.g. Work Centers is shop-floor master
// data a Production Manager maintains (change_workcenter) without holding the
// user-management perms the rest of the section needs.

// Help - available to all authenticated users (at top of nav)
const helpPages: Page[] = [
    { name: "Help & Docs", url: "/docs/", icon: BookOpen, external: true },
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
    const showInventory = isPlatformStaff || hasAny('view_materiallot', 'view_receivinginspectionplan')
    const showReman = isPlatformStaff || hasAny('view_core', 'view_harvestedcomponent')
    const showQuality = isPlatformStaff || hasAny('view_qualityreports', 'view_capa', 'view_trainingrecord')
    const showApprovals = isPlatformStaff || hasAny('view_approvalrequest', 'respond_to_approval')
    const showTools = isPlatformStaff || hasAny('view_documents', 'view_chatsession')

    // Admin items gate individually: user/tenant admin needs the management
    // perms, but Work Centers is floor master data (a Production Manager holds
    // change_workcenter without add_user), and audit viewing is staff-wide.
    const isUserAdmin = isPlatformStaff || hasAny('change_tenantgroup', 'add_user', 'change_user')
    const adminPages = useMemo(() => [
        ...(isUserAdmin ? [
            { name: "Settings", url: "/settings", icon: Settings },
            { name: "User Management", url: "/admin/users", icon: Users },
        ] : []),
        ...(isPlatformStaff || hasAny('change_workcenter', 'add_workcenter')
            ? [{ name: "Work Centers", url: "/admin/work-centers", icon: Factory }] : []),
        ...(isUserAdmin ? [{ name: "Data Management", url: "/Edit", icon: Database }] : []),
        ...(isPlatformStaff || hasAny('view_auditlog', 'view_logentry')
            ? [{ name: "Audit Log", url: "/admin/audit-log", icon: History }] : []),
        // eslint-disable-next-line react-hooks/exhaustive-deps -- hasAny is stable per permission load
    ], [isUserAdmin, isPlatformStaff, permissionsLoading])
    const showAdmin = adminPages.length > 0

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
                    {/* Home - landing page, available to all authenticated users */}
                    {isAuthenticated && <NavPages pages={homePages} />}

                    {/* Help & Docs - available to all authenticated users */}
                    {isAuthenticated && <NavPages pages={helpPages} />}

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

                            {/* Scheduling - APS board + reports */}
                            {showProduction && (
                                <NavPagesCollapsible
                                    title="Scheduling"
                                    pages={schedulingPages}
                                    defaultOpen={false}
                                />
                            )}

                            {/* Supply - inbound material + suppliers */}
                            {showInventory && (
                                <NavPagesCollapsible
                                    title="Supply"
                                    pages={inventoryPages}
                                    defaultOpen={false}
                                />
                            )}

                            {/* Reman - users with reman view permissions */}
                            {showReman && (
                                <NavPagesCollapsible
                                    title="Remanufacturing"
                                    pages={remanPages}
                                    defaultOpen={false}
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