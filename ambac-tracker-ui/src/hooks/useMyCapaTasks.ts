import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface TaskDocument {
    id: string;
    file_name: string;
    file_url?: string;
    upload_date?: string;
}

export interface CapaTask {
    id: string;
    task_number: string;
    capa: string;
    capa_info?: {
        id: string;
        capa_number: string;
        description?: string;
    };
    task_type: string;
    task_type_display: string;
    description: string;
    assigned_to?: string;
    assigned_to_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    completion_mode: string;
    completion_mode_display: string;
    due_date?: string;
    status: string;
    status_display: string;
    completed_by?: string;
    completed_by_info?: {
        id: string;
        username: string;
        full_name?: string;
    };
    completed_date?: string;
    completion_notes?: string;
    completion_signature?: string;
    is_overdue: boolean;
    requires_signature: boolean;
    documents_info?: {
        count: number;
        items: TaskDocument[];
    };
    created_at: string;
    updated_at: string;
}

// Response can be either an array or paginated result
type MyTasksResponse = CapaTask[] | { results: CapaTask[]; count: number };

export function useMyCapaTasks() {
    return useQuery({
        queryKey: ["capa-my-tasks"],
        queryFn: async () => {
            const response = await api.api_CapaTasks_my_tasks_list() as MyTasksResponse;
            // Normalize response: return array whether paginated or not
            return Array.isArray(response) ? response : response.results;
        },
    });
}
