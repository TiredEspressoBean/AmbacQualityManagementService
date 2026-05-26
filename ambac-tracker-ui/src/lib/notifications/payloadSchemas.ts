/**
 * Demo payload schemas for the Phase 3 rule-builder UI.
 *
 * Mirrors a subset of the dataclass fields declared in
 * `PartsTracker/Tracker/services/{mes,qms}/events.py`. The Tree field
 * picker walks these so the user can click `payload.severity` straight
 * into the CEL editor. The real implementation will generate this from
 * the backend's typed CEL environment introspection at Phase 3 time.
 */

export type CelType = 'string' | 'number' | 'boolean' | 'datetime' | 'uuid';

export interface PayloadField {
    name: string;
    type: CelType;
    description: string;
    /** Optional fixed value set — surfaces as a dropdown in the form builder. */
    enum?: readonly string[];
    /** Optional human label; defaults to humanized `name`. */
    label?: string;
}

const SEVERITY_VALUES = ['minor', 'major', 'critical'] as const;

export const PAYLOAD_SCHEMAS: Record<string, PayloadField[]> = {
    'ncr.opened': [
        { name: 'part_number', type: 'string', description: 'Part affected', label: 'Part number' },
        { name: 'work_order_number', type: 'string', description: 'Work order number', label: 'Work order' },
        { name: 'step_name', type: 'string', description: 'Step where NCR opened', label: 'Step' },
        { name: 'severity', type: 'string', description: 'NCR severity', enum: SEVERITY_VALUES, label: 'Severity' },
        { name: 'opened_by_id', type: 'number', description: 'User who opened the NCR', label: 'Opened by (user id)' },
        { name: 'opened_by_name', type: 'string', description: 'Display name', label: 'Opened by (name)' },
        { name: 'opened_at', type: 'datetime', description: 'Timestamp', label: 'Opened at' },
    ],
    'capa.opened': [
        { name: 'capa_number', type: 'string', description: 'CAPA identifier', label: 'CAPA number' },
        { name: 'severity', type: 'string', description: 'CAPA severity', enum: SEVERITY_VALUES, label: 'Severity' },
        { name: 'assigned_to_id', type: 'number', description: 'Assignee user', label: 'Assignee (user id)' },
        { name: 'assigned_to_name', type: 'string', description: 'Display name', label: 'Assignee (name)' },
        { name: 'due_date', type: 'datetime', description: 'Action due', label: 'Due date' },
    ],
    'capa.due_soon': [
        { name: 'capa_number', type: 'string', description: 'CAPA identifier' },
        { name: 'assigned_to_id', type: 'number', description: 'Assignee user' },
        { name: 'due_date', type: 'datetime', description: 'Action due' },
        { name: 'days_remaining', type: 'number', description: 'Days until due' },
    ],
    'order.late_risk': [
        { name: 'order_number', type: 'string', description: 'Order identifier' },
        { name: 'customer_id', type: 'number', description: 'Customer' },
        { name: 'customer_name', type: 'string', description: 'Customer display name' },
        { name: 'risk_score', type: 'number', description: '0–100' },
        { name: 'ship_date', type: 'datetime', description: 'Promised ship' },
    ],
    'inspection.failed': [
        { name: 'part_number', type: 'string', description: 'Part inspected' },
        { name: 'inspector_id', type: 'number', description: 'Inspector user' },
        { name: 'failure_code', type: 'string', description: 'Reason code' },
    ],
};

/**
 * Sample payloads used by the live-preview pane. Each event's payload
 * gets a deterministic value the user can mutate in-place to see how
 * different field values affect their CEL filter result.
 */
export const SAMPLE_PAYLOADS: Record<string, Record<string, unknown>> = {
    'ncr.opened': {
        part_number: 'P-12345',
        work_order_number: 'WO-2026-0007',
        step_name: 'Final Inspection',
        severity: 'major',
        opened_by_id: 42,
        opened_by_name: 'Jane Inspector',
        opened_at: '2026-05-05T14:30:00Z',
    },
    'capa.opened': {
        capa_number: 'CAPA-2026-014',
        severity: 'critical',
        assigned_to_id: 17,
        assigned_to_name: 'Sam Quality',
        due_date: '2026-06-01T00:00:00Z',
    },
    'capa.due_soon': {
        capa_number: 'CAPA-2026-014',
        assigned_to_id: 17,
        due_date: '2026-05-20T00:00:00Z',
        days_remaining: 3,
    },
    'order.late_risk': {
        order_number: 'ORD-9001',
        customer_id: 5,
        customer_name: 'Acme Aero',
        risk_score: 78,
        ship_date: '2026-05-30T00:00:00Z',
    },
    'inspection.failed': {
        part_number: 'P-77',
        inspector_id: 9,
        failure_code: 'DIM_OOT',
    },
};

export function getPayloadFields(eventCode: string): PayloadField[] {
    return PAYLOAD_SCHEMAS[eventCode] ?? [];
}

export function getSamplePayload(eventCode: string): Record<string, unknown> {
    return SAMPLE_PAYLOADS[eventCode] ?? {};
}
