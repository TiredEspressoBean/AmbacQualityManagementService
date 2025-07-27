// src/App.tsx
import {RouterProvider} from "@tanstack/react-router";
import {router} from "@/router";
import {ThemeProvider} from "@/components/theme-provider";
import {Toaster} from "@/components/ui/sonner";
import {QueryClientProvider} from "@tanstack/react-query";
import {useEffect} from "react";
import { queryClient } from '@/lib/queryClient'
import React from "react";
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export default function App() {
    useEffect(() => {
        fetch("/api/csrf/", {
            credentials: "include",
        });
    }, []);

    return (
        <QueryClientProvider client={queryClient}>
            <ReactQueryDevtools initialIsOpen={false} />
            <ThemeProvider>
                <RouterProvider router={router}/>
                <Toaster/>
            </ThemeProvider>
        </QueryClientProvider>);
}
