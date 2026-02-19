import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { ChevronDown, type LucideIcon } from "lucide-react"

import {
    SidebarGroup,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuBadge,
} from "@/components/ui/sidebar"
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

export type Page = {
    name: string
    url: string
    icon: LucideIcon
    badge?: number | string
}

// Simple flat list of nav items (no header)
export function NavPages({
    title,
    pages,
}: {
    title?: string
    pages: Page[]
}) {
    return (
        <SidebarGroup>
            {title && <SidebarGroupLabel>{title}</SidebarGroupLabel>}
            <SidebarMenu>
                {pages.map((item) => (
                    <SidebarMenuItem key={item.name}>
                        <SidebarMenuButton asChild>
                            <Link to={item.url}>
                                <item.icon />
                                <span>{item.name}</span>
                            </Link>
                        </SidebarMenuButton>
                        {item.badge !== undefined && item.badge !== 0 && (
                            <SidebarMenuBadge>{item.badge}</SidebarMenuBadge>
                        )}
                    </SidebarMenuItem>
                ))}
            </SidebarMenu>
        </SidebarGroup>
    )
}

// Collapsible section with header
export function NavPagesCollapsible({
    title,
    pages,
    defaultOpen = true,
}: {
    title: string
    pages: Page[]
    defaultOpen?: boolean
}) {
    const [isOpen, setIsOpen] = useState(defaultOpen)

    return (
        <SidebarGroup>
            <Collapsible open={isOpen} onOpenChange={setIsOpen}>
                <CollapsibleTrigger asChild>
                    <SidebarGroupLabel className="cursor-pointer hover:bg-sidebar-accent rounded-md transition-colors flex items-center justify-between pr-2">
                        <span>{title}</span>
                        <ChevronDown
                            className={cn(
                                "h-4 w-4 transition-transform duration-200",
                                isOpen && "rotate-180"
                            )}
                        />
                    </SidebarGroupLabel>
                </CollapsibleTrigger>
                <CollapsibleContent>
                    <SidebarMenu>
                        {pages.map((item) => (
                            <SidebarMenuItem key={item.name}>
                                <SidebarMenuButton asChild>
                                    <Link to={item.url}>
                                        <item.icon />
                                        <span>{item.name}</span>
                                    </Link>
                                </SidebarMenuButton>
                                {item.badge !== undefined && item.badge !== 0 && (
                                    <SidebarMenuBadge>{item.badge}</SidebarMenuBadge>
                                )}
                            </SidebarMenuItem>
                        ))}
                    </SidebarMenu>
                </CollapsibleContent>
            </Collapsible>
        </SidebarGroup>
    )
}
