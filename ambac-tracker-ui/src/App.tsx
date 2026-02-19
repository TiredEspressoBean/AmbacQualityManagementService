// src/App.tsx
import {RouterProvider} from "@tanstack/react-router";
import {createAppRouter} from "@/router";
import {ThemeProvider} from "@/components/theme-provider";
import {TenantProvider} from "@/components/tenant-provider";
import {Toaster} from "@/components/ui/sonner";
import {QueryClientProvider} from "@tanstack/react-query";
import {useEffect, useRef} from "react";
import { queryClient } from '@/lib/queryClient'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { api } from "@/lib/api/generated";
import { toast } from "sonner";

// Create router with queryClient for data prefetching
const router = createAppRouter(queryClient);

export default function App() {
    const interceptorSetup = useRef(false);

    useEffect(() => {
        // Fetch CSRF token on app load using the api client's axios instance
        api.axios.get("/api/csrf/", {
            withCredentials: true,
        });

        // Set up 403 response interceptor (only once)
        if (!interceptorSetup.current) {
            interceptorSetup.current = true;

            api.axios.interceptors.response.use(
                (response) => response,
                (error) => {
                    const status = error.response?.status;
                    const errorDetail = error.response?.data?.detail || "";

                    // Handle 401 Unauthorized - session expired or not logged in
                    if (status === 401) {
                        // Clear any cached user data
                        queryClient.clear();

                        // Only redirect if not already on login/signup pages
                        const publicPaths = ['/login', '/signup', '/password-reset-request', '/reset-password'];
                        const isPublicPath = publicPaths.some(p => window.location.pathname.startsWith(p));

                        if (!isPublicPath) {
                            toast.error("Session Expired", {
                                description: "Please log in again.",
                            });
                            router.navigate({ to: '/login' });
                        }
                    }

                    // Handle 403 Forbidden - permission denied
                    if (status === 403) {
                        // Check if it's a tenant access error
                        if (error.response?.data?.code === 'tenant_access_denied') {
                            toast.error("Tenant Access Denied", {
                                description: errorDetail || "You don't have access to this tenant.",
                            });
                        } else {
                            // Generic permission error
                            toast.error("Permission Denied", {
                                description: errorDetail || "You don't have permission to perform this action.",
                            });
                        }

                        // Redirect to forbidden page (unless already there)
                        if (window.location.pathname !== '/forbidden') {
                            router.navigate({ to: '/forbidden' });
                        }
                    }

                    // Re-throw the error so individual handlers can still catch it
                    return Promise.reject(error);
                }
            );
        }
    }, []);

    return (
        <QueryClientProvider client={queryClient}>
            <ReactQueryDevtools initialIsOpen={false} />
            <ThemeProvider>
                <TenantProvider>
                    <RouterProvider router={router}/>
                    <Toaster/>
                </TenantProvider>
            </ThemeProvider>
        </QueryClientProvider>);
}
