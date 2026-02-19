import { QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 60 * 1000,       // Data considered fresh for 1 minute
            gcTime: 5 * 60 * 1000,      // Cache garbage collected after 5 minutes
            refetchOnWindowFocus: false, // Don't refetch when window regains focus
            retry: 1,                    // Only retry failed requests once
            networkMode: 'offlineFirst', // Use cached data when offline, fetch in background when online
            refetchOnReconnect: true,    // Auto-refresh stale queries when connection returns
        },
        mutations: {
            onError: (error) => {
                toast.error("Operation failed", {
                    description: error instanceof Error ? error.message : "An unexpected error occurred",
                });
            },
        },
    },
})