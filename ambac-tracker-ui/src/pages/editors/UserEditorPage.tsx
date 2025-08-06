import { useRetrieveUsers } from "@/hooks/useRetrieveUsers.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditUserActionsCell } from "@/components/edit-user-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useUsersList({
                          offset,
                          limit,
                          ordering,
                          search,
                      }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
}) {
    return useRetrieveUsers({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function UserEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Users"
            modelName="Users"
            useList={useUsersList}
            sortOptions={[
                { label: "Username (A-Z)", value: "username" },
                { label: "Username (Z-A)", value: "-username" },
                { label: "First Name (A-Z)", value: "first_name" },
                { label: "First Name (Z-A)", value: "-first_name" },
                { label: "Last Name (A-Z)", value: "last_name" },
                { label: "Last Name (Z-A)", value: "-last_name" },
                { label: "Email (A-Z)", value: "email" },
                { label: "Email (Z-A)", value: "-email" },
                { label: "Date Joined (Newest)", value: "-date_joined" },
                { label: "Date Joined (Oldest)", value: "date_joined" },
                { label: "Active Users First", value: "-is_active" },
                { label: "Inactive Users First", value: "is_active" },
                { label: "Staff Users First", value: "-is_staff" },
                { label: "Non-Staff Users First", value: "is_staff" },
            ]}
            columns={[
                { header: "Username", renderCell: (user: any) => user.username },
                { 
                    header: "Full Name", 
                    renderCell: (user: any) => {
                        const firstName = user.first_name || "";
                        const lastName = user.last_name || "";
                        const fullName = `${firstName} ${lastName}`.trim();
                        return fullName || "-";
                    }
                },
                { header: "Email", renderCell: (user: any) => user.email || "-" },
                { header: "Company", renderCell: (user: any) => user.parent_company?.name || "-" },
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
                    )
                },
                { 
                    header: "Joined", 
                    renderCell: (user: any) => {
                        if (user.date_joined) {
                            return new Date(user.date_joined).toLocaleDateString();
                        }
                        return "-";
                    }
                },
            ]}
            renderActions={(user) => <EditUserActionsCell userId={user.id} />}
            onCreate={() => navigate({ to: "/UserForm/create" })}
        />
    );
}