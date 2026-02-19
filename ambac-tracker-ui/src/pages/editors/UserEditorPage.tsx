import { useRetrieveUsers } from "@/hooks/useRetrieveUsers.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditUserActionsCell } from "@/components/edit-user-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useUsersList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchUsersEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["user", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_User_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Users", "User"],
        queryFn: () => api.api_User_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useUsersList({
                          offset,
                          limit,
                          ordering,
                          search,
                          filters,
                      }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveUsers({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function UserEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Users"
            modelName="Users"
            useList={useUsersList}
            columns={[
                { header: "Username", renderCell: (user: any) => user.username, priority: 1 },
                {
                    header: "Full Name",
                    renderCell: (user: any) => {
                        const firstName = user.first_name || "";
                        const lastName = user.last_name || "";
                        const fullName = `${firstName} ${lastName}`.trim();
                        return fullName || "-";
                    },
                    priority: 1
                },
                { header: "Email", renderCell: (user: any) => user.email || "-", priority: 1 },
                { header: "Company", renderCell: (user: any) => user.parent_company?.name || "-", priority: 5 },
                {
                    header: "Status",
                    renderCell: (user: any) => (
                        <div className="flex gap-2">
                            {user.is_active ? (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    Active
                                </span>
                            ) : (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    Inactive
                                </span>
                            )}
                            {user.is_staff && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    Staff
                                </span>
                            )}
                        </div>
                    ),
                    priority: 1
                },
                {
                    header: "Joined",
                    renderCell: (user: any) => {
                        if (user.date_joined) {
                            return new Date(user.date_joined).toLocaleDateString();
                        }
                        return "-";
                    },
                    priority: 4
                },
            ]}
            renderActions={(user) => <EditUserActionsCell userId={user.id} />}
            onCreate={() => navigate({ to: "/UserForm/create" })}
        />
    );
}