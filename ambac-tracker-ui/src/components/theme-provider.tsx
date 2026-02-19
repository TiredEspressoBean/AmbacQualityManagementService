import { ThemeProvider as NextThemesProvider } from "next-themes"
import { type ReactNode } from "react"

type ThemeProviderProps = {
    children: ReactNode
    defaultTheme?: string
    storageKey?: string
}

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "vite-ui-theme",
    ...props
}: ThemeProviderProps) {
    return (
        <NextThemesProvider
            attribute="class"
            defaultTheme={defaultTheme}
            storageKey={storageKey}
            enableSystem
            disableTransitionOnChange
            {...props}
        >
            {children}
        </NextThemesProvider>
    )
}
