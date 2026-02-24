import { useState } from "react";
import { Building2, Check, ChevronsUpDown, Plus, Settings } from "lucide-react";
import { Link } from "@tanstack/react-router";

import { useTenantContext } from "@/components/tenant-provider";
import { useAuthUser } from "@/hooks/useAuthUser";
import { useUserTenants } from "@/hooks/useUserTenants";
import { useSwitchTenant } from "@/hooks/useSwitchTenant";
import { Badge } from "@/components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
    useSidebar,
} from "@/components/ui/sidebar";

export function AppSidebarHeader() {
    const { tenant, isSaas } = useTenantContext();
    const { data: user } = useAuthUser();
    const { data: tenants, isLoading: tenantsLoading } = useUserTenants();
    const switchTenant = useSwitchTenant();
    const { isMobile } = useSidebar();
    const [open, setOpen] = useState(false);

    const isStaff = user?.is_staff || user?.is_superuser;
    const hasMultipleTenants = tenants && tenants.length > 1;

    // Staff always sees dropdown, others only if multiple tenants in SaaS mode
    const showDropdown = isStaff || (isSaas && hasMultipleTenants);

    const handleTenantSwitch = (tenantId: string) => {
        if (tenantId === tenant?.id) return;
        switchTenant.mutate(tenantId);
        setOpen(false);
    };

    // Logo or fallback icon
    const logoContent = tenant?.logo_url ? (
        <img
            src={tenant.logo_url}
            alt={tenant.name}
            className="size-9 rounded-lg object-contain bg-white p-0.5"
        />
    ) : (
        <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-9 items-center justify-center rounded-lg">
            <Building2 className="size-4" />
        </div>
    );

    // Wrapper with visual distinction
    const headerWrapper = (children: React.ReactNode) => (
        <div className="border-b border-sidebar-border bg-sidebar-accent/30 px-2 py-3">
            <SidebarMenu>
                <SidebarMenuItem>{children}</SidebarMenuItem>
            </SidebarMenu>
        </div>
    );

    // Static header (no dropdown)
    if (!showDropdown) {
        return headerWrapper(
            <SidebarMenuButton
                size="lg"
                className="cursor-default hover:bg-transparent active:bg-transparent"
            >
                <div className="flex items-center gap-3 min-w-0">
                    {logoContent}
                    <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-sm truncate">
                            {tenant?.name || "My Company"}
                        </span>
                        {tenant?.status === "trial" && (
                            <Badge variant="secondary" className="w-fit text-[10px] px-1.5 py-0">
                                Trial
                            </Badge>
                        )}
                    </div>
                </div>
            </SidebarMenuButton>
        );
    }

    // Dropdown header
    return headerWrapper(
        <DropdownMenu open={open} onOpenChange={setOpen}>
            <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                    size="lg"
                    className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                        {logoContent}
                        <div className="flex flex-col min-w-0 flex-1">
                            <span className="font-semibold text-sm truncate">
                                {tenant?.name || "My Company"}
                            </span>
                            {tenant?.status === "trial" && (
                                <Badge variant="secondary" className="w-fit text-[10px] px-1.5 py-0">
                                    Trial
                                </Badge>
                            )}
                        </div>
                    </div>
                    <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-50" />
                </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
                side={isMobile ? "bottom" : "right"}
                align="start"
                sideOffset={4}
            >
                <DropdownMenuLabel className="text-xs text-muted-foreground">
                    Organizations
                </DropdownMenuLabel>
                {tenantsLoading ? (
                    <DropdownMenuItem disabled>
                        <span className="text-muted-foreground">Loading...</span>
                    </DropdownMenuItem>
                ) : tenants && tenants.length > 0 ? (
                    tenants.map((t) => (
                        <DropdownMenuItem
                            key={t.id}
                            onClick={() => handleTenantSwitch(t.id)}
                            className="gap-2 cursor-pointer"
                        >
                            {t.logo_url ? (
                                <img
                                    src={t.logo_url}
                                    alt={t.name}
                                    className="size-6 rounded object-contain bg-white"
                                />
                            ) : (
                                <div className="size-6 rounded bg-muted flex items-center justify-center">
                                    <Building2 className="size-3" />
                                </div>
                            )}
                            <span className="flex-1 truncate">{t.name}</span>
                            {t.is_current && (
                                <Check className="size-4 text-primary" />
                            )}
                        </DropdownMenuItem>
                    ))
                ) : (
                    <DropdownMenuItem disabled>
                        <span className="text-muted-foreground">No other organizations</span>
                    </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                    <Link
                        to="/settings"
                        className="gap-2 cursor-pointer"
                        onClick={() => setOpen(false)}
                    >
                        <div className="size-6 rounded bg-muted flex items-center justify-center">
                            <Settings className="size-3" />
                        </div>
                        <span>Organization settings</span>
                    </Link>
                </DropdownMenuItem>
                {isStaff && (
                    <DropdownMenuItem asChild>
                        <Link
                            to="/settings"
                            className="gap-2 cursor-pointer"
                            onClick={() => setOpen(false)}
                        >
                            <div className="size-6 rounded border border-dashed flex items-center justify-center">
                                <Plus className="size-3" />
                            </div>
                            <span className="text-muted-foreground">Add organization</span>
                        </Link>
                    </DropdownMenuItem>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
