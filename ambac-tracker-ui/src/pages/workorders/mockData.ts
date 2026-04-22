// Mock data for WorkOrder control-center pages.
// Shapes mirror frontend types where possible so swap-in is trivial later.

export type MockStepType = "TASK" | "DECISION" | "REWORK" | "ESCALATION" | "TIMER" | "TERMINAL" | "START";
export type MockEdgeType = "default" | "rework" | "escalation" | "pass" | "fail";

export type MockStep = {
    id: string;
    order: number;
    name: string;
    requires_qa: boolean;
    node_type: MockStepType;
};

export type MockStepEdge = {
    from_step: string;
    to_step: string;
    edge_type: MockEdgeType;
};

export type MockPartStatus =
    | "PENDING"
    | "IN_PROGRESS"
    | "AWAITING_QA"
    | "READY_FOR_NEXT_STEP"
    | "COMPLETED"
    | "QUARANTINED"
    | "REWORK_NEEDED"
    | "REWORK_IN_PROGRESS"
    | "SCRAPPED";

export type MockStepVisit = {
    step_order: number;
    step_name: string;
    visit_number: number;
    started_at: string;
    ended_at: string | null;
    operator: string | null;
    equipment: string | null;
    quality_status: "PASS" | "FAIL" | null;
};

export type MockPart = {
    id: string;
    serial: string;
    step_id: string;
    status: MockPartStatus;
    updated_at: string;
    operator: string | null;
    rework_count: number;
    requires_sampling: boolean;
    traveler: MockStepVisit[];
};

export type MockWorkOrderStatus =
    | "PENDING"
    | "IN_PROGRESS"
    | "ON_HOLD"
    | "COMPLETED"
    | "CANCELLED"
    | "WAITING_FOR_OPERATOR";

export type MockSplitReason = "QUANTITY" | "OPERATION" | "REWORK";

export type MockWorkOrder = {
    id: string;
    erp_id: string;
    status: MockWorkOrderStatus;
    priority: 1 | 2 | 3 | 4;
    quantity: number;
    expected_completion: string;
    process_name: string;
    customer: string;
    part_type: string;
    is_batch: boolean;
    parent_workorder_id: string | null;
    split_reason: MockSplitReason | null;
    steps: MockStep[];
    edges: MockStepEdge[];
    parts: MockPart[];
};

// Normalized shape used by the control-center Exceptions view.
export type ExceptionSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ExceptionItem = {
    id: string;
    kind: "DOWNTIME" | "QUARANTINE" | "CAPA";
    title: string;
    description: string;
    severity: ExceptionSeverity;
    state: string;
    opened_at: string;
    closed_at: string | null;
    work_order_ids: string[];
    reported_by: string;
    source_ref: string;
};


const SEVERITY_RANK: Record<ExceptionSeverity, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
};
export function severityRank(s: ExceptionSeverity): number {
    return SEVERITY_RANK[s];
}
