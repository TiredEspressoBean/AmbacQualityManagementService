import {
    type LucideIcon,
} from "lucide-react"

import {
    SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from "@/components/ui/sidebar"

export function NavPages({
                             title, pages,
                         }: {
    title?: string
    pages: {
        name: string
        url: string
        icon: LucideIcon
    }[]
}) {

    return (<SidebarGroup className="group-data-[collapsible=icon]:hidden">
        {title && <SidebarGroupLabel>{title}</SidebarGroupLabel>}
        <SidebarMenu>
            {pages.map((item) => (<SidebarMenuItem key={item.name}>
                <SidebarMenuButton asChild>
                    <a href={item.url}>
                        <item.icon/>
                        <span>{item.name}</span>
                    </a>
                </SidebarMenuButton>
            </SidebarMenuItem>))}
        </SidebarMenu>
    </SidebarGroup>)
}
