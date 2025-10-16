"use client"

import {
    ChevronsUpDown,
    User,
} from "lucide-react"
import {
    Avatar, AvatarFallback,
} from "@/components/ui/avatar"
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar,
} from "@/components/ui/sidebar"
import {LogoutMenuItem} from '@/components/auth/Logout.tsx'
import { Link } from "@tanstack/react-router"


export function NavUser({
                            user,
                        }: {
    user: {
        first_name: string, last_name: string, email: string
        avatar: string
    }
}) {
    const {isMobile} = useSidebar()

    return (<SidebarMenu>
            <SidebarMenuItem>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <SidebarMenuButton
                            size="lg"
                            className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                        >
                            <Avatar className="h-8 w-8 rounded-lg">
                                <AvatarFallback className="rounded-lg">
                                    {user?.first_name?.[0]?.toUpperCase() ?? ""}
                                    {user?.last_name?.[0]?.toUpperCase() ?? ""}
                                </AvatarFallback>
                            </Avatar>

                            <div className="grid flex-1 text-left text-sm leading-tight">
                                  <span className="truncate font-medium">
                                    {user?.first_name || "John"} {user?.last_name || "Doe"}
                                  </span>
                                <span className="truncate text-xs">{user?.email || "no-email@example.com"}</span>
                            </div>
                            <ChevronsUpDown className="ml-auto size-4"/>
                        </SidebarMenuButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                        className="w-56"
                        side={isMobile ? "bottom" : "right"}
                        align="end"
                        sideOffset={8}
                    >
                        <DropdownMenuItem asChild>
                            <Link to="/profile" className="cursor-pointer">
                                <User className="mr-2 h-4 w-4" />
                                <span>Profile</span>
                            </Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <LogoutMenuItem/>
                    </DropdownMenuContent>
                </DropdownMenu>
            </SidebarMenuItem>
        </SidebarMenu>)
}
