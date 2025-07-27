// components/theme-toggle.tsx
"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const classList = document.documentElement.classList;
        setIsDark(classList.contains("dark"));
    }, []);

    const toggleTheme = () => {
        const classList = document.documentElement.classList;
        if (classList.contains("dark")) {
            classList.remove("dark");
            localStorage.setItem("theme", "light");
            setIsDark(false);
        } else {
            classList.add("dark");
            localStorage.setItem("theme", "dark");
            setIsDark(true);
        }
    };

    return (
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            <span className="sr-only">Toggle theme</span>
        </Button>
    );
}
