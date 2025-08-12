import * as React from "react"
import {
    AudioWaveform,
    BookOpen,
    Bot,
    ClipboardCheck,
    Command,
    GalleryVerticalEnd,
    House,
    MapPin,
    Settings2,
    SquareTerminal,
    Files,
    type LucideIcon,
} from "lucide-react"

import { NavPages } from "@/components/nav-pages"
import { NavUser } from "@/components/nav-user"
import { AppSidebarHeader } from "@/components/app-sidebar-header"
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarRail,
} from "@/components/ui/sidebar"
import { useAuthUser } from "@/hooks/useAuthUser"
import {LoginLink} from '@/components/login-link-sidebar'

type Page = {
    name: string
    url: string
    icon: LucideIcon
}

type Section = {
    key: string
    title?: string
    pages: Page[]
}

type MockUser = {
    name: string
    email: string
    avatar: string
}

const data: {
    user: MockUser
    teams: { name: string; logo: LucideIcon; plan: string }[]
    navMain: {
        title: string
        url: string
        icon: LucideIcon
        isActive?: boolean
        items: { title: string; url: string }[]
    }[]
    user_sections: Section[]
    staff_sections: Section[]
} = {
    user: {
        name: "shadcn",
        email: "me@example.com",
        avatar: "/avatars/shadcn.jpg",
    },
    teams: [
        { name: "Acme Inc", logo: GalleryVerticalEnd, plan: "Enterprise" },
        { name: "Acme Corp.", logo: AudioWaveform, plan: "Startup" },
        { name: "Evil Corp.", logo: Command, plan: "Free" },
    ],
    navMain: [
        {
            title: "Playground",
            url: "#",
            icon: SquareTerminal,
            isActive: true,
            items: [
                { title: "History", url: "#" },
                { title: "Starred", url: "#" },
                { title: "Settings", url: "#" },
            ],
        },
        {
            title: "Models",
            url: "#",
            icon: Bot,
            items: [
                { title: "Genesis", url: "#" },
                { title: "Explorer", url: "#" },
                { title: "Quantum", url: "#" },
            ],
        },
        {
            title: "Documentation",
            url: "#",
            icon: BookOpen,
            items: [
                { title: "Introduction", url: "#" },
                { title: "Get Started", url: "#" },
                { title: "Tutorials", url: "#" },
                { title: "Changelog", url: "#" },
            ],
        },
        {
            title: "Settings",
            url: "#",
            icon: Settings2,
            items: [
                { title: "General", url: "#" },
                { title: "Team", url: "#" },
                { title: "Billing", url: "#" },
                { title: "Limits", url: "#" },
            ],
        },
    ],
    user_sections: [
        {
            key: "User Pages",
            pages: [
                { name: "Home", url: "/", icon: House },
                { name: "Tracker", url: "/tracker", icon: MapPin },
            ],
        },
    ],
    staff_sections: [
        {
            key: "Staff Pages",
            title: "Internal Tools",
            pages: [
                { name: "Quality Assurance", url: "/QA", icon: ClipboardCheck },
                { name: "Editing", url: "/Edit", icon: GalleryVerticalEnd },
                { name: "Documents", url: "/Documents", icon: Files }
            ],
        },
    ],
}

export function AppSidebar({
                               ...props
                           }: React.ComponentProps<typeof Sidebar>) {
    const { data: user } = useAuthUser()

    // Determine if user is staff
    const is_employee = user?.groups &&
        user.groups.length > 0 &&
        !user.groups.some((group: { name: string }) => group.name === 'Customers')

    console.log(user)

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader>
                <AppSidebarHeader />
            </SidebarHeader>
            <SidebarContent>
                {/* Always show user sections */}
                {data.user_sections.map((section) => (
                    <NavPages
                        key={section.key}
                        pages={section.pages}
                    />
                ))}

                {/* Only show staff sections if user is staff */}
                {is_employee && data.staff_sections.map((section) => (
                    <NavPages
                        key={section.key}
                        title={section.title ?? "Untitled"}
                        pages={section.pages}
                    />
                ))}
            </SidebarContent>
            <SidebarFooter>
                {user ? <NavUser user={user} /> : <LoginLink />}
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>
    )
}