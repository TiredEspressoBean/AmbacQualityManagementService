import { Building2 } from "lucide-react" // You can replace this with your actual logo/icon

import {
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar"

export function AppSidebarHeader() {
  return (
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
              size="lg"
              className="cursor-default bg-transparent text-left active:bg-transparent active:text-inherit focus:ring-0 focus:outline-none"
          >
            <div className="flex items-center gap-3">
              <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                <Building2 className="size-4" />
              </div>
              <div className="grid leading-tight">
                <span className="font-semibold text-sm truncate">Ambac International</span>
                <span className="text-xs text-muted-foreground truncate">New Product Development</span>
              </div>
            </div>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
  )
}
