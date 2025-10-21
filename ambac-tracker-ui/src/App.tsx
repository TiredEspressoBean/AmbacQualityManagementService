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
import { api } from "@/lib/api/generated";

export default function App() {
    useEffect(() => {
        // Fetch CSRF token on app load using the api client's axios instance
        api.axios.get("/api/csrf/", {
            withCredentials: true,
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
