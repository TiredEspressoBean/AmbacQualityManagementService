// src/components/theme-provider.tsx
import {type ReactNode, useEffect } from "react";

export function ThemeProvider({ children }: { children: ReactNode }) {
    useEffect(() => {
        const stored = localStorage.getItem("vite-ui-theme");
        const systemPrefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;

        const resolvedTheme =
            stored === "dark" || (!stored && systemPrefersDark) ? "dark" : "light";

        document.documentElement.classList.remove("light", "dark");
        document.documentElement.classList.add(resolvedTheme);
    }, []);

    return <>{children}</>;
}
