import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";
import qs from "qs";

export type AcceptToInventoryResponse = {
  component: HarvestedComponent;
  part_id: string;
  part_erp_id: string;
};
export type HarvestedComponent = {
  id: string;
  core: string;
  core_number: string;
  component_type: string;
  component_type_name: string;
  /**
   * The Parts record created for this component (if accepted)
   */
  component_part: string | null;
  component_part_erp_id: string | null;
  disassembled_at: string;
  disassembled_by: number;
  disassembled_by_name: string;
  condition_grade: ConditionGradeEnum;
  condition_notes?: string | undefined;
  is_scrapped: boolean;
  scrap_reason: string;
  scrapped_at: string | null;
  scrapped_by: number | null;
  scrapped_by_name: string | null;
  position?: /**
   * Position within core (e.g., 'Cyl 1', 'Position A')
   *
   * @maxLength 50
   */
  string | undefined;
  original_part_number?: /**
   * Original part number if readable
   *
   * @maxLength 100
   */
  string | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type ConditionGradeEnum =
  /**
   * * `A` - Grade A - Excellent
   * `B` - Grade B - Good
   * `C` - Grade C - Fair
   * `SCRAP` - Scrap - Not Usable
   *
   * @enum A, B, C, SCRAP
   */
  "A" | "B" | "C" | "SCRAP";
export type AddNoteInputRequest = {
  /**
   * @minLength 1
   */
  message: string;
  visibility?: /**
   * @default "visible"
   */
  VisibilityEnum | undefined;
};
export type VisibilityEnum =
  /**
   * * `visible` - visible
   * `internal` - internal
   *
   * @enum visible, internal
   */
  "visible" | "internal";
export type ApprovalRequest = {
  id: string;
  approval_number: string;
  content_type?: (number | null) | undefined;
  object_id?:
    | /**
     * @maxLength 36
     */
    (string | null)
    | undefined;
  content_object_info: {};
  requested_by?: (number | null) | undefined;
  requested_by_info: {};
  reason?: (string | null) | undefined;
  notes?: (string | null) | undefined;
  status?: ApprovalStatusEnum | undefined;
  status_display: string;
  approval_type: ApprovalTypeEnum;
  approval_type_display: string;
  flow_type?: ApprovalFlowTypeEnum | undefined;
  flow_type_display: string;
  sequence_type?: ApprovalSequenceEnum | undefined;
  threshold?:
    | /**
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  delegation_policy?: DelegationPolicyEnum | undefined;
  escalation_day?:
    | /**
     * Specific date when escalation should trigger
     */
    (string | null)
    | undefined;
  escalate_to?: (number | null) | undefined;
  due_date?: (string | null) | undefined;
  approver_assignments_info: Array<unknown>;
  required_approvers_info: Array<unknown>;
  optional_approvers_info: Array<unknown>;
  approver_groups: Array<string>;
  approver_groups_info: Array<unknown>;
  responses: Array<ApprovalResponse>;
  pending_approvers: Array<unknown>;
  requested_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  archived: boolean;
};
export type ApprovalStatusEnum =
  /**
   * * `NOT_REQUIRED` - Not Required
   * `PENDING` - Pending
   * `APPROVED` - Approved
   * `REJECTED` - Rejected
   * `CANCELLED` - Cancelled
   *
   * @enum NOT_REQUIRED, PENDING, APPROVED, REJECTED, CANCELLED
   */
  "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
export type ApprovalTypeEnum =
  /**
   * * `DOCUMENT_RELEASE` - Document Release
   * `CAPA_CRITICAL` - CAPA Critical
   * `CAPA_MAJOR` - CAPA Major
   * `ECO` - Engineering Change Order
   * `TRAINING_CERT` - Training Certification
   * `PROCESS_APPROVAL` - Process Approval
   *
   * @enum DOCUMENT_RELEASE, CAPA_CRITICAL, CAPA_MAJOR, ECO, TRAINING_CERT, PROCESS_APPROVAL
   */
  | "DOCUMENT_RELEASE"
  | "CAPA_CRITICAL"
  | "CAPA_MAJOR"
  | "ECO"
  | "TRAINING_CERT"
  | "PROCESS_APPROVAL";
export type ApprovalFlowTypeEnum =
  /**
   * * `ALL_REQUIRED` - All Required
   * `THRESHOLD` - Threshold
   * `ANY` - Any
   *
   * @enum ALL_REQUIRED, THRESHOLD, ANY
   */
  "ALL_REQUIRED" | "THRESHOLD" | "ANY";
export type ApprovalSequenceEnum =
  /**
   * * `PARALLEL` - Parallel
   * `SEQUENTIAL` - Sequential
   *
   * @enum PARALLEL, SEQUENTIAL
   */
  "PARALLEL" | "SEQUENTIAL";
export type DelegationPolicyEnum =
  /**
   * * `OPTIONAL` - Optional
   * `DISABLED` - Disabled
   *
   * @enum OPTIONAL, DISABLED
   */
  "OPTIONAL" | "DISABLED";
export type ApprovalResponse = {
  id: string;
  approval_request: string;
  approver: number;
  approver_info: {};
  decision: DecisionEnum;
  decision_display: string;
  decision_date: string;
  comments?: (string | null) | undefined;
  signature_data?:
    | /**
     * Base64 encoded signature image (PNG)
     */
    (string | null)
    | undefined;
  signature_meaning?:
    | /**
     * e.g., 'I approve as QA Manager'
     *
     * @maxLength 200
     */
    (string | null)
    | undefined;
  /**
   * When identity verification succeeded
   */
  verified_at: string | null;
  verification_method?: VerificationMethodEnum | undefined;
  verification_method_display: string;
  delegated_to?: (number | null) | undefined;
  delegated_to_info: {};
  ip_address: string | null;
  /**
   * True if requester approved their own request
   */
  self_approved: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type DecisionEnum =
  /**
   * * `APPROVED` - Approved
   * `REJECTED` - Rejected
   * `DELEGATED` - Delegated
   *
   * @enum APPROVED, REJECTED, DELEGATED
   */
  "APPROVED" | "REJECTED" | "DELEGATED";
export type VerificationMethodEnum =
  /**
   * * `PASSWORD` - Password
   * `SSO` - SSO
   * `NONE` - None
   *
   * @enum PASSWORD, SSO, NONE
   */
  "PASSWORD" | "SSO" | "NONE";
export type ApprovalRequestRequest = {
  content_type?: (number | null) | undefined;
  object_id?:
    | /**
     * @maxLength 36
     */
    (string | null)
    | undefined;
  requested_by?: (number | null) | undefined;
  reason?: (string | null) | undefined;
  notes?: (string | null) | undefined;
  status?: ApprovalStatusEnum | undefined;
  approval_type: ApprovalTypeEnum;
  flow_type?: ApprovalFlowTypeEnum | undefined;
  sequence_type?: ApprovalSequenceEnum | undefined;
  threshold?:
    | /**
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  delegation_policy?: DelegationPolicyEnum | undefined;
  escalation_day?:
    | /**
     * Specific date when escalation should trigger
     */
    (string | null)
    | undefined;
  escalate_to?: (number | null) | undefined;
  due_date?: (string | null) | undefined;
};
export type ApprovalResponseRequest = {
  approval_request: string;
  approver: number;
  decision: DecisionEnum;
  comments?: (string | null) | undefined;
  signature_data?:
    | /**
     * Base64 encoded signature image (PNG)
     */
    (string | null)
    | undefined;
  signature_meaning?:
    | /**
     * e.g., 'I approve as QA Manager'
     *
     * @maxLength 200
     */
    (string | null)
    | undefined;
  verification_method?: VerificationMethodEnum | undefined;
  delegated_to?: (number | null) | undefined;
  archived?: boolean | undefined;
};
export type ApprovalTemplate = {
  id: string;
  /**
   * @maxLength 100
   */
  template_name: string;
  approval_type: ApprovalTypeEnum;
  approval_type_display: string;
  default_groups?: Array<string> | undefined;
  default_groups_info: Array<unknown>;
  default_approvers?: Array<number> | undefined;
  default_approvers_info: Array<unknown>;
  default_threshold?:
    | /**
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  auto_assign_by_role?:
    | /**
     * Group name to auto-assign (e.g., 'QA_Manager')
     *
     * @maxLength 50
     */
    (string | null)
    | undefined;
  approval_flow_type?: ApprovalFlowTypeEnum | undefined;
  approval_flow_type_display: string;
  delegation_policy?: DelegationPolicyEnum | undefined;
  delegation_policy_display: string;
  approval_sequence?: ApprovalSequenceEnum | undefined;
  approval_sequence_display: string;
  allow_self_approval?: /**
   * Allow requesters to approve their own requests (requires justification)
   */
  boolean | undefined;
  default_due_days?: /**
   * Days until due date
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  escalation_days?:
    | /**
     * Days before escalation triggers
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  escalate_to?: (number | null) | undefined;
  escalate_to_info: {};
  deactivated_at?:
    | /**
     * Null = currently active
     */
    (string | null)
    | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type ApprovalTemplateRequest = {
  /**
   * @minLength 1
   * @maxLength 100
   */
  template_name: string;
  approval_type: ApprovalTypeEnum;
  default_groups?: Array<string> | undefined;
  default_approvers?: Array<number> | undefined;
  default_threshold?:
    | /**
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  auto_assign_by_role?:
    | /**
     * Group name to auto-assign (e.g., 'QA_Manager')
     *
     * @maxLength 50
     */
    (string | null)
    | undefined;
  approval_flow_type?: ApprovalFlowTypeEnum | undefined;
  delegation_policy?: DelegationPolicyEnum | undefined;
  approval_sequence?: ApprovalSequenceEnum | undefined;
  allow_self_approval?: /**
   * Allow requesters to approve their own requests (requires justification)
   */
  boolean | undefined;
  default_due_days?: /**
   * Days until due date
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  escalation_days?:
    | /**
     * Days before escalation triggers
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  escalate_to?: (number | null) | undefined;
  deactivated_at?:
    | /**
     * Null = currently active
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
};
export type AuditLog = {
  id: number;
  /**
   * @maxLength 255
   */
  object_pk: string;
  object_repr: string;
  content_type: number;
  content_type_name: string;
  actor?: (number | null) | undefined;
  actor_info: {};
  remote_addr?: (string | null) | undefined;
  timestamp: string;
  /**
   * @minimum 0
   * @maximum 32767
   */
  action: ActionEnum;
  changes?: unknown | undefined;
};
export type ActionEnum =
  /**
   * * `0` - create
   * `1` - update
   * `2` - delete
   * `3` - access
   *
   * @enum 0, 1, 2, 3
   */
  0 | 1 | 2 | 3;
export type BOM = {
  id: string;
  part_type: string;
  part_type_name: string;
  /**
   * @maxLength 10
   */
  revision: string;
  bom_type?: BOMTypeEnum | undefined;
  status?: BOMStatusEnum | undefined;
  description?: string | undefined;
  effective_date: string | null;
  obsolete_date: string | null;
  approved_by: number | null;
  approved_at: string | null;
  lines: Array<BOMLine>;
  line_count: number;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type BOMTypeEnum =
  /**
   * * `assembly` - Assembly
   * `disassembly` - Disassembly
   *
   * @enum assembly, disassembly
   */
  "assembly" | "disassembly";
export type BOMStatusEnum =
  /**
   * * `draft` - Draft
   * `released` - Released
   * `obsolete` - Obsolete
   *
   * @enum draft, released, obsolete
   */
  "draft" | "released" | "obsolete";
export type BOMLine = {
  id: string;
  bom: string;
  component_type: string;
  component_type_name: string;
  /**
   * @pattern ^-?\d{0,6}(?:\.\d{0,4})?$
   */
  quantity: string;
  unit_of_measure?: /**
   * @maxLength 20
   */
  string | undefined;
  find_number?: /**
   * Drawing callout number
   *
   * @maxLength 20
   */
  string | undefined;
  reference_designator?: /**
   * Reference designator(s) - e.g., 'R1, R2, R3' for electronics
   *
   * @maxLength 100
   */
  string | undefined;
  is_optional?: boolean | undefined;
  allow_harvested?: /**
   * For reman: whether harvested components can satisfy this line
   */
  boolean | undefined;
  notes?: string | undefined;
  line_number?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type BOMList = {
  id: string;
  part_type: string;
  part_type_name: string;
  /**
   * @maxLength 10
   */
  revision: string;
  bom_type?: BOMTypeEnum | undefined;
  status?: BOMStatusEnum | undefined;
  line_count: number;
};
export type BOMRequest = {
  part_type: string;
  /**
   * @minLength 1
   * @maxLength 10
   */
  revision: string;
  bom_type?: BOMTypeEnum | undefined;
  status?: BOMStatusEnum | undefined;
  description?: string | undefined;
  archived?: boolean | undefined;
};
export type BulkAddPartsInputRequest = {
  part_type: string;
  step: string;
  quantity: number;
  part_status?: /**
   * @default "PENDING"
   */
  PartsStatusEnum | undefined;
  work_order?: string | undefined;
  erp_id_start?: /**
   * @default 1
   */
  number | undefined;
};
export type PartsStatusEnum =
  /**
   * * `PENDING` - Pending
   * `IN_PROGRESS` - In Progress
   * `AWAITING_QA` - Awaiting QA
   * `READY FOR NEXT STEP` - Ready for next step
   * `COMPLETED` - Completed
   * `QUARANTINED` - Quarantined
   * `REWORK_NEEDED` - Rework Needed
   * `REWORK_IN_PROGRESS` - Rework In Progress
   * `SCRAPPED` - Scrapped
   * `CANCELLED` - Cancelled
   *
   * @enum PENDING, IN_PROGRESS, AWAITING_QA, READY FOR NEXT STEP, COMPLETED, QUARANTINED, REWORK_NEEDED, REWORK_IN_PROGRESS, SCRAPPED, CANCELLED
   */
  | "PENDING"
  | "IN_PROGRESS"
  | "AWAITING_QA"
  | "READY FOR NEXT STEP"
  | "COMPLETED"
  | "QUARANTINED"
  | "REWORK_NEEDED"
  | "REWORK_IN_PROGRESS"
  | "SCRAPPED"
  | "CANCELLED";
export type CAPA = {
  id: string;
  capa_number: string;
  capa_type: CapaTypeEnum;
  capa_type_display: string;
  severity: SeverityEnum;
  severity_display: string;
  status: string;
  status_display: string;
  /**
   * Clear description of the problem
   */
  problem_statement: string;
  immediate_action?:
    | /**
     * Containment action taken immediately
     */
    (string | null)
    | undefined;
  initiated_by?: (number | null) | undefined;
  initiated_by_info: {};
  initiated_date: string;
  assigned_to?: (number | null) | undefined;
  assigned_to_info: {};
  due_date?:
    | /**
     * User-set due date
     */
    (string | null)
    | undefined;
  completed_date: string | null;
  verified_by?: (number | null) | undefined;
  verified_by_info: {};
  /**
   * Whether this CAPA requires management approval (auto-set for Critical/Major)
   */
  approval_required: boolean;
  approval_status?: /**
     * Approval workflow status
    
    * `NOT_REQUIRED` - Not Required
    * `PENDING` - Pending
    * `APPROVED` - Approved
    * `REJECTED` - Rejected
     */
  ApprovalStatusEnum | undefined;
  approval_status_display: string;
  approved_by: number | null;
  approved_by_info: {};
  approved_at: string | null;
  allow_self_verification?: /**
   * Allow initiator/assignee to verify their own CAPA (requires justification)
   */
  boolean | undefined;
  part?:
    | /**
     * Representative part if applicable
     */
    (string | null)
    | undefined;
  step?:
    | /**
     * Process step where issue occurred
     */
    (string | null)
    | undefined;
  work_order?: (string | null) | undefined;
  quality_reports?: Array<string> | undefined;
  dispositions?: Array<string> | undefined;
  tasks: Array<CapaTasks>;
  rca_records: Array<RcaRecord>;
  verifications: Array<CapaVerification>;
  completion_percentage: number;
  is_overdue: boolean;
  blocking_items: Array<unknown>;
  created_at: string;
  updated_at: string;
  archived: boolean;
};
export type CapaTypeEnum =
  /**
   * * `CORRECTIVE` - Corrective Action
   * `PREVENTIVE` - Preventive Action
   * `CUSTOMER_COMPLAINT` - Customer Complaint
   * `INTERNAL_AUDIT` - Internal Audit
   * `SUPPLIER` - Supplier Issue
   *
   * @enum CORRECTIVE, PREVENTIVE, CUSTOMER_COMPLAINT, INTERNAL_AUDIT, SUPPLIER
   */
  | "CORRECTIVE"
  | "PREVENTIVE"
  | "CUSTOMER_COMPLAINT"
  | "INTERNAL_AUDIT"
  | "SUPPLIER";
export type SeverityEnum =
  /**
   * * `CRITICAL` - Critical
   * `MAJOR` - Major
   * `MINOR` - Minor
   *
   * @enum CRITICAL, MAJOR, MINOR
   */
  "CRITICAL" | "MAJOR" | "MINOR";
export type CapaTasks = {
  id: string;
  task_number: string;
  capa: string;
  capa_info: {};
  task_type: TaskTypeEnum;
  task_type_display: string;
  description: string;
  assigned_to?: (number | null) | undefined;
  assigned_to_info: {};
  assignees: Array<CapaTaskAssignee>;
  completion_mode?: CompletionModeEnum | undefined;
  completion_mode_display: string;
  due_date?: (string | null) | undefined;
  requires_signature?: /**
   * If true, task completion requires signature and password verification
   */
  boolean | undefined;
  status?: CapaTaskStatusEnum | undefined;
  status_display: string;
  completed_by: number | null;
  completed_by_info: {};
  completed_date: string | null;
  completion_notes?: (string | null) | undefined;
  /**
   * Base64-encoded signature image data
   */
  completion_signature: string | null;
  is_overdue: boolean;
  documents_info: {};
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type TaskTypeEnum =
  /**
   * * `CONTAINMENT` - Containment
   * `CORRECTIVE` - Corrective Action
   * `PREVENTIVE` - Preventive Action
   *
   * @enum CONTAINMENT, CORRECTIVE, PREVENTIVE
   */
  "CONTAINMENT" | "CORRECTIVE" | "PREVENTIVE";
export type CapaTaskAssignee = {
  id: string;
  task: string;
  task_info: {};
  user: number;
  user_info: {};
  status?: CapaTaskStatusEnum | undefined;
  completed_at: string | null;
  completion_notes?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type CapaTaskStatusEnum =
  /**
   * * `NOT_STARTED` - Not Started
   * `IN_PROGRESS` - In Progress
   * `COMPLETED` - Completed
   * `CANCELLED` - Cancelled
   *
   * @enum NOT_STARTED, IN_PROGRESS, COMPLETED, CANCELLED
   */
  "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type CompletionModeEnum =
  /**
   * * `SINGLE_OWNER` - Single Owner
   * `ANY_ASSIGNEE` - Any Assignee
   * `ALL_ASSIGNEES` - All Assignees
   *
   * @enum SINGLE_OWNER, ANY_ASSIGNEE, ALL_ASSIGNEES
   */
  "SINGLE_OWNER" | "ANY_ASSIGNEE" | "ALL_ASSIGNEES";
export type RcaRecord = {
  id: string;
  capa: string;
  capa_info: {};
  rca_method: RcaMethodEnum;
  rca_method_display: string;
  problem_description: string;
  root_cause_summary?: (string | null) | undefined;
  conducted_by?: (number | null) | undefined;
  conducted_by_info: {};
  conducted_date?: (string | null) | undefined;
  rca_review_status?: RcaReviewStatusEnum | undefined;
  rca_review_status_display: string;
  root_cause_verification_status?: RootCauseVerificationStatusEnum | undefined;
  root_cause_verification_status_display: string;
  root_cause_verified_at: string | null;
  root_cause_verified_by?: (number | null) | undefined;
  root_cause_verified_by_info: {};
  /**
   * True if conductor verified their own RCA
   */
  self_verified: boolean;
  quality_reports?: Array<string> | undefined;
  dispositions?: Array<string> | undefined;
  root_causes: Array<RootCause>;
  five_whys: FiveWhys;
  fishbone: Fishbone;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type RcaMethodEnum =
  /**
   * * `FIVE_WHYS` - 5 Whys
   * `FISHBONE` - Fishbone Diagram
   * `FAULT_TREE` - Fault Tree
   * `PARETO` - Pareto Analysis
   *
   * @enum FIVE_WHYS, FISHBONE, FAULT_TREE, PARETO
   */
  "FIVE_WHYS" | "FISHBONE" | "FAULT_TREE" | "PARETO";
export type RcaReviewStatusEnum =
  /**
   * * `NOT_REQUIRED` - Not Required
   * `REQUIRED` - Required
   * `COMPLETED` - Completed
   *
   * @enum NOT_REQUIRED, REQUIRED, COMPLETED
   */
  "NOT_REQUIRED" | "REQUIRED" | "COMPLETED";
export type RootCauseVerificationStatusEnum =
  /**
   * * `UNVERIFIED` - Unverified
   * `VERIFIED` - Verified
   * `DISPUTED` - Disputed
   *
   * @enum UNVERIFIED, VERIFIED, DISPUTED
   */
  "UNVERIFIED" | "VERIFIED" | "DISPUTED";
export type RootCause = {
  id: string;
  rca_record: string;
  rca_record_info: {};
  description: string;
  category: RootCauseCategoryEnum;
  category_display: string;
  role?: RoleEnum | undefined;
  role_display: string;
  sequence?: /**
   * Order in causal chain
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type RootCauseCategoryEnum =
  /**
   * * `MAN` - Man (People)
   * `MACHINE` - Machine (Equipment)
   * `MATERIAL` - Material
   * `METHOD` - Method (Process)
   * `MEASUREMENT` - Measurement
   * `ENVIRONMENT` - Environment
   * `OTHER` - Other
   *
   * @enum MAN, MACHINE, MATERIAL, METHOD, MEASUREMENT, ENVIRONMENT, OTHER
   */
  | "MAN"
  | "MACHINE"
  | "MATERIAL"
  | "METHOD"
  | "MEASUREMENT"
  | "ENVIRONMENT"
  | "OTHER";
export type RoleEnum =
  /**
   * * `PRIMARY` - Primary
   * `CONTRIBUTING` - Contributing
   *
   * @enum PRIMARY, CONTRIBUTING
   */
  "PRIMARY" | "CONTRIBUTING";
export type FiveWhys = {
  id: string;
  rca_record: string;
  rca_record_info: {};
  why_1_question?: (string | null) | undefined;
  why_1_answer?: (string | null) | undefined;
  why_2_question?: (string | null) | undefined;
  why_2_answer?: (string | null) | undefined;
  why_3_question?: (string | null) | undefined;
  why_3_answer?: (string | null) | undefined;
  why_4_question?: (string | null) | undefined;
  why_4_answer?: (string | null) | undefined;
  why_5_question?: (string | null) | undefined;
  why_5_answer?: (string | null) | undefined;
  identified_root_cause?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type Fishbone = {
  id: string;
  rca_record: string;
  rca_record_info: {};
  problem_statement: string;
  man_causes?: /**
   * Array of cause strings
   */
  unknown | undefined;
  machine_causes?: unknown | undefined;
  material_causes?: unknown | undefined;
  method_causes?: unknown | undefined;
  measurement_causes?: unknown | undefined;
  environment_causes?: unknown | undefined;
  identified_root_cause?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type CapaVerification = {
  id: string;
  capa: string;
  capa_info: {};
  /**
   * How effectiveness was verified
   */
  verification_method: string;
  /**
   * What defines success
   */
  verification_criteria: string;
  verification_date?: (string | null) | undefined;
  verified_by?: (number | null) | undefined;
  verified_by_info: {};
  effectiveness_result?: EffectivenessResultEnum | undefined;
  effectiveness_result_display: string;
  effectiveness_decided_at: string | null;
  verification_notes?: (string | null) | undefined;
  /**
   * True if initiator/assignee verified their own CAPA
   */
  self_verified: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type EffectivenessResultEnum =
  /**
   * * `CONFIRMED` - Confirmed Effective
   * `NOT_EFFECTIVE` - Not Effective
   * `INCONCLUSIVE` - Inconclusive
   *
   * @enum CONFIRMED, NOT_EFFECTIVE, INCONCLUSIVE
   */
  "CONFIRMED" | "NOT_EFFECTIVE" | "INCONCLUSIVE";
export type CAPARequest = {
  capa_type: CapaTypeEnum;
  severity: SeverityEnum;
  /**
   * Clear description of the problem
   *
   * @minLength 1
   */
  problem_statement: string;
  immediate_action?:
    | /**
     * Containment action taken immediately
     */
    (string | null)
    | undefined;
  initiated_by?: (number | null) | undefined;
  assigned_to?: (number | null) | undefined;
  due_date?:
    | /**
     * User-set due date
     */
    (string | null)
    | undefined;
  verified_by?: (number | null) | undefined;
  approval_status?: /**
     * Approval workflow status
    
    * `NOT_REQUIRED` - Not Required
    * `PENDING` - Pending
    * `APPROVED` - Approved
    * `REJECTED` - Rejected
     */
  ApprovalStatusEnum | undefined;
  allow_self_verification?: /**
   * Allow initiator/assignee to verify their own CAPA (requires justification)
   */
  boolean | undefined;
  part?:
    | /**
     * Representative part if applicable
     */
    (string | null)
    | undefined;
  step?:
    | /**
     * Process step where issue occurred
     */
    (string | null)
    | undefined;
  work_order?: (string | null) | undefined;
  quality_reports?: Array<string> | undefined;
  dispositions?: Array<string> | undefined;
};
export type CalibrationRecord = {
  id: string;
  equipment: string;
  equipment_info: {};
  calibration_date: string;
  due_date: string;
  result?: ResultEnum | undefined;
  result_display: string;
  calibration_type?: CalibrationTypeEnum | undefined;
  calibration_type_display: string;
  performed_by?: /**
   * Person or lab that performed calibration
   *
   * @maxLength 200
   */
  string | undefined;
  external_lab?: /**
   * External calibration lab name if sent out
   *
   * @maxLength 200
   */
  string | undefined;
  certificate_number?: /**
   * Calibration certificate number for traceability
   *
   * @maxLength 100
   */
  string | undefined;
  standards_used?: /**
   * Reference standards used with traceability info (e.g., 'NIST-traceable gauge blocks, cert #12345')
   */
  string | undefined;
  as_found_in_tolerance?:
    | /**
     * Was equipment within tolerance when received for calibration?
     */
    (boolean | null)
    | undefined;
  adjustments_made?: /**
   * Were adjustments made during calibration?
   */
  boolean | undefined;
  notes?: string | undefined;
  status: string;
  is_current: boolean;
  days_until_due: number;
  days_overdue: number | null;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type ResultEnum =
  /**
   * * `pass` - Pass
   * `fail` - Fail
   * `limited` - Limited/Restricted Use
   *
   * @enum pass, fail, limited
   */
  "pass" | "fail" | "limited";
export type CalibrationTypeEnum =
  /**
   * * `scheduled` - Scheduled
   * `initial` - Initial
   * `after_repair` - After Repair
   * `after_adjustment` - After Adjustment
   * `verification` - Verification Check
   *
   * @enum scheduled, initial, after_repair, after_adjustment, verification
   */
  | "scheduled"
  | "initial"
  | "after_repair"
  | "after_adjustment"
  | "verification";
export type CalibrationRecordRequest = {
  equipment: string;
  calibration_date: string;
  due_date: string;
  result?: ResultEnum | undefined;
  calibration_type?: CalibrationTypeEnum | undefined;
  performed_by?: /**
   * Person or lab that performed calibration
   *
   * @maxLength 200
   */
  string | undefined;
  external_lab?: /**
   * External calibration lab name if sent out
   *
   * @maxLength 200
   */
  string | undefined;
  certificate_number?: /**
   * Calibration certificate number for traceability
   *
   * @maxLength 100
   */
  string | undefined;
  standards_used?: /**
   * Reference standards used with traceability info (e.g., 'NIST-traceable gauge blocks, cert #12345')
   */
  string | undefined;
  as_found_in_tolerance?:
    | /**
     * Was equipment within tolerance when received for calibration?
     */
    (boolean | null)
    | undefined;
  adjustments_made?: /**
   * Were adjustments made during calibration?
   */
  boolean | undefined;
  notes?: string | undefined;
  archived?: boolean | undefined;
};
export type CapaTaskAssigneeRequest = {
  task: string;
  user: number;
  status?: CapaTaskStatusEnum | undefined;
  completion_notes?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type CapaTasksRequest = {
  capa: string;
  task_type: TaskTypeEnum;
  /**
   * @minLength 1
   */
  description: string;
  assigned_to?: (number | null) | undefined;
  completion_mode?: CompletionModeEnum | undefined;
  due_date?: (string | null) | undefined;
  requires_signature?: /**
   * If true, task completion requires signature and password verification
   */
  boolean | undefined;
  status?: CapaTaskStatusEnum | undefined;
  completion_notes?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type CapaVerificationRequest = {
  capa: string;
  /**
   * How effectiveness was verified
   *
   * @minLength 1
   */
  verification_method: string;
  /**
   * What defines success
   *
   * @minLength 1
   */
  verification_criteria: string;
  verification_date?: (string | null) | undefined;
  verified_by?: (number | null) | undefined;
  effectiveness_result?: EffectivenessResultEnum | undefined;
  verification_notes?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type ClockInRequest = {
  entry_type: TimeEntryTypeEnum;
  work_order?: (string | null) | undefined;
  part?: (string | null) | undefined;
  step?: (string | null) | undefined;
  equipment?: (string | null) | undefined;
  work_center?: (string | null) | undefined;
  notes?: /**
   * @default ""
   */
  string | undefined;
};
export type TimeEntryTypeEnum =
  /**
   * * `production` - Production
   * `setup` - Setup/Changeover
   * `rework` - Rework
   * `downtime` - Downtime
   * `indirect` - Indirect Labor
   *
   * @enum production, setup, rework, downtime, indirect
   */
  "production" | "setup" | "rework" | "downtime" | "indirect";
export type Core = {
  id: string;
  /**
   * Unique identifier for this core unit (unique per tenant)
   *
   * @maxLength 100
   */
  core_number: string;
  serial_number?: /**
   * Original equipment serial number if available
   *
   * @maxLength 100
   */
  string | undefined;
  /**
   * Type of unit (e.g., Fuel Injector, Turbocharger)
   */
  core_type: string;
  core_type_name: string;
  received_date: string;
  received_by: number;
  received_by_name: string | null;
  customer?:
    | /**
     * Customer who returned this core
     */
    (string | null)
    | undefined;
  customer_name: string | null;
  source_type?: SourceTypeEnum | undefined;
  source_reference?: /**
   * RMA number, PO number, or other reference
   *
   * @maxLength 100
   */
  string | undefined;
  /**
     * Overall condition grade assigned at receipt
    
    * `A` - Grade A - Excellent
    * `B` - Grade B - Good
    * `C` - Grade C - Fair
    * `SCRAP` - Scrap - Not Usable
     */
  condition_grade: ConditionGradeEnum;
  condition_notes?: /**
   * Detailed notes on condition observed at receipt
   */
  string | undefined;
  status?: CoreStatusEnum | undefined;
  disassembly_started_at: string | null;
  disassembly_completed_at: string | null;
  disassembled_by: number | null;
  disassembled_by_name: string | null;
  core_credit_value?:
    | /**
     * Credit value to be issued for this core
     *
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    (string | null)
    | undefined;
  core_credit_issued?: /**
   * Whether core credit has been issued to customer
   */
  boolean | undefined;
  core_credit_issued_at: string | null;
  work_order?: (string | null) | undefined;
  harvested_component_count: number;
  usable_component_count: number;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type SourceTypeEnum =
  /**
   * * `customer_return` - Customer Return
   * `purchased` - Purchased Core
   * `warranty` - Warranty Return
   * `trade_in` - Trade-In
   *
   * @enum customer_return, purchased, warranty, trade_in
   */
  "customer_return" | "purchased" | "warranty" | "trade_in";
export type CoreStatusEnum =
  /**
   * * `received` - Received
   * `in_disassembly` - In Disassembly
   * `disassembled` - Disassembled
   * `scrapped` - Scrapped
   *
   * @enum received, in_disassembly, disassembled, scrapped
   */
  "received" | "in_disassembly" | "disassembled" | "scrapped";
export type CoreList = {
  id: string;
  /**
   * Unique identifier for this core unit (unique per tenant)
   *
   * @maxLength 100
   */
  core_number: string;
  /**
   * Type of unit (e.g., Fuel Injector, Turbocharger)
   */
  core_type: string;
  core_type_name: string;
  customer_name: string | null;
  status?: CoreStatusEnum | undefined;
  /**
     * Overall condition grade assigned at receipt
    
    * `A` - Grade A - Excellent
    * `B` - Grade B - Good
    * `C` - Grade C - Fair
    * `SCRAP` - Scrap - Not Usable
     */
  condition_grade: ConditionGradeEnum;
  received_date: string;
};
export type CoreRequest = {
  /**
   * Unique identifier for this core unit (unique per tenant)
   *
   * @minLength 1
   * @maxLength 100
   */
  core_number: string;
  serial_number?: /**
   * Original equipment serial number if available
   *
   * @maxLength 100
   */
  string | undefined;
  /**
   * Type of unit (e.g., Fuel Injector, Turbocharger)
   */
  core_type: string;
  received_date: string;
  customer?:
    | /**
     * Customer who returned this core
     */
    (string | null)
    | undefined;
  source_type?: SourceTypeEnum | undefined;
  source_reference?: /**
   * RMA number, PO number, or other reference
   *
   * @maxLength 100
   */
  string | undefined;
  /**
     * Overall condition grade assigned at receipt
    
    * `A` - Grade A - Excellent
    * `B` - Grade B - Good
    * `C` - Grade C - Fair
    * `SCRAP` - Scrap - Not Usable
     */
  condition_grade: ConditionGradeEnum;
  condition_notes?: /**
   * Detailed notes on condition observed at receipt
   */
  string | undefined;
  status?: CoreStatusEnum | undefined;
  core_credit_value?:
    | /**
     * Credit value to be issued for this core
     *
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    (string | null)
    | undefined;
  core_credit_issued?: /**
   * Whether core credit has been issued to customer
   */
  boolean | undefined;
  work_order?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type CurrentTenantResponse = {
  tenant: TenantInfo;
  deployment: DeploymentInfo;
  features: {};
  limits: {};
  user: {};
};
export type TenantInfo = {
  id: string;
  name: string;
  /**
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier: string;
  status: string;
  is_demo: boolean;
  trial_ends_at: string | null;
  logo_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  address: string | null;
  default_timezone: string;
};
export type DeploymentInfo = {
  mode: ModeEnum;
  is_saas: boolean;
  is_dedicated: boolean;
};
export type ModeEnum =
  /**
   * * `saas` - saas
   * `dedicated` - dedicated
   *
   * @enum saas, dedicated
   */
  "saas" | "dedicated";
export type Documents = {
  id: string;
  classification?:
    | /**
     * Security classification level for document access control
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
    (ClassificationEnum | NullEnum | null)
    | undefined;
  ai_readable?: boolean | undefined;
  is_image?: boolean | undefined;
  /**
   * @maxLength 50
   */
  file_name: string;
  file: string;
  file_url: string;
  upload_date: string;
  uploaded_by?: (number | null) | undefined;
  uploaded_by_info: {};
  content_type?:
    | /**
     * Model of the object this document relates to
     */
    (number | null)
    | undefined;
  object_id?:
    | /**
     * ID of the object this document relates to (CharField for UUID compatibility)
     *
     * @maxLength 36
     */
    (string | null)
    | undefined;
  content_type_info: {};
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  access_info: {};
  auto_properties: {};
  status?: /**
     * Document workflow status
    
    * `DRAFT` - Draft
    * `UNDER_REVIEW` - Under Review
    * `APPROVED` - Approved
    * `RELEASED` - Released
    * `OBSOLETE` - Obsolete
     */
  DocumentsStatusEnum | undefined;
  status_display: string;
  approved_by: number | null;
  approved_by_info: {};
  approved_at: string | null;
  document_type?:
    | /**
     * Type/category of document (e.g., SOP, Work Instruction)
     */
    (string | null)
    | undefined;
  document_type_info: {};
  change_justification?: /**
   * Reason for this revision (required when creating new versions)
   */
  string | undefined;
  previous_version: string | null;
  is_current_version: boolean;
  /**
   * Date when this document version becomes effective (typically set on release)
   */
  effective_date: string | null;
  /**
   * Next scheduled review date (auto-calculated from document_type.default_review_period_days)
   */
  review_date: string | null;
  /**
   * Date when document was marked obsolete (set automatically on status change)
   */
  obsolete_date: string | null;
  /**
   * Date until which this document must be retained (calculated from effective_date + retention_days)
   */
  retention_until: string | null;
  is_due_for_review: boolean;
  days_until_review: number | null;
  is_past_retention: boolean;
  itar_controlled?: /**
   * Document contains ITAR-controlled technical data (22 CFR 120-130)
   */
  boolean | undefined;
  eccn?: /**
   * Export Control Classification Number (e.g., EAR99, 3A001, 9A004.a)
   *
   * @maxLength 20
   */
  string | undefined;
  export_control_reason?: /**
   * Reason for export control classification (e.g., 'Contains defense article specs')
   *
   * @maxLength 100
   */
  string | undefined;
  created_at: string;
  updated_at: string;
};
export type ClassificationEnum =
  /**
   * * `public` - Public
   * `internal` - Internal Use
   * `confidential` - Confidential
   * `restricted` - Restricted
   * `secret` - Secret
   *
   * @enum public, internal, confidential, restricted, secret
   */
  "public" | "internal" | "confidential" | "restricted" | "secret";
export type NullEnum =
  /**
   * @enum
   */
  unknown;
export type DocumentsStatusEnum =
  /**
   * * `DRAFT` - Draft
   * `UNDER_REVIEW` - Under Review
   * `APPROVED` - Approved
   * `RELEASED` - Released
   * `OBSOLETE` - Obsolete
   *
   * @enum DRAFT, UNDER_REVIEW, APPROVED, RELEASED, OBSOLETE
   */
  "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "RELEASED" | "OBSOLETE";
export type DocumentsRequest = {
  classification?:
    | /**
     * Security classification level for document access control
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
    (ClassificationEnum | NullEnum | null)
    | undefined;
  ai_readable?: boolean | undefined;
  is_image?: boolean | undefined;
  /**
   * @minLength 1
   * @maxLength 50
   */
  file_name: string;
  file: string;
  uploaded_by?: (number | null) | undefined;
  content_type?:
    | /**
     * Model of the object this document relates to
     */
    (number | null)
    | undefined;
  object_id?:
    | /**
     * ID of the object this document relates to (CharField for UUID compatibility)
     *
     * @maxLength 36
     */
    (string | null)
    | undefined;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  status?: /**
     * Document workflow status
    
    * `DRAFT` - Draft
    * `UNDER_REVIEW` - Under Review
    * `APPROVED` - Approved
    * `RELEASED` - Released
    * `OBSOLETE` - Obsolete
     */
  DocumentsStatusEnum | undefined;
  document_type?:
    | /**
     * Type/category of document (e.g., SOP, Work Instruction)
     */
    (string | null)
    | undefined;
  document_type_code?: /**
   * @minLength 1
   */
  string | undefined;
  change_justification?: /**
   * Reason for this revision (required when creating new versions)
   */
  string | undefined;
  itar_controlled?: /**
   * Document contains ITAR-controlled technical data (22 CFR 120-130)
   */
  boolean | undefined;
  eccn?: /**
   * Export Control Classification Number (e.g., EAR99, 3A001, 9A004.a)
   *
   * @maxLength 20
   */
  string | undefined;
  export_control_reason?: /**
   * Reason for export control classification (e.g., 'Contains defense article specs')
   *
   * @maxLength 100
   */
  string | undefined;
};
export type DowntimeEvent = {
  id: string;
  equipment?: (string | null) | undefined;
  equipment_name: string | null;
  work_center?: (string | null) | undefined;
  work_center_name: string | null;
  category: DowntimeCategoryEnum;
  /**
   * @maxLength 200
   */
  reason: string;
  description?: string | undefined;
  start_time: string;
  end_time?: (string | null) | undefined;
  duration_minutes: number | null;
  work_order?: (string | null) | undefined;
  reported_by: number;
  reported_by_name: string | null;
  resolved_by: number | null;
  resolved_by_name: string | null;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type DowntimeCategoryEnum =
  /**
   * * `planned` - Planned Maintenance
   * `unplanned` - Unplanned/Breakdown
   * `changeover` - Changeover/Setup
   * `calibration` - Calibration
   * `no_work` - No Work Available
   * `no_operator` - No Operator Available
   * `material` - Waiting for Material
   * `quality` - Quality Issue
   * `other` - Other
   *
   * @enum planned, unplanned, changeover, calibration, no_work, no_operator, material, quality, other
   */
  | "planned"
  | "unplanned"
  | "changeover"
  | "calibration"
  | "no_work"
  | "no_operator"
  | "material"
  | "quality"
  | "other";
export type DowntimeEventRequest = {
  equipment?: (string | null) | undefined;
  work_center?: (string | null) | undefined;
  category: DowntimeCategoryEnum;
  /**
   * @minLength 1
   * @maxLength 200
   */
  reason: string;
  description?: string | undefined;
  start_time: string;
  end_time?: (string | null) | undefined;
  work_order?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type Equipments = {
  id: string;
  /**
   * @maxLength 100
   */
  name: string;
  equipment_type?: (string | null) | undefined;
  equipment_type_name: string;
  serial_number?: /**
   * @maxLength 100
   */
  string | undefined;
  manufacturer?: /**
   * @maxLength 100
   */
  string | undefined;
  model_number?: /**
   * @maxLength 100
   */
  string | undefined;
  location?: /**
   * @maxLength 100
   */
  string | undefined;
  status?: EquipmentsStatusEnum | undefined;
  notes?: string | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type EquipmentsStatusEnum =
  /**
   * * `in_service` - In Service
   * `out_of_service` - Out of Service
   * `in_calibration` - In Calibration
   * `in_maintenance` - In Maintenance
   * `retired` - Retired
   *
   * @enum in_service, out_of_service, in_calibration, in_maintenance, retired
   */
  | "in_service"
  | "out_of_service"
  | "in_calibration"
  | "in_maintenance"
  | "retired";
export type EquipmentsRequest = {
  /**
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  equipment_type?: (string | null) | undefined;
  serial_number?: /**
   * @maxLength 100
   */
  string | undefined;
  manufacturer?: /**
   * @maxLength 100
   */
  string | undefined;
  model_number?: /**
   * @maxLength 100
   */
  string | undefined;
  location?: /**
   * @maxLength 100
   */
  string | undefined;
  status?: EquipmentsStatusEnum | undefined;
  notes?: string | undefined;
  archived?: boolean | undefined;
};
export type GenerateReportRequest = {
  /**
     * Type of report to generate (spc, capa, quality_report, etc.)
    
    * `spc` - spc
    * `capa` - capa
    * `quality_report` - quality_report
     */
  report_type: ReportTypeEnum;
  /**
   * Parameters specific to the report type
   */
  params: {};
};
export type ReportTypeEnum =
  /**
   * * `spc` - spc
   * `capa` - capa
   * `quality_report` - quality_report
   *
   * @enum spc, capa, quality_report
   */
  "spc" | "capa" | "quality_report";
export type GeneratedReport = {
  id: string;
  /**
   * Type of report: spc, capa, quality_report, etc.
   */
  report_type: string;
  generated_by: number | null;
  generated_by_name: string | null;
  generated_at: string;
  /**
   * Parameters used to generate the report (for reproducibility)
   */
  parameters: unknown;
  /**
   * The Document containing the generated PDF file
   */
  document: string | null;
  document_url: string | null;
  /**
   * Email address the report was sent to
   */
  emailed_to: string | null;
  emailed_at: string | null;
  status: GeneratedReportStatusEnum;
  /**
   * Error details if generation failed
   */
  error_message: string | null;
};
export type GeneratedReportStatusEnum =
  /**
   * * `PENDING` - Pending
   * `COMPLETED` - Completed
   * `FAILED` - Failed
   *
   * @enum PENDING, COMPLETED, FAILED
   */
  "PENDING" | "COMPLETED" | "FAILED";
export type GroupAddPermissionsResponse = {
  detail: string;
  added_count: number;
  group: Group;
};
export type Group = {
  id: number;
  /**
   * @maxLength 150
   */
  name: string;
  description: string | null;
  user_count: number;
  users: Array<{}>;
  permissions: Array<{}>;
};
export type GroupAddUsersResponse = {
  detail: string;
  group: Group;
};
export type GroupRemovePermissionsResponse = {
  detail: string;
  removed_count: number;
  group: Group;
};
export type GroupRemoveUsersResponse = {
  detail: string;
  group: Group;
};
export type GroupSetPermissionsResponse = {
  detail: string;
  group: Group;
};
export type HarvestedComponentRequest = {
  core: string;
  component_type: string;
  condition_grade: ConditionGradeEnum;
  condition_notes?: string | undefined;
  position?: /**
   * Position within core (e.g., 'Cyl 1', 'Position A')
   *
   * @maxLength 50
   */
  string | undefined;
  original_part_number?: /**
   * Original part number if readable
   *
   * @maxLength 100
   */
  string | undefined;
  archived?: boolean | undefined;
};
export type HeatMapAnnotations = {
  id: string;
  model: string;
  model_display: string;
  part: string;
  part_display: string;
  position_x: number;
  position_y: number;
  position_z: number;
  measurement_value?: (number | null) | undefined;
  defect_type?:
    | /**
     * @maxLength 255
     */
    (string | null)
    | undefined;
  severity?:
    | (HeatMapAnnotationsSeverityEnum | BlankEnum | NullEnum | null)
    | undefined;
  notes?: string | undefined;
  quality_reports?: Array<string> | undefined;
  created_by: number | null;
  created_by_display: string;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
  deleted_at: string | null;
};
export type HeatMapAnnotationsSeverityEnum =
  /**
   * * `low` - Low
   * `medium` - Medium
   * `high` - High
   * `critical` - Critical
   *
   * @enum low, medium, high, critical
   */
  "low" | "medium" | "high" | "critical";
export type BlankEnum =
  /**
   * @enum
   */
  unknown;
export type HeatMapAnnotationsRequest = {
  model: string;
  part: string;
  position_x: number;
  position_y: number;
  position_z: number;
  measurement_value?: (number | null) | undefined;
  defect_type?:
    | /**
     * @maxLength 255
     */
    (string | null)
    | undefined;
  severity?:
    | (HeatMapAnnotationsSeverityEnum | BlankEnum | NullEnum | null)
    | undefined;
  notes?: string | undefined;
  quality_reports?: Array<string> | undefined;
  archived?: boolean | undefined;
};
export type HeatMapFacetsResponse = {
  defect_types: Array<DefectTypeFacet>;
  severities: Array<SeverityFacet>;
  total_count: number;
};
export type DefectTypeFacet = {
  value: string;
  count: number;
};
export type SeverityFacet = {
  value: string;
  count: number;
};
export type ImportResponse = {
  summary: ImportSummary;
  results: Array<{}>;
};
export type ImportSummary = {
  total: number;
  created: number;
  updated: number;
  errors: number;
};
export type MaterialLot = {
  id: string;
  /**
   * @maxLength 100
   */
  lot_number: string;
  parent_lot?: (string | null) | undefined;
  parent_lot_number: string | null;
  material_type?: (string | null) | undefined;
  material_type_name: string | null;
  material_description?: /**
   * Description for raw materials not tracked as PartTypes
   *
   * @maxLength 200
   */
  string | undefined;
  supplier?: (string | null) | undefined;
  supplier_name: string | null;
  supplier_lot_number?: /**
   * Supplier's lot/batch number
   *
   * @maxLength 100
   */
  string | undefined;
  received_date: string;
  received_by: number;
  /**
   * @pattern ^-?\d{0,8}(?:\.\d{0,4})?$
   */
  quantity: string;
  /**
   * @pattern ^-?\d{0,8}(?:\.\d{0,4})?$
   */
  quantity_remaining: string;
  /**
   * @maxLength 20
   */
  unit_of_measure: string;
  status?: MaterialLotStatusEnum | undefined;
  manufacture_date?: (string | null) | undefined;
  expiration_date?: (string | null) | undefined;
  certificate_of_conformance?: (string | null) | undefined;
  storage_location?: /**
   * @maxLength 100
   */
  string | undefined;
  child_lot_count: number;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type MaterialLotStatusEnum =
  /**
   * * `received` - Received
   * `in_use` - In Use
   * `consumed` - Consumed
   * `scrapped` - Scrapped
   * `quarantine` - Quarantine
   *
   * @enum received, in_use, consumed, scrapped, quarantine
   */
  "received" | "in_use" | "consumed" | "scrapped" | "quarantine";
export type MaterialLotRequest = {
  /**
   * @minLength 1
   * @maxLength 100
   */
  lot_number: string;
  parent_lot?: (string | null) | undefined;
  material_type?: (string | null) | undefined;
  material_description?: /**
   * Description for raw materials not tracked as PartTypes
   *
   * @maxLength 200
   */
  string | undefined;
  supplier?: (string | null) | undefined;
  supplier_lot_number?: /**
   * Supplier's lot/batch number
   *
   * @maxLength 100
   */
  string | undefined;
  received_date: string;
  /**
   * @pattern ^-?\d{0,8}(?:\.\d{0,4})?$
   */
  quantity: string;
  /**
   * @minLength 1
   * @maxLength 20
   */
  unit_of_measure: string;
  status?: MaterialLotStatusEnum | undefined;
  manufacture_date?: (string | null) | undefined;
  expiration_date?: (string | null) | undefined;
  certificate_of_conformance?: (string | null) | undefined;
  storage_location?: /**
   * @maxLength 100
   */
  string | undefined;
  archived?: boolean | undefined;
};
export type MeasurementDefinition = {
  id: string;
  /**
   * @maxLength 100
   */
  label: string;
  step_name: string;
  unit?: /**
   * @maxLength 50
   */
  string | undefined;
  nominal?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  upper_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  lower_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  required?: boolean | undefined;
  type: TypeEnum;
  step: string;
  archived?: boolean | undefined;
};
export type TypeEnum =
  /**
   * * `NUMERIC` - Numeric
   * `PASS_FAIL` - Pass/Fail
   *
   * @enum NUMERIC, PASS_FAIL
   */
  "NUMERIC" | "PASS_FAIL";
export type MeasurementDefinitionRequest = {
  /**
   * @minLength 1
   * @maxLength 100
   */
  label: string;
  unit?: /**
   * @maxLength 50
   */
  string | undefined;
  nominal?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  upper_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  lower_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  required?: boolean | undefined;
  type: TypeEnum;
  archived?: boolean | undefined;
};
export type MeasurementDefinitionSPC = {
  id: string;
  /**
   * @maxLength 100
   */
  label: string;
  type: TypeEnum;
  unit?: /**
   * @maxLength 50
   */
  string | undefined;
  nominal?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  upper_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  lower_tol?:
    | /**
     * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
};
export type MeasurementResult = {
  report: string;
  definition: string;
  value_numeric?: (number | null) | undefined;
  value_pass_fail?:
    | (ValuePassFailEnum | BlankEnum | NullEnum | null)
    | undefined;
  is_within_spec: boolean;
  created_by: number;
  archived?: boolean | undefined;
};
export type ValuePassFailEnum =
  /**
   * * `PASS` - Pass
   * `FAIL` - Fail
   *
   * @enum PASS, FAIL
   */
  "PASS" | "FAIL";
export type MeasurementResultRequest = {
  definition: string;
  value_numeric?: (number | null) | undefined;
  value_pass_fail?:
    | (ValuePassFailEnum | BlankEnum | NullEnum | null)
    | undefined;
  archived?: boolean | undefined;
};
export type NotificationPreference = {
  id: number;
  notification_type: NotificationTypeEnum;
  notification_type_display: string;
  channel_type?: ChannelTypeEnum | undefined;
  channel_type_display: string;
  status: NotificationTaskStatusEnum;
  status_display: string;
  schedule?: NotificationSchedule | undefined;
  /**
   * When this notification should be sent (UTC)
   */
  next_send_at: string;
  next_send_at_display: string | null;
  last_sent_at: string | null;
  last_sent_at_display: string | null;
  attempt_count: number;
  max_attempts?:
    | /**
     * Max sends before stopping. Null = infinite
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  created_at: string;
  updated_at: string;
};
export type NotificationTypeEnum =
  /**
   * * `WEEKLY_REPORT` - Weekly Order Report
   * `CAPA_REMINDER` - CAPA Reminder
   * `APPROVAL_REQUEST` - Approval Request
   * `APPROVAL_DECISION` - Approval Decision
   * `APPROVAL_ESCALATION` - Approval Escalation
   *
   * @enum WEEKLY_REPORT, CAPA_REMINDER, APPROVAL_REQUEST, APPROVAL_DECISION, APPROVAL_ESCALATION
   */
  | "WEEKLY_REPORT"
  | "CAPA_REMINDER"
  | "APPROVAL_REQUEST"
  | "APPROVAL_DECISION"
  | "APPROVAL_ESCALATION";
export type ChannelTypeEnum =
  /**
   * * `email` - Email
   * `in_app` - In-App Notification
   * `sms` - SMS
   *
   * @enum email, in_app, sms
   */
  "email" | "in_app" | "sms";
export type NotificationTaskStatusEnum =
  /**
   * * `pending` - Pending
   * `sent` - Sent
   * `failed` - Failed
   * `cancelled` - Cancelled
   *
   * @enum pending, sent, failed, cancelled
   */
  "pending" | "sent" | "failed" | "cancelled";
export type NotificationSchedule = {
  interval_type: IntervalTypeEnum;
  day_of_week?:
    | /**
     * 0=Monday, 6=Sunday
     *
     * @minimum 0
     * @maximum 6
     */
    (number | null)
    | undefined;
  time?:
    | /**
     * Time in user's local timezone
     */
    (string | null)
    | undefined;
  interval_weeks?:
    | /**
     * Number of weeks between sends
     *
     * @minimum 1
     */
    (number | null)
    | undefined;
  escalation_tiers?:
    | /**
     * List of [threshold_days, interval_days] tuples
     */
    (Array<Array<number>> | null)
    | undefined;
};
export type IntervalTypeEnum =
  /**
   * * `fixed` - fixed
   * `deadline_based` - deadline_based
   *
   * @enum fixed, deadline_based
   */
  "fixed" | "deadline_based";
export type NotificationPreferenceRequest = {
  notification_type: NotificationTypeEnum;
  channel_type?: ChannelTypeEnum | undefined;
  schedule?: NotificationScheduleRequest | undefined;
  max_attempts?:
    | /**
     * Max sends before stopping. Null = infinite
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
};
export type NotificationScheduleRequest = {
  interval_type: IntervalTypeEnum;
  day_of_week?:
    | /**
     * 0=Monday, 6=Sunday
     *
     * @minimum 0
     * @maximum 6
     */
    (number | null)
    | undefined;
  time?:
    | /**
     * Time in user's local timezone
     */
    (string | null)
    | undefined;
  interval_weeks?:
    | /**
     * Number of weeks between sends
     *
     * @minimum 1
     */
    (number | null)
    | undefined;
  escalation_tiers?:
    | /**
     * List of [threshold_days, interval_days] tuples
     */
    (Array<Array<number>> | null)
    | undefined;
};
export type Orders = {
  id: string;
  /**
   * Auto-generated internal order number: ORD-YYYY-####
   */
  order_number: string;
  /**
   * @maxLength 200
   */
  name: string;
  customer_note?: (string | null) | undefined;
  latest_note: {};
  notes_timeline: Array<unknown>;
  customer?: (number | null) | undefined;
  customer_info: {};
  company?: (string | null) | undefined;
  company_info: {};
  estimated_completion?: (string | null) | undefined;
  original_completion_date: string | null;
  order_status: OrdersStatusEnum;
  current_hubspot_gate?: (string | null) | undefined;
  parts_summary: {};
  process_stages: Array<unknown>;
  gate_info: {};
  customer_first_name: string | null;
  customer_last_name: string | null;
  company_name: string | null;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type OrdersStatusEnum =
  /**
   * * `RFI` - RFI
   * `PENDING` - Pending
   * `IN_PROGRESS` - In progress
   * `COMPLETED` - Completed
   * `ON_HOLD` - On hold
   * `CANCELLED` - Cancelled
   *
   * @enum RFI, PENDING, IN_PROGRESS, COMPLETED, ON_HOLD, CANCELLED
   */
  "RFI" | "PENDING" | "IN_PROGRESS" | "COMPLETED" | "ON_HOLD" | "CANCELLED";
export type OrdersRequest = {
  /**
   * @minLength 1
   * @maxLength 200
   */
  name: string;
  customer_note?: (string | null) | undefined;
  customer?: (number | null) | undefined;
  company?: (string | null) | undefined;
  estimated_completion?: (string | null) | undefined;
  order_status: OrdersStatusEnum;
  current_hubspot_gate?: (string | null) | undefined;
  archived?: boolean | undefined;
};
export type PaginatedApprovalRequestList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ApprovalRequest>;
};
export type PaginatedApprovalResponseList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ApprovalResponse>;
};
export type PaginatedApprovalTemplateList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ApprovalTemplate>;
};
export type PaginatedAssemblyUsageList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<AssemblyUsage>;
};
export type AssemblyUsage = {
  id: string;
  /**
   * The parent assembly this component was installed into
   */
  assembly: string;
  assembly_erp_id: string;
  /**
   * The component part installed
   */
  component: string;
  component_erp_id: string;
  quantity?: /**
   * @pattern ^-?\d{0,6}(?:\.\d{0,4})?$
   */
  string | undefined;
  bom_line?: (string | null) | undefined;
  installed_at: string;
  installed_by: number;
  installed_by_name: string;
  step?: (string | null) | undefined;
  removed_at: string | null;
  removed_by: number | null;
  removal_reason: string;
  is_installed: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedAuditLogList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<AuditLog>;
};
export type PaginatedAvailableUserResponseList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<AvailableUserResponse>;
};
export type AvailableUserResponse = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  groups: Array<string>;
};
export type PaginatedBOMLineList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<BOMLine>;
};
export type PaginatedBOMListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<BOMList>;
};
export type PaginatedCAPAList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CAPA>;
};
export type PaginatedCalibrationRecordList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CalibrationRecord>;
};
export type PaginatedCapaTasksList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CapaTasks>;
};
export type PaginatedCapaVerificationList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CapaVerification>;
};
export type PaginatedChatSessionList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ChatSession>;
};
export type ChatSession = {
  id: number;
  /**
   * @maxLength 255
   */
  langgraph_thread_id: string;
  title?: /**
   * @maxLength 255
   */
  string | undefined;
  is_archived?: boolean | undefined;
  created_at: string;
  updated_at: string;
};
export type PaginatedCompanyList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Company>;
};
export type Company = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  description: string;
  hubspot_api_id?:
    | /**
     * @maxLength 50
     */
    (string | null)
    | undefined;
  user_count: number;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedCoreListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CoreList>;
};
export type PaginatedCustomerOrderList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<CustomerOrder>;
};
export type CustomerOrder = {
  id: string;
  /**
   * Auto-generated internal order number: ORD-YYYY-####
   */
  order_number: string;
  name: string;
  latest_note: {};
  notes_timeline: Array<unknown>;
  order_status: string;
  order_status_code: string;
  estimated_completion: string | null;
  original_completion_date: string | null;
  process_stages: Array<unknown>;
  gate_info: {};
  parts_summary: {};
  company_name: string | null;
  customer_first_name: string | null;
  customer_last_name: string | null;
  created_at: string;
  updated_at: string;
};
export type PaginatedDisassemblyBOMLineList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<DisassemblyBOMLine>;
};
export type DisassemblyBOMLine = {
  id: string;
  /**
   * The type of core being disassembled
   */
  core_type: string;
  core_type_name: string;
  /**
   * The type of component expected from disassembly
   */
  component_type: string;
  component_type_name: string;
  expected_qty?: /**
   * Number of this component expected per core
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  expected_fallout_rate?: /**
   * Expected percentage of components that won't be usable (0.10 = 10%)
   *
   * @pattern ^-?\d{0,3}(?:\.\d{0,2})?$
   */
  string | undefined;
  expected_usable_qty: number;
  notes?: /**
   * Special handling instructions or notes
   */
  string | undefined;
  line_number?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedDocumentTypeList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<DocumentType>;
};
export type DocumentType = {
  id: string;
  /**
   * Display name (e.g., 'Standard Operating Procedure')
   *
   * @maxLength 100
   */
  name: string;
  /**
   * Short code for ID prefix (e.g., 'SOP', 'WI', 'DWG')
   *
   * @maxLength 20
   */
  code: string;
  description?: /**
   * Description of this document type
   */
  string | undefined;
  requires_approval?: /**
   * Whether documents of this type require approval before release
   */
  boolean | undefined;
  approval_template?:
    | /**
     * Approval template to use for this document type (defaults to DOCUMENT_RELEASE if not set)
     */
    (string | null)
    | undefined;
  approval_template_name: string | null;
  default_review_period_days?:
    | /**
     * Default number of days between reviews for documents of this type (e.g., 365 for annual review)
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  default_retention_days?:
    | /**
     * Default retention period in days for documents of this type (e.g., 2555 for 7 years)
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedDocumentsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Documents>;
};
export type PaginatedDowntimeEventList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<DowntimeEvent>;
};
export type PaginatedEquipmentTypeList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<EquipmentType>;
};
export type EquipmentType = {
  id: string;
  external_id?:
    | /**
     * External system identifier for integration sync
     *
     * @maxLength 255
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_current_version?: boolean | undefined;
  /**
   * @maxLength 50
   */
  name: string;
  description?: string | undefined;
  requires_calibration?: boolean | undefined;
  default_calibration_interval_days?:
    | /**
     * Default calibration interval in days for new equipment of this type
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  is_portable?: boolean | undefined;
  track_downtime?: boolean | undefined;
  tenant?:
    | /**
     * Tenant this record belongs to
     */
    (string | null)
    | undefined;
  previous_version?: (string | null) | undefined;
};
export type PaginatedEquipmentsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Equipments>;
};
export type PaginatedFishboneList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Fishbone>;
};
export type PaginatedFiveWhysList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<FiveWhys>;
};
export type PaginatedGeneratedReportList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<GeneratedReport>;
};
export type PaginatedGroupList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Group>;
};
export type PaginatedHarvestedComponentList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<HarvestedComponent>;
};
export type PaginatedHeatMapAnnotationsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<HeatMapAnnotations>;
};
export type PaginatedMaterialLotList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<MaterialLot>;
};
export type PaginatedMaterialUsageList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<MaterialUsage>;
};
export type MaterialUsage = {
  id: string;
  lot?: (string | null) | undefined;
  lot_number: string | null;
  harvested_component?: (string | null) | undefined;
  part: string;
  part_erp_id: string;
  work_order?: (string | null) | undefined;
  step?: (string | null) | undefined;
  /**
   * @pattern ^-?\d{0,8}(?:\.\d{0,4})?$
   */
  qty_consumed: string;
  consumed_at: string;
  consumed_by: number;
  consumed_by_name: string;
  is_substitute?: /**
   * True if this material was a substitute for the BOM-specified material
   */
  boolean | undefined;
  substitution_reason?: /**
   * @maxLength 200
   */
  string | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedMeasurementDefinitionList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<MeasurementDefinition>;
};
export type PaginatedNotificationPreferenceList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<NotificationPreference>;
};
export type PaginatedOrdersList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Orders>;
};
export type PaginatedPartSelectList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<PartSelect>;
};
export type PartSelect = {
  id: string;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  part_type?: (string | null) | undefined;
  part_type_name: string | null;
  part_status?: PartsStatusEnum | undefined;
};
export type PaginatedPartTypeSelectList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<PartTypeSelect>;
};
export type PartTypeSelect = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  ID_prefix?:
    | /**
     * @maxLength 50
     */
    (string | null)
    | undefined;
};
export type PaginatedPartTypesList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<PartTypes>;
};
export type PartTypes = {
  id: string;
  external_id?:
    | /**
     * External system identifier for integration sync
     *
     * @maxLength 255
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_current_version?: boolean | undefined;
  /**
   * @maxLength 50
   */
  name: string;
  ID_prefix?:
    | /**
     * @maxLength 50
     */
    (string | null)
    | undefined;
  ERP_id?:
    | /**
     * @maxLength 50
     */
    (string | null)
    | undefined;
  itar_controlled?: /**
   * Part type is ITAR-controlled defense article (22 CFR 121 USML)
   */
  boolean | undefined;
  eccn?: /**
   * Default ECCN for parts of this type (e.g., EAR99, 9A004)
   *
   * @maxLength 20
   */
  string | undefined;
  usml_category?: /**
   * USML Category if ITAR-controlled (e.g., IV, XI, XIX)
   *
   * @maxLength 10
   */
  string | undefined;
  tenant?:
    | /**
     * Tenant this record belongs to
     */
    (string | null)
    | undefined;
  previous_version?: (string | null) | undefined;
};
export type PaginatedPartsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Parts>;
};
export type Parts = {
  id: string;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  part_status?: PartsStatusEnum | undefined;
  requires_sampling: boolean;
  order?: string | undefined;
  part_type: string;
  part_type_info: {};
  step: string;
  step_info: {};
  work_order?: (string | null) | undefined;
  quality_info: {};
  created_at: string;
  updated_at: string;
  has_error: boolean;
  part_type_name: string | null;
  process_name: string | null;
  order_name: string | null;
  step_description: string;
  work_order_erp_id: string | null;
  is_from_batch_process: boolean;
  sampling_rule?: (string | null) | undefined;
  sampling_ruleset?: (string | null) | undefined;
  sampling_context?: unknown | undefined;
  process: string | null;
  total_rework_count: number;
  archived?: boolean | undefined;
};
export type PaginatedProcessWithStepsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ProcessWithSteps>;
};
export type ProcessWithSteps = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  is_remanufactured?: boolean | undefined;
  part_type: string;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
  process_steps: Array<ProcessStep>;
  step_edges: Array<StepEdge>;
  status?: /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  ProcessStatusEnum | undefined;
  change_description?:
    | /**
     * Description of changes from previous version (for approval review)
     */
    (string | null)
    | undefined;
  approved_at: string | null;
  approved_by: number | null;
  version: number;
  previous_version: string | null;
  is_current_version: boolean;
};
export type ProcessStep = {
  id: number;
  step: Step;
  /**
   * Position of this step within the process flow
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  order: number;
  is_entry_point?: /**
   * If True, this is the starting step for new parts
   */
  boolean | undefined;
};
export type Step = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  description?: (string | null) | undefined;
  part_type: string;
  part_type_name: string;
  expected_duration?: (string | null) | undefined;
  requires_qa_signoff?: boolean | undefined;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
  block_on_quarantine?: boolean | undefined;
  pass_threshold?: number | undefined;
  step_type?: /**
     * Visual type for flow editor.
    
    * `task` - Task
    * `start` - Start
    * `decision` - Decision
    * `rework` - Rework
    * `timer` - Timer/Wait
    * `terminal` - Terminal
     */
  StepTypeEnum | undefined;
  is_decision_point?: boolean | undefined;
  decision_type?: (DecisionTypeEnum | BlankEnum) | undefined;
  is_terminal?: boolean | undefined;
  terminal_status?: (TerminalStatusEnum | BlankEnum) | undefined;
  max_visits?:
    | /**
     * Max times a part can visit this step. Null = unlimited.
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  revisit_assignment?: RevisitAssignmentEnum | undefined;
};
export type StepTypeEnum =
  /**
   * * `task` - Task
   * `start` - Start
   * `decision` - Decision
   * `rework` - Rework
   * `timer` - Timer/Wait
   * `terminal` - Terminal
   *
   * @enum task, start, decision, rework, timer, terminal
   */
  "task" | "start" | "decision" | "rework" | "timer" | "terminal";
export type DecisionTypeEnum =
  /**
   * * `qa_result` - Based on QA Pass/Fail
   * `measurement` - Based on Measurement Threshold
   * `manual` - Manual Operator Selection
   *
   * @enum qa_result, measurement, manual
   */
  "qa_result" | "measurement" | "manual";
export type TerminalStatusEnum =
  /**
   * * `completed` - Completed Successfully
   * `shipped` - Shipped to Customer
   * `stock` - Put into Inventory
   * `scrapped` - Scrapped
   * `returned` - Returned to Supplier
   * `awaiting_pickup` - Awaiting Customer Pickup
   * `core_banked` - Core Banked
   * `rma_closed` - RMA Closed
   *
   * @enum completed, shipped, stock, scrapped, returned, awaiting_pickup, core_banked, rma_closed
   */
  | "completed"
  | "shipped"
  | "stock"
  | "scrapped"
  | "returned"
  | "awaiting_pickup"
  | "core_banked"
  | "rma_closed";
export type RevisitAssignmentEnum =
  /**
   * * `any` - Any Qualified Operator
   * `same` - Same as Previous
   * `different` - Different Operator
   * `role` - Specific Role
   *
   * @enum any, same, different, role
   */
  "any" | "same" | "different" | "role";
export type StepEdge = {
  id: number;
  from_step: string;
  to_step: string;
  edge_type?: EdgeTypeEnum | undefined;
  from_step_name: string;
  to_step_name: string;
  condition_measurement?:
    | /**
     * Optional: measurement that triggers this edge
     */
    (string | null)
    | undefined;
  condition_operator?: (ConditionOperatorEnum | BlankEnum) | undefined;
  condition_value?:
    | /**
     * Threshold value for measurement-based routing
     *
     * @pattern ^-?\d{0,6}(?:\.\d{0,4})?$
     */
    (string | null)
    | undefined;
};
export type EdgeTypeEnum =
  /**
   * * `default` - Default/Pass
   * `alternate` - Alternate/Fail
   * `escalation` - Escalation
   *
   * @enum default, alternate, escalation
   */
  "default" | "alternate" | "escalation";
export type ConditionOperatorEnum =
  /**
   * * `gte` - >= (greater or equal)
   * `lte` - <= (less or equal)
   * `eq` - = (equal)
   *
   * @enum gte, lte, eq
   */
  "gte" | "lte" | "eq";
export type ProcessStatusEnum =
  /**
   * * `draft` - Draft
   * `pending_approval` - Pending Approval
   * `approved` - Approved
   * `deprecated` - Deprecated
   *
   * @enum draft, pending_approval, approved, deprecated
   */
  "draft" | "pending_approval" | "approved" | "deprecated";
export type PaginatedProcessesList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Processes>;
};
export type Processes = {
  id: string;
  part_type_name: string;
  process_steps: Array<ProcessStep>;
  step_edges: Array<StepEdge>;
  external_id?:
    | /**
     * External system identifier for integration sync
     *
     * @maxLength 255
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_current_version?: boolean | undefined;
  /**
   * @maxLength 50
   */
  name: string;
  is_remanufactured?: boolean | undefined;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
  status?: /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  ProcessStatusEnum | undefined;
  change_description?:
    | /**
     * Description of changes from previous version (for approval review)
     */
    (string | null)
    | undefined;
  approved_at?: (string | null) | undefined;
  tenant?:
    | /**
     * Tenant this record belongs to
     */
    (string | null)
    | undefined;
  previous_version?: (string | null) | undefined;
  part_type: string;
  approved_by?: (number | null) | undefined;
};
export type PaginatedQualityErrorsListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<QualityErrorsList>;
};
export type QualityErrorsList = {
  id: string;
  /**
   * @maxLength 50
   */
  error_name: string;
  error_example: string;
  part_type?: (string | null) | undefined;
  part_type_name: string;
  requires_3d_annotation?: boolean | undefined;
  archived?: boolean | undefined;
};
export type PaginatedQualityReportsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<QualityReports>;
};
export type QualityReports = {
  id: string;
  /**
   * Auto-generated: QR-YYYY-######
   */
  report_number: string;
  step?: (string | null) | undefined;
  part?: (string | null) | undefined;
  machine?: (string | null) | undefined;
  operators?: /**
   * Operators running the process when defect occurred (for root cause)
   */
  Array<number> | undefined;
  sampling_method?: /**
   * @maxLength 50
   */
  string | undefined;
  status: QualityReportStatusEnum;
  status_display: string;
  description?:
    | /**
     * @maxLength 300
     */
    (string | null)
    | undefined;
  file?: (string | null) | undefined;
  created_at: string;
  errors: Array<string>;
  sampling_audit_log?:
    | /**
     * Links to the sampling decision that triggered this inspection
     */
    (string | null)
    | undefined;
  detected_by?:
    | /**
     * Inspector/operator who detected the defect (required for new reports)
     */
    (number | null)
    | undefined;
  detected_by_info: {};
  verified_by?:
    | /**
     * Second signature for critical inspections (aerospace/medical)
     */
    (number | null)
    | undefined;
  verified_by_info: {};
  is_first_piece?: /**
   * If True, this inspection is a First Piece Inspection (FPI) for setup verification
   */
  boolean | undefined;
  part_info: {};
  step_info: {};
  machine_info: {};
  operators_info: Array<unknown>;
  errors_info: Array<unknown>;
  file_info: {};
  archived?: boolean | undefined;
};
export type QualityReportStatusEnum =
  /**
   * * `PASS` - Pass
   * `FAIL` - Fail
   * `PENDING` - Pending
   *
   * @enum PASS, FAIL, PENDING
   */
  "PASS" | "FAIL" | "PENDING";
export type PaginatedQuarantineDispositionList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<QuarantineDisposition>;
};
export type QuarantineDisposition = {
  id: string;
  disposition_number: string;
  current_state?: CurrentStateEnum | undefined;
  disposition_type?: (DispositionTypeEnum | BlankEnum) | undefined;
  severity?: SeverityEnum | undefined;
  severity_display: string;
  assigned_to?: (number | null) | undefined;
  description?: string | undefined;
  resolution_notes?: string | undefined;
  resolution_completed?: boolean | undefined;
  resolution_completed_by?: (number | null) | undefined;
  resolution_completed_by_name: string;
  resolution_completed_at?: (string | null) | undefined;
  containment_action?: /**
   * Immediate action taken to prevent escape
   */
  string | undefined;
  containment_completed_at?: (string | null) | undefined;
  containment_completed_by?: (number | null) | undefined;
  containment_completed_by_name: string;
  requires_customer_approval?: boolean | undefined;
  customer_approval_received?: boolean | undefined;
  customer_approval_reference?: /**
   * PO#, email reference, or approval document number
   *
   * @maxLength 100
   */
  string | undefined;
  customer_approval_date?: (string | null) | undefined;
  scrap_verified?: boolean | undefined;
  scrap_verification_method?: /**
   * How product was rendered unusable: crushed, marked, etc.
   *
   * @maxLength 100
   */
  string | undefined;
  scrap_verified_by?: (number | null) | undefined;
  scrap_verified_by_name: string;
  scrap_verified_at?: (string | null) | undefined;
  part?: (string | null) | undefined;
  step?: (string | null) | undefined;
  step_info: {};
  rework_attempt_at_step?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  rework_limit_exceeded: boolean;
  quality_reports: Array<string>;
  assignee_name: string;
  choices_data: {};
  annotation_status: {};
  can_be_completed: boolean;
  completion_blockers: Array<string>;
  archived?: boolean | undefined;
};
export type CurrentStateEnum =
  /**
   * * `OPEN` - Open
   * `IN_PROGRESS` - In Progress
   * `CLOSED` - Closed
   *
   * @enum OPEN, IN_PROGRESS, CLOSED
   */
  "OPEN" | "IN_PROGRESS" | "CLOSED";
export type DispositionTypeEnum =
  /**
   * * `REWORK` - Rework
   * `REPAIR` - Repair
   * `SCRAP` - Scrap
   * `USE_AS_IS` - Use As Is
   * `RETURN_TO_SUPPLIER` - Return to Supplier
   *
   * @enum REWORK, REPAIR, SCRAP, USE_AS_IS, RETURN_TO_SUPPLIER
   */
  "REWORK" | "REPAIR" | "SCRAP" | "USE_AS_IS" | "RETURN_TO_SUPPLIER";
export type PaginatedRcaRecordList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<RcaRecord>;
};
export type PaginatedSPCBaselineListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<SPCBaselineList>;
};
export type SPCBaselineList = {
  id: string;
  /**
   * The measurement definition this baseline applies to
   */
  measurement_definition: string;
  measurement_label: string;
  /**
     * Type of control chart (X-bar R, X-bar S, or I-MR)
    
    * `XBAR_R` - X̄-R
    * `XBAR_S` - X̄-S
    * `I_MR` - I-MR
     */
  chart_type: ChartTypeEnum;
  chart_type_display: string;
  subgroup_size?: /**
   * Number of samples per subgroup (n=2 to 25 for X-bar charts, n=1 for I-MR)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  status?: /**
     * Current status of this baseline
    
    * `ACTIVE` - Active
    * `SUPERSEDED` - Superseded
     */
  BaselineStatusEnum | undefined;
  status_display: string;
  frozen_by?:
    | /**
     * User who froze/created this baseline
     */
    (number | null)
    | undefined;
  frozen_by_name: string | null;
  /**
   * Timestamp when baseline was frozen
   */
  frozen_at: string;
  sample_count?: /**
   * Number of data points used to calculate this baseline
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
};
export type ChartTypeEnum =
  /**
   * * `XBAR_R` - X̄-R
   * `XBAR_S` - X̄-S
   * `I_MR` - I-MR
   *
   * @enum XBAR_R, XBAR_S, I_MR
   */
  "XBAR_R" | "XBAR_S" | "I_MR";
export type BaselineStatusEnum =
  /**
   * * `ACTIVE` - Active
   * `SUPERSEDED` - Superseded
   *
   * @enum ACTIVE, SUPERSEDED
   */
  "ACTIVE" | "SUPERSEDED";
export type PaginatedSamplingRuleList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<SamplingRule>;
};
export type SamplingRule = {
  id: string;
  rule_type: RuleTypeEnum;
  rule_type_display: string;
  value?:
    | /**
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  order?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  algorithm_description?: /**
   * Description of sampling algorithm for audit purposes
   */
  string | undefined;
  last_validated?: (string | null) | undefined;
  ruleset: string;
  ruleset_info: {};
  created_by?: (number | null) | undefined;
  created_at: string;
  modified_by?: (number | null) | undefined;
  updated_at: string;
  ruletype_name: string;
  ruleset_name: string;
  archived?: boolean | undefined;
};
export type RuleTypeEnum =
  /**
   * * `every_nth_part` - Every Nth Part
   * `percentage` - Percentage of Parts
   * `random` - Pure Random
   * `first_n_parts` - First N Parts
   * `last_n_parts` - Last N Parts
   * `exact_count` - Exact Count (No Variance)
   *
   * @enum every_nth_part, percentage, random, first_n_parts, last_n_parts, exact_count
   */
  | "every_nth_part"
  | "percentage"
  | "random"
  | "first_n_parts"
  | "last_n_parts"
  | "exact_count";
export type PaginatedSamplingRuleSetList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<SamplingRuleSet>;
};
export type SamplingRuleSet = {
  id: string;
  /**
   * @maxLength 100
   */
  name: string;
  origin?: /**
   * @maxLength 100
   */
  string | undefined;
  active?: boolean | undefined;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_fallback?: boolean | undefined;
  fallback_threshold?:
    | /**
     * Number of consecutive failures before switching to fallback
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  fallback_duration?:
    | /**
     * Number of good parts required before reverting to this ruleset
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  part_type: string;
  part_type_info: {};
  process?:
    | /**
     * Optional process context. Steps can be in multiple processes.
     */
    (string | null)
    | undefined;
  process_info: {};
  step: string;
  step_info: {};
  rules: Array<unknown>;
  created_by?: (number | null) | undefined;
  created_at: string;
  modified_by?: (number | null) | undefined;
  updated_at: string;
  part_type_name: string;
  process_name: string;
  archived?: boolean | undefined;
};
export type PaginatedScheduleSlotList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ScheduleSlot>;
};
export type ScheduleSlot = {
  id: string;
  work_center: string;
  work_center_name: string;
  shift: string;
  shift_name: string;
  work_order: string;
  work_order_erp_id: string;
  scheduled_date: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start?: (string | null) | undefined;
  actual_end?: (string | null) | undefined;
  status?: ScheduleSlotStatusEnum | undefined;
  notes?: string | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type ScheduleSlotStatusEnum =
  /**
   * * `scheduled` - Scheduled
   * `in_progress` - In Progress
   * `completed` - Completed
   * `cancelled` - Cancelled
   *
   * @enum scheduled, in_progress, completed, cancelled
   */
  "scheduled" | "in_progress" | "completed" | "cancelled";
export type PaginatedShiftList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Shift>;
};
export type Shift = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  /**
   * @maxLength 10
   */
  code: string;
  start_time: string;
  end_time: string;
  days_of_week?: /**
   * Comma-separated day numbers (0=Monday, 6=Sunday)
   *
   * @maxLength 20
   */
  string | undefined;
  is_active?: boolean | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedStepDistributionResponseList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<StepDistributionResponse>;
};
export type StepDistributionResponse = {
  id: string;
  count: number;
  name: string;
};
export type PaginatedStepExecutionList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<StepExecution>;
};
export type StepExecution = {
  id: string;
  /**
   * The part being tracked through this step
   */
  part: string;
  /**
   * The step being executed
   */
  step: string;
  visit_number?: /**
   * Which visit this is (1st, 2nd, 3rd time at this step)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  part_info: {};
  step_info: {};
  entered_at: string;
  exited_at?: (string | null) | undefined;
  duration_seconds: number | null;
  assigned_to?:
    | /**
     * Operator assigned to this step execution
     */
    (number | null)
    | undefined;
  assigned_to_info: {};
  completed_by?:
    | /**
     * Operator who completed this step
     */
    (number | null)
    | undefined;
  completed_by_info: {};
  next_step?:
    | /**
     * The step this part moved to (for audit trail)
     */
    (string | null)
    | undefined;
  decision_result?: /**
   * Result of decision: 'pass', 'fail', measurement value, etc.
   *
   * @maxLength 50
   */
  string | undefined;
  status?: StepExecutionStatusEnum | undefined;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type StepExecutionStatusEnum =
  /**
   * * `pending` - Pending
   * `in_progress` - In Progress
   * `completed` - Completed
   * `skipped` - Skipped
   *
   * @enum pending, in_progress, completed, skipped
   */
  "pending" | "in_progress" | "completed" | "skipped";
export type PaginatedStepExecutionListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<StepExecutionList>;
};
export type StepExecutionList = {
  id: string;
  /**
   * The part being tracked through this step
   */
  part: string;
  part_erp_id: string;
  part_status: string;
  /**
   * The step being executed
   */
  step: string;
  step_name: string;
  step_order: number | null;
  visit_number?: /**
   * Which visit this is (1st, 2nd, 3rd time at this step)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  entered_at: string;
  exited_at?: (string | null) | undefined;
  status?: StepExecutionStatusEnum | undefined;
  assigned_to?:
    | /**
     * Operator assigned to this step execution
     */
    (number | null)
    | undefined;
  assigned_to_name: string | null;
  decision_result?: /**
   * Result of decision: 'pass', 'fail', measurement value, etc.
   *
   * @maxLength 50
   */
  string | undefined;
};
export type PaginatedStepsList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Steps>;
};
export type Steps = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  expected_duration?: (string | null) | undefined;
  description?: (string | null) | undefined;
  block_on_quarantine?: boolean | undefined;
  requires_qa_signoff?: boolean | undefined;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
  pass_threshold?: number | undefined;
  requires_first_piece_inspection?: /**
   * If True, first part of each work order at this step requires FPI before others can proceed
   */
  boolean | undefined;
  part_type: string;
  part_type_info: {};
  part_type_name: string | null;
  step_type?: /**
     * Visual type for flow editor.
    
    * `task` - Task
    * `start` - Start
    * `decision` - Decision
    * `rework` - Rework
    * `timer` - Timer/Wait
    * `terminal` - Terminal
     */
  StepTypeEnum | undefined;
  is_decision_point?: boolean | undefined;
  decision_type?: (DecisionTypeEnum | BlankEnum) | undefined;
  is_terminal?: boolean | undefined;
  terminal_status?: (TerminalStatusEnum | BlankEnum) | undefined;
  max_visits?:
    | /**
     * Max times a part can visit this step. Null = unlimited.
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  revisit_assignment?: RevisitAssignmentEnum | undefined;
  revisit_role?:
    | /**
     * Required role when revisit_assignment='role'
     */
    (number | null)
    | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedTenantGroupList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<TenantGroup>;
};
export type TenantGroup = {
  id: string;
  /**
   * Display name
   *
   * @maxLength 100
   */
  name: string;
  description?: string | undefined;
  /**
   * True if created by tenant admin, False if seeded from presets
   */
  is_custom: boolean;
  permission_count: number;
  member_count: number;
  preset_key: string | null;
  created_at: string;
  updated_at: string;
};
export type PaginatedTenantList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<Tenant>;
};
export type Tenant = {
  id: string;
  /**
   * Display name of the organization
   *
   * @maxLength 100
   */
  name: string;
  /**
   * URL-safe identifier, immutable after creation
   *
   * @maxLength 50
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier?: TierEnum | undefined;
  status?: TenantStatusEnum | undefined;
  is_active?: boolean | undefined;
  is_demo?: /**
   * Demo tenant with reset capability
   */
  boolean | undefined;
  trial_ends_at?:
    | /**
     * Trial expiration date
     */
    (string | null)
    | undefined;
  created_at: string;
  updated_at: string;
  settings?: /**
   * Tenant-specific configuration
   */
  unknown | undefined;
  user_count: number;
  logo?:
    | /**
     * Organization logo (recommended: 200x200 PNG)
     */
    (string | null)
    | undefined;
  logo_url: string | null;
  contact_email?: /**
   * Primary contact email for the organization
   *
   * @maxLength 254
   */
  string | undefined;
  contact_phone?: /**
   * Primary contact phone number
   *
   * @maxLength 30
   */
  string | undefined;
  website?: /**
   * Organization website URL
   *
   * @maxLength 200
   */
  string | undefined;
  address?: /**
   * Organization mailing address
   */
  string | undefined;
  default_timezone?: /**
   * Default timezone for the organization (IANA format, e.g., 'America/New_York')
   *
   * @maxLength 50
   */
  string | undefined;
};
export type TierEnum =
  /**
   * * `starter` - Starter
   * `pro` - Pro
   * `enterprise` - Enterprise
   *
   * @enum starter, pro, enterprise
   */
  "starter" | "pro" | "enterprise";
export type TenantStatusEnum =
  /**
   * * `active` - Active
   * `trial` - Trial
   * `suspended` - Suspended
   * `pending_deletion` - Pending Deletion
   *
   * @enum active, trial, suspended, pending_deletion
   */
  "active" | "trial" | "suspended" | "pending_deletion";
export type PaginatedThreeDModelList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<ThreeDModel>;
};
export type ThreeDModel = {
  id: string;
  /**
   * @maxLength 255
   */
  name: string;
  file: string;
  part_type: string;
  part_type_display: string;
  step?: (string | null) | undefined;
  step_display: string;
  uploaded_at: string;
  /**
   * Output format after processing (always 'glb')
   */
  file_type: string;
  annotation_count: number;
  /**
     * Current processing state
    
    * `pending` - Pending
    * `processing` - Processing
    * `completed` - Completed
    * `failed` - Failed
     */
  processing_status: ProcessingStatusEnum;
  /**
   * Error message if processing failed
   */
  processing_error: string;
  /**
   * When processing completed
   */
  processed_at: string | null;
  is_ready: boolean;
  processing_metrics: {};
  /**
   * Original uploaded filename
   */
  original_filename: string;
  /**
   * Original file format (e.g., 'step', 'stl', 'obj')
   */
  original_format: string;
  /**
   * Original file size in bytes
   */
  original_size_bytes: number | null;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
  deleted_at: string | null;
};
export type ProcessingStatusEnum =
  /**
   * * `pending` - Pending
   * `processing` - Processing
   * `completed` - Completed
   * `failed` - Failed
   *
   * @enum pending, processing, completed, failed
   */
  "pending" | "processing" | "completed" | "failed";
export type PaginatedTimeEntryList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<TimeEntry>;
};
export type TimeEntry = {
  id: string;
  entry_type: TimeEntryTypeEnum;
  start_time: string;
  end_time?: (string | null) | undefined;
  user: number;
  user_name: string;
  duration_hours: number | null;
  part?: (string | null) | undefined;
  part_erp_id: string | null;
  work_order?: (string | null) | undefined;
  work_order_erp_id: string | null;
  step?: (string | null) | undefined;
  equipment?: (string | null) | undefined;
  work_center?: (string | null) | undefined;
  notes?: string | undefined;
  downtime_reason?: /**
   * @maxLength 100
   */
  string | undefined;
  approved?: boolean | undefined;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedTrainingRecordList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<TrainingRecord>;
};
export type TrainingRecord = {
  id: string;
  user: number;
  user_info: {};
  training_type: string;
  training_type_info: {};
  completed_date: string;
  expires_date?:
    | /**
     * Date training expires. Null = never expires.
     */
    (string | null)
    | undefined;
  trainer?:
    | /**
     * Person who conducted the training
     */
    (number | null)
    | undefined;
  trainer_info: {};
  notes?: string | undefined;
  status: string;
  is_current: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedTrainingRequirementList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<TrainingRequirement>;
};
export type TrainingRequirement = {
  id: string;
  training_type: string;
  training_type_info: {};
  step?: (string | null) | undefined;
  step_info: {};
  process?: (string | null) | undefined;
  process_info: {};
  equipment_type?: (string | null) | undefined;
  equipment_type_info: {};
  notes?: /**
   * Why is this required? e.g., 'Per WI-042' or 'Customer requirement'
   */
  string | undefined;
  scope: string;
  scope_display: string;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedTrainingTypeList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<TrainingType>;
};
export type TrainingType = {
  id: string;
  /**
   * @maxLength 100
   */
  name: string;
  description?: string | undefined;
  validity_period_days?:
    | /**
     * Default number of days training is valid. Null = never expires.
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedUserInvitationList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<UserInvitation>;
};
export type UserInvitation = {
  id: number;
  user: number;
  user_email: string;
  user_name: string;
  invited_by?: (number | null) | undefined;
  invited_by_name: string;
  sent_at: string;
  expires_at: string;
  accepted_at: string | null;
  is_expired: boolean;
  is_valid: boolean;
  accepted_ip_address: string | null;
  accepted_user_agent: string | null;
  invitation_url: string;
};
export type PaginatedUserList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<User>;
};
export type User = {
  id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   *
   * @maxLength 150
   * @pattern ^[\w.@+-]+$
   */
  username: string;
  first_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  last_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  email?: /**
   * @maxLength 254
   */
  string | undefined;
  full_name: string;
  is_staff?: /**
   * Designates whether the user can log into this admin site.
   */
  boolean | undefined;
  is_active?: /**
   * Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
   */
  boolean | undefined;
  date_joined: string;
  parent_company: Company;
  groups: Array<{}>;
};
export type PaginatedUserSelectList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<UserSelect>;
};
export type UserSelect = {
  id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   */
  username: string;
  first_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  last_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  email?: /**
   * @maxLength 254
   */
  string | undefined;
  full_name: string;
  /**
   * Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
   */
  is_active: boolean;
};
export type PaginatedWIPSummaryList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<WIPSummary>;
};
export type WIPSummary = {
  step_id: string;
  step_name: string;
  step_order: number;
  is_decision_point: boolean;
  pending_count: number;
  in_progress_count: number;
  total_active: number;
};
export type PaginatedWorkCenterList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<WorkCenter>;
};
export type WorkCenter = {
  id: string;
  /**
   * @maxLength 100
   */
  name: string;
  /**
   * @maxLength 20
   */
  code: string;
  description?: string | undefined;
  capacity_units?: /**
   * Unit of measure for capacity (hours, pieces, etc.)
   *
   * @maxLength 20
   */
  string | undefined;
  default_efficiency?: /**
   * Default efficiency percentage (100 = 100%)
   *
   * @pattern ^-?\d{0,3}(?:\.\d{0,2})?$
   */
  string | undefined;
  equipment?: Array<string> | undefined;
  equipment_names: Array<string>;
  cost_center?: /**
   * @maxLength 50
   */
  string | undefined;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type PaginatedWorkOrderListList = {
  /**
   * @example 123
   */
  count: number;
  next?:
    | /**
     * @example "http://api.example.org/accounts/?offset=400&limit=100"
     */
    (string | null)
    | undefined;
  previous?:
    | /**
     * @example "http://api.example.org/accounts/?offset=200&limit=100"
     */
    (string | null)
    | undefined;
  results: Array<WorkOrderList>;
};
export type WorkOrderList = {
  id: string;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status?: WorkOrderStatusEnum | undefined;
  priority?: /**
     * Work order priority. Lower number = higher priority for scheduling.
    
    * `1` - Urgent
    * `2` - High
    * `3` - Normal
    * `4` - Low
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
  PriorityEnum | undefined;
  quantity?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  related_order?: (string | null) | undefined;
  related_order_info: {};
  process?: (string | null) | undefined;
  process_info: {};
  expected_completion?: (string | null) | undefined;
  true_completion?: (string | null) | undefined;
  expected_duration?: (string | null) | undefined;
  true_duration?: (string | null) | undefined;
  notes?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  parts_count: number;
  qa_progress: {};
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type WorkOrderStatusEnum =
  /**
   * * `PENDING` - Pending
   * `IN_PROGRESS` - In progress
   * `COMPLETED` - Completed
   * `ON_HOLD` - On hold
   * `CANCELLED` - Cancelled
   * `WAITING_FOR_OPERATOR` - Waiting for operator
   *
   * @enum PENDING, IN_PROGRESS, COMPLETED, ON_HOLD, CANCELLED, WAITING_FOR_OPERATOR
   */
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "ON_HOLD"
  | "CANCELLED"
  | "WAITING_FOR_OPERATOR";
export type PriorityEnum =
  /**
   * * `1` - Urgent
   * `2` - High
   * `3` - Normal
   * `4` - Low
   *
   * @enum 1, 2, 3, 4
   */
  1 | 2 | 3 | 4;
export type PartTravelerResponse = {
  part_id: string;
  part_erp_id: string;
  work_order_id: string | null;
  process_name: string | null;
  current_step_id: string | null;
  current_step_name: string | null;
  part_status: string;
  traveler: Array<TravelerStepEntry>;
};
export type TravelerStepEntry = {
  step_id: string;
  step_name: string;
  step_order: number;
  visit_number?: /**
   * @default 1
   */
  number | undefined;
  status: TravelerStepStatusEnum;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  operator: TravelerOperator;
  approved_by: TravelerApproval;
  equipment_used: Array<TravelerEquipment>;
  measurements: Array<TravelerMeasurement>;
  quality_status: QualityStatusEnum | NullEnum | null;
  defects_found: Array<TravelerDefect>;
  materials_used: Array<TravelerMaterial>;
  attachments: Array<TravelerAttachment>;
};
export type TravelerStepStatusEnum =
  /**
   * * `COMPLETED` - COMPLETED
   * `IN_PROGRESS` - IN_PROGRESS
   * `PENDING` - PENDING
   * `SKIPPED` - SKIPPED
   *
   * @enum COMPLETED, IN_PROGRESS, PENDING, SKIPPED
   */
  "COMPLETED" | "IN_PROGRESS" | "PENDING" | "SKIPPED";
export type TravelerOperator = {
  id: number;
  name: string;
  employee_id: string | null;
};
export type TravelerApproval = {
  id: number;
  name: string;
  approved_at: string;
};
export type TravelerEquipment = {
  id: string;
  name: string;
  calibration_due: string | null;
};
export type TravelerMeasurement = {
  definition_id: string;
  label: string;
  nominal: number | null;
  upper_tol: number | null;
  lower_tol: number | null;
  actual_value: number | null;
  unit: string | null;
  passed: boolean;
  recorded_at: string;
  recorded_by: string | null;
};
export type QualityStatusEnum =
  /**
   * * `PASS` - PASS
   * `FAIL` - FAIL
   * `CONDITIONAL` - CONDITIONAL
   *
   * @enum PASS, FAIL, CONDITIONAL
   */
  "PASS" | "FAIL" | "CONDITIONAL";
export type TravelerDefect = {
  error_type_id: string | null;
  error_name: string;
  severity: string | null;
  disposition: string | null;
};
export type TravelerMaterial = {
  material_name: string;
  lot_number: string | null;
  quantity: number;
};
export type TravelerAttachment = {
  id: string;
  file_name: string;
  file_url: string;
  uploaded_at: string;
  classification: string | null;
};
export type PartsRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  part_status?: PartsStatusEnum | undefined;
  order?: string | undefined;
  part_type: string;
  step: string;
  work_order?: (string | null) | undefined;
  sampling_rule?: (string | null) | undefined;
  sampling_ruleset?: (string | null) | undefined;
  sampling_context?: unknown | undefined;
  archived?: boolean | undefined;
};
export type PatchedApprovalRequestRequest = Partial<{
  content_type: number | null;
  /**
   * @maxLength 36
   */
  object_id: string | null;
  requested_by: number | null;
  reason: string | null;
  notes: string | null;
  status: ApprovalStatusEnum;
  approval_type: ApprovalTypeEnum;
  flow_type: ApprovalFlowTypeEnum;
  sequence_type: ApprovalSequenceEnum;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  threshold: number | null;
  delegation_policy: DelegationPolicyEnum;
  /**
   * Specific date when escalation should trigger
   */
  escalation_day: string | null;
  escalate_to: number | null;
  due_date: string | null;
}>;
export type PatchedApprovalResponseRequest = Partial<{
  approval_request: string;
  approver: number;
  decision: DecisionEnum;
  comments: string | null;
  /**
   * Base64 encoded signature image (PNG)
   */
  signature_data: string | null;
  /**
   * e.g., 'I approve as QA Manager'
   *
   * @maxLength 200
   */
  signature_meaning: string | null;
  verification_method: VerificationMethodEnum;
  delegated_to: number | null;
  archived: boolean;
}>;
export type PatchedApprovalTemplateRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 100
   */
  template_name: string;
  approval_type: ApprovalTypeEnum;
  default_groups: Array<string>;
  default_approvers: Array<number>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  default_threshold: number | null;
  /**
   * Group name to auto-assign (e.g., 'QA_Manager')
   *
   * @maxLength 50
   */
  auto_assign_by_role: string | null;
  approval_flow_type: ApprovalFlowTypeEnum;
  delegation_policy: DelegationPolicyEnum;
  approval_sequence: ApprovalSequenceEnum;
  /**
   * Allow requesters to approve their own requests (requires justification)
   */
  allow_self_approval: boolean;
  /**
   * Days until due date
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  default_due_days: number;
  /**
   * Days before escalation triggers
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  escalation_days: number | null;
  escalate_to: number | null;
  /**
   * Null = currently active
   */
  deactivated_at: string | null;
  archived: boolean;
}>;
export type PatchedBOMRequest = Partial<{
  part_type: string;
  /**
   * @minLength 1
   * @maxLength 10
   */
  revision: string;
  bom_type: BOMTypeEnum;
  status: BOMStatusEnum;
  description: string;
  archived: boolean;
}>;
export type PatchedCAPARequest = Partial<{
  capa_type: CapaTypeEnum;
  severity: SeverityEnum;
  /**
   * Clear description of the problem
   *
   * @minLength 1
   */
  problem_statement: string;
  /**
   * Containment action taken immediately
   */
  immediate_action: string | null;
  initiated_by: number | null;
  assigned_to: number | null;
  /**
   * User-set due date
   */
  due_date: string | null;
  verified_by: number | null;
  /**
     * Approval workflow status
    
    * `NOT_REQUIRED` - Not Required
    * `PENDING` - Pending
    * `APPROVED` - Approved
    * `REJECTED` - Rejected
     */
  approval_status: ApprovalStatusEnum;
  /**
   * Allow initiator/assignee to verify their own CAPA (requires justification)
   */
  allow_self_verification: boolean;
  /**
   * Representative part if applicable
   */
  part: string | null;
  /**
   * Process step where issue occurred
   */
  step: string | null;
  work_order: string | null;
  quality_reports: Array<string>;
  dispositions: Array<string>;
}>;
export type PatchedCalibrationRecordRequest = Partial<{
  equipment: string;
  calibration_date: string;
  due_date: string;
  result: ResultEnum;
  calibration_type: CalibrationTypeEnum;
  /**
   * Person or lab that performed calibration
   *
   * @maxLength 200
   */
  performed_by: string;
  /**
   * External calibration lab name if sent out
   *
   * @maxLength 200
   */
  external_lab: string;
  /**
   * Calibration certificate number for traceability
   *
   * @maxLength 100
   */
  certificate_number: string;
  /**
   * Reference standards used with traceability info (e.g., 'NIST-traceable gauge blocks, cert #12345')
   */
  standards_used: string;
  /**
   * Was equipment within tolerance when received for calibration?
   */
  as_found_in_tolerance: boolean | null;
  /**
   * Were adjustments made during calibration?
   */
  adjustments_made: boolean;
  notes: string;
  archived: boolean;
}>;
export type PatchedCapaTasksRequest = Partial<{
  capa: string;
  task_type: TaskTypeEnum;
  /**
   * @minLength 1
   */
  description: string;
  assigned_to: number | null;
  completion_mode: CompletionModeEnum;
  due_date: string | null;
  /**
   * If true, task completion requires signature and password verification
   */
  requires_signature: boolean;
  status: CapaTaskStatusEnum;
  completion_notes: string | null;
  archived: boolean;
}>;
export type PatchedCapaVerificationRequest = Partial<{
  capa: string;
  /**
   * How effectiveness was verified
   *
   * @minLength 1
   */
  verification_method: string;
  /**
   * What defines success
   *
   * @minLength 1
   */
  verification_criteria: string;
  verification_date: string | null;
  verified_by: number | null;
  effectiveness_result: EffectivenessResultEnum;
  verification_notes: string | null;
  archived: boolean;
}>;
export type PatchedCoreRequest = Partial<{
  /**
   * Unique identifier for this core unit (unique per tenant)
   *
   * @minLength 1
   * @maxLength 100
   */
  core_number: string;
  /**
   * Original equipment serial number if available
   *
   * @maxLength 100
   */
  serial_number: string;
  /**
   * Type of unit (e.g., Fuel Injector, Turbocharger)
   */
  core_type: string;
  received_date: string;
  /**
   * Customer who returned this core
   */
  customer: string | null;
  source_type: SourceTypeEnum;
  /**
   * RMA number, PO number, or other reference
   *
   * @maxLength 100
   */
  source_reference: string;
  /**
     * Overall condition grade assigned at receipt
    
    * `A` - Grade A - Excellent
    * `B` - Grade B - Good
    * `C` - Grade C - Fair
    * `SCRAP` - Scrap - Not Usable
     */
  condition_grade: ConditionGradeEnum;
  /**
   * Detailed notes on condition observed at receipt
   */
  condition_notes: string;
  status: CoreStatusEnum;
  /**
   * Credit value to be issued for this core
   *
   * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
   */
  core_credit_value: string | null;
  /**
   * Whether core credit has been issued to customer
   */
  core_credit_issued: boolean;
  work_order: string | null;
  archived: boolean;
}>;
export type PatchedDocumentsRequest = Partial<{
  /**
     * Security classification level for document access control
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
  classification: ClassificationEnum | NullEnum | null;
  ai_readable: boolean;
  is_image: boolean;
  /**
   * @minLength 1
   * @maxLength 50
   */
  file_name: string;
  file: string;
  uploaded_by: number | null;
  /**
   * Model of the object this document relates to
   */
  content_type: number | null;
  /**
   * ID of the object this document relates to (CharField for UUID compatibility)
   *
   * @maxLength 36
   */
  object_id: string | null;
  /**
   * @minimum 0
   * @maximum 2147483647
   */
  version: number;
  /**
     * Document workflow status
    
    * `DRAFT` - Draft
    * `UNDER_REVIEW` - Under Review
    * `APPROVED` - Approved
    * `RELEASED` - Released
    * `OBSOLETE` - Obsolete
     */
  status: DocumentsStatusEnum;
  /**
   * Type/category of document (e.g., SOP, Work Instruction)
   */
  document_type: string | null;
  /**
   * @minLength 1
   */
  document_type_code: string;
  /**
   * Reason for this revision (required when creating new versions)
   */
  change_justification: string;
  /**
   * Document contains ITAR-controlled technical data (22 CFR 120-130)
   */
  itar_controlled: boolean;
  /**
   * Export Control Classification Number (e.g., EAR99, 3A001, 9A004.a)
   *
   * @maxLength 20
   */
  eccn: string;
  /**
   * Reason for export control classification (e.g., 'Contains defense article specs')
   *
   * @maxLength 100
   */
  export_control_reason: string;
}>;
export type PatchedDowntimeEventRequest = Partial<{
  equipment: string | null;
  work_center: string | null;
  category: DowntimeCategoryEnum;
  /**
   * @minLength 1
   * @maxLength 200
   */
  reason: string;
  description: string;
  start_time: string;
  end_time: string | null;
  work_order: string | null;
  archived: boolean;
}>;
export type PatchedEquipmentsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  equipment_type: string | null;
  /**
   * @maxLength 100
   */
  serial_number: string;
  /**
   * @maxLength 100
   */
  manufacturer: string;
  /**
   * @maxLength 100
   */
  model_number: string;
  /**
   * @maxLength 100
   */
  location: string;
  status: EquipmentsStatusEnum;
  notes: string;
  archived: boolean;
}>;
export type PatchedHarvestedComponentRequest = Partial<{
  core: string;
  component_type: string;
  condition_grade: ConditionGradeEnum;
  condition_notes: string;
  /**
   * Position within core (e.g., 'Cyl 1', 'Position A')
   *
   * @maxLength 50
   */
  position: string;
  /**
   * Original part number if readable
   *
   * @maxLength 100
   */
  original_part_number: string;
  archived: boolean;
}>;
export type PatchedHeatMapAnnotationsRequest = Partial<{
  model: string;
  part: string;
  position_x: number;
  position_y: number;
  position_z: number;
  measurement_value: number | null;
  /**
   * @maxLength 255
   */
  defect_type: string | null;
  severity: HeatMapAnnotationsSeverityEnum | BlankEnum | NullEnum | null;
  notes: string;
  quality_reports: Array<string>;
  archived: boolean;
}>;
export type PatchedMaterialLotRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 100
   */
  lot_number: string;
  parent_lot: string | null;
  material_type: string | null;
  /**
   * Description for raw materials not tracked as PartTypes
   *
   * @maxLength 200
   */
  material_description: string;
  supplier: string | null;
  /**
   * Supplier's lot/batch number
   *
   * @maxLength 100
   */
  supplier_lot_number: string;
  received_date: string;
  /**
   * @pattern ^-?\d{0,8}(?:\.\d{0,4})?$
   */
  quantity: string;
  /**
   * @minLength 1
   * @maxLength 20
   */
  unit_of_measure: string;
  status: MaterialLotStatusEnum;
  manufacture_date: string | null;
  expiration_date: string | null;
  certificate_of_conformance: string | null;
  /**
   * @maxLength 100
   */
  storage_location: string;
  archived: boolean;
}>;
export type PatchedMeasurementDefinitionRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 100
   */
  label: string;
  /**
   * @maxLength 50
   */
  unit: string;
  /**
   * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
   */
  nominal: string | null;
  /**
   * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
   */
  upper_tol: string | null;
  /**
   * @pattern ^-?\d{0,3}(?:\.\d{0,6})?$
   */
  lower_tol: string | null;
  required: boolean;
  type: TypeEnum;
  archived: boolean;
}>;
export type PatchedNotificationPreferenceRequest = Partial<{
  notification_type: NotificationTypeEnum;
  channel_type: ChannelTypeEnum;
  schedule: NotificationScheduleRequest;
  /**
   * Max sends before stopping. Null = infinite
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  max_attempts: number | null;
}>;
export type PatchedOrdersRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 200
   */
  name: string;
  customer_note: string | null;
  customer: number | null;
  company: string | null;
  estimated_completion: string | null;
  order_status: OrdersStatusEnum;
  current_hubspot_gate: string | null;
  archived: boolean;
}>;
export type PatchedPartsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  part_status: PartsStatusEnum;
  order: string;
  part_type: string;
  step: string;
  work_order: string | null;
  sampling_rule: string | null;
  sampling_ruleset: string | null;
  sampling_context: unknown;
  archived: boolean;
}>;
export type PatchedProcessWithStepsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  part_type: string;
  /**
   * If True, UI treats work order parts as a batch unit
   */
  is_batch_process: boolean;
  nodes: Array<{}>;
  edges: Array<{}>;
  /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  status: ProcessStatusEnum;
  /**
   * Description of changes from previous version (for approval review)
   */
  change_description: string | null;
}>;
export type PatchedProcessesRequest = Partial<{
  /**
   * External system identifier for integration sync
   *
   * @maxLength 255
   */
  external_id: string | null;
  archived: boolean;
  deleted_at: string | null;
  /**
   * @minimum 0
   * @maximum 2147483647
   */
  version: number;
  is_current_version: boolean;
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  /**
   * If True, UI treats work order parts as a batch unit
   */
  is_batch_process: boolean;
  /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  status: ProcessStatusEnum;
  /**
   * Description of changes from previous version (for approval review)
   */
  change_description: string | null;
  approved_at: string | null;
  /**
   * Tenant this record belongs to
   */
  tenant: string | null;
  previous_version: string | null;
  part_type: string;
  approved_by: number | null;
}>;
export type PatchedQualityReportsRequest = Partial<{
  step: string | null;
  part: string | null;
  machine: string | null;
  /**
   * Operators running the process when defect occurred (for root cause)
   */
  operators: Array<number>;
  /**
   * @minLength 1
   * @maxLength 50
   */
  sampling_method: string;
  status: QualityReportStatusEnum;
  /**
   * @maxLength 300
   */
  description: string | null;
  file: string | null;
  measurements: Array<MeasurementResultRequest>;
  /**
   * Links to the sampling decision that triggered this inspection
   */
  sampling_audit_log: string | null;
  /**
   * Inspector/operator who detected the defect (required for new reports)
   */
  detected_by: number | null;
  /**
   * Second signature for critical inspections (aerospace/medical)
   */
  verified_by: number | null;
  /**
   * If True, this inspection is a First Piece Inspection (FPI) for setup verification
   */
  is_first_piece: boolean;
  archived: boolean;
}>;
export type PatchedQuarantineDispositionRequest = Partial<{
  current_state: CurrentStateEnum;
  disposition_type: DispositionTypeEnum | BlankEnum;
  severity: SeverityEnum;
  assigned_to: number | null;
  description: string;
  resolution_notes: string;
  resolution_completed: boolean;
  resolution_completed_by: number | null;
  resolution_completed_at: string | null;
  /**
   * Immediate action taken to prevent escape
   */
  containment_action: string;
  containment_completed_at: string | null;
  containment_completed_by: number | null;
  requires_customer_approval: boolean;
  customer_approval_received: boolean;
  /**
   * PO#, email reference, or approval document number
   *
   * @maxLength 100
   */
  customer_approval_reference: string;
  customer_approval_date: string | null;
  scrap_verified: boolean;
  /**
   * How product was rendered unusable: crushed, marked, etc.
   *
   * @maxLength 100
   */
  scrap_verification_method: string;
  scrap_verified_by: number | null;
  scrap_verified_at: string | null;
  part: string | null;
  step: string | null;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  rework_attempt_at_step: number;
  quality_reports: Array<string>;
  archived: boolean;
}>;
export type PatchedRcaRecordRequest = Partial<{
  capa: string;
  rca_method: RcaMethodEnum;
  /**
   * @minLength 1
   */
  problem_description: string;
  root_cause_summary: string | null;
  conducted_by: number | null;
  conducted_date: string | null;
  rca_review_status: RcaReviewStatusEnum;
  root_cause_verification_status: RootCauseVerificationStatusEnum;
  root_cause_verified_by: number | null;
  quality_reports: Array<string>;
  dispositions: Array<string>;
  five_whys_data: FiveWhysNestedRequest;
  fishbone_data: FishboneNestedRequest;
  archived: boolean;
}>;
export type FiveWhysNestedRequest = Partial<{
  why_1_question: string | null;
  why_1_answer: string | null;
  why_2_question: string | null;
  why_2_answer: string | null;
  why_3_question: string | null;
  why_3_answer: string | null;
  why_4_question: string | null;
  why_4_answer: string | null;
  why_5_question: string | null;
  why_5_answer: string | null;
  identified_root_cause: string | null;
}>;
export type FishboneNestedRequest = Partial<{
  problem_statement: string | null;
  man_causes: string | null;
  machine_causes: string | null;
  material_causes: string | null;
  method_causes: string | null;
  measurement_causes: string | null;
  environment_causes: string | null;
  identified_root_cause: string | null;
}>;
export type PatchedSPCBaselineRequest = Partial<{
  /**
   * The measurement definition this baseline applies to
   */
  measurement_definition: string;
  /**
     * Type of control chart (X-bar R, X-bar S, or I-MR)
    
    * `XBAR_R` - X̄-R
    * `XBAR_S` - X̄-S
    * `I_MR` - I-MR
     */
  chart_type: ChartTypeEnum;
  /**
   * Number of samples per subgroup (n=2 to 25 for X-bar charts, n=1 for I-MR)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  subgroup_size: number;
  /**
   * X-bar chart Upper Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  xbar_ucl: string | null;
  /**
   * X-bar chart Center Line (grand mean)
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  xbar_cl: string | null;
  /**
   * X-bar chart Lower Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  xbar_lcl: string | null;
  /**
   * Range (or S) chart Upper Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  range_ucl: string | null;
  /**
   * Range (or S) chart Center Line
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  range_cl: string | null;
  /**
   * Range (or S) chart Lower Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  range_lcl: string | null;
  /**
   * Individual chart Upper Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  individual_ucl: string | null;
  /**
   * Individual chart Center Line
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  individual_cl: string | null;
  /**
   * Individual chart Lower Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  individual_lcl: string | null;
  /**
   * Moving Range chart Upper Control Limit
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  mr_ucl: string | null;
  /**
   * Moving Range chart Center Line
   *
   * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
   */
  mr_cl: string | null;
  /**
     * Current status of this baseline
    
    * `ACTIVE` - Active
    * `SUPERSEDED` - Superseded
     */
  status: BaselineStatusEnum;
  /**
   * User who froze/created this baseline
   */
  frozen_by: number | null;
  /**
   * The baseline that replaced this one
   */
  superseded_by: string | null;
  /**
   * Reason for superseding this baseline
   */
  superseded_reason: string;
  /**
   * Number of data points used to calculate this baseline
   *
   * @minimum 0
   * @maximum 2147483647
   */
  sample_count: number;
  /**
   * Additional notes about this baseline
   */
  notes: string;
}>;
export type PatchedSamplingRuleRequest = Partial<{
  rule_type: RuleTypeEnum;
  /**
   * @minimum 0
   * @maximum 2147483647
   */
  value: number | null;
  /**
   * @minimum 0
   * @maximum 2147483647
   */
  order: number;
  /**
   * Description of sampling algorithm for audit purposes
   *
   * @minLength 1
   */
  algorithm_description: string;
  last_validated: string | null;
  ruleset: string;
  created_by: number | null;
  modified_by: number | null;
  archived: boolean;
}>;
export type PatchedScheduleSlotRequest = Partial<{
  work_center: string;
  shift: string;
  work_order: string;
  scheduled_date: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start: string | null;
  actual_end: string | null;
  status: ScheduleSlotStatusEnum;
  notes: string;
  archived: boolean;
}>;
export type PatchedStepExecutionRequest = Partial<{
  /**
   * The part being tracked through this step
   */
  part: string;
  /**
   * The step being executed
   */
  step: string;
  /**
   * Which visit this is (1st, 2nd, 3rd time at this step)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  visit_number: number;
  exited_at: string | null;
  /**
   * Operator assigned to this step execution
   */
  assigned_to: number | null;
  /**
   * Operator who completed this step
   */
  completed_by: number | null;
  /**
   * The step this part moved to (for audit trail)
   */
  next_step: string | null;
  /**
   * Result of decision: 'pass', 'fail', measurement value, etc.
   *
   * @maxLength 50
   */
  decision_result: string;
  status: StepExecutionStatusEnum;
  archived: boolean;
}>;
export type PatchedStepsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  expected_duration: string | null;
  description: string | null;
  block_on_quarantine: boolean;
  requires_qa_signoff: boolean;
  sampling_required: boolean;
  /**
   * Minimum % of parts that must be sampled at this step
   */
  min_sampling_rate: number;
  pass_threshold: number;
  /**
   * If True, first part of each work order at this step requires FPI before others can proceed
   */
  requires_first_piece_inspection: boolean;
  part_type: string;
  /**
     * Visual type for flow editor.
    
    * `task` - Task
    * `start` - Start
    * `decision` - Decision
    * `rework` - Rework
    * `timer` - Timer/Wait
    * `terminal` - Terminal
     */
  step_type: StepTypeEnum;
  is_decision_point: boolean;
  decision_type: DecisionTypeEnum | BlankEnum;
  is_terminal: boolean;
  terminal_status: TerminalStatusEnum | BlankEnum;
  /**
   * Max times a part can visit this step. Null = unlimited.
   *
   * @minimum 0
   * @maximum 2147483647
   */
  max_visits: number | null;
  revisit_assignment: RevisitAssignmentEnum;
  /**
   * Required role when revisit_assignment='role'
   */
  revisit_role: number | null;
  archived: boolean;
}>;
export type PatchedTenantRequest = Partial<{
  /**
   * Display name of the organization
   *
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  /**
   * URL-safe identifier, immutable after creation
   *
   * @minLength 1
   * @maxLength 50
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier: TierEnum;
  status: TenantStatusEnum;
  is_active: boolean;
  /**
   * Demo tenant with reset capability
   */
  is_demo: boolean;
  /**
   * Trial expiration date
   */
  trial_ends_at: string | null;
  /**
   * Tenant-specific configuration
   */
  settings: unknown;
  /**
   * Organization logo (recommended: 200x200 PNG)
   */
  logo: string | null;
  /**
   * Primary contact email for the organization
   *
   * @maxLength 254
   */
  contact_email: string;
  /**
   * Primary contact phone number
   *
   * @maxLength 30
   */
  contact_phone: string;
  /**
   * Organization website URL
   *
   * @maxLength 200
   */
  website: string;
  /**
   * Organization mailing address
   */
  address: string;
  /**
   * Default timezone for the organization (IANA format, e.g., 'America/New_York')
   *
   * @minLength 1
   * @maxLength 50
   */
  default_timezone: string;
}>;
export type PatchedTimeEntryRequest = Partial<{
  entry_type: TimeEntryTypeEnum;
  start_time: string;
  end_time: string | null;
  part: string | null;
  work_order: string | null;
  step: string | null;
  equipment: string | null;
  work_center: string | null;
  notes: string;
  /**
   * @maxLength 100
   */
  downtime_reason: string;
  approved: boolean;
  archived: boolean;
}>;
export type PatchedWorkOrderRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status: WorkOrderStatusEnum;
  /**
     * Work order priority. Lower number = higher priority for scheduling.
    
    * `1` - Urgent
    * `2` - High
    * `3` - Normal
    * `4` - Low
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
  priority: PriorityEnum;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  quantity: number;
  related_order: string | null;
  process: string | null;
  expected_completion: string | null;
  expected_duration: string | null;
  true_completion: string | null;
  true_duration: string | null;
  /**
   * @maxLength 500
   */
  notes: string | null;
  archived: boolean;
}>;
export type ProcessSPC = {
  id: string;
  /**
   * @maxLength 50
   */
  name: string;
  part_type_name: string;
  steps: Array<ProcessStepSPC>;
};
export type ProcessStepSPC = {
  id: string;
  name: string;
  order: number;
  measurements: Array<MeasurementDefinitionSPC>;
};
export type ProcessWithStepsRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured?: boolean | undefined;
  part_type: string;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
  nodes?: Array<{}> | undefined;
  edges?: Array<{}> | undefined;
  status?: /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  ProcessStatusEnum | undefined;
  change_description?:
    | /**
     * Description of changes from previous version (for approval review)
     */
    (string | null)
    | undefined;
};
export type ProcessesRequest = {
  external_id?:
    | /**
     * External system identifier for integration sync
     *
     * @maxLength 255
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_current_version?: boolean | undefined;
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured?: boolean | undefined;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
  status?: /**
     * Controls editability and availability for work orders
    
    * `draft` - Draft
    * `pending_approval` - Pending Approval
    * `approved` - Approved
    * `deprecated` - Deprecated
     */
  ProcessStatusEnum | undefined;
  change_description?:
    | /**
     * Description of changes from previous version (for approval review)
     */
    (string | null)
    | undefined;
  approved_at?: (string | null) | undefined;
  tenant?:
    | /**
     * Tenant this record belongs to
     */
    (string | null)
    | undefined;
  previous_version?: (string | null) | undefined;
  part_type: string;
  approved_by?: (number | null) | undefined;
};
export type QualityReportsRequest = {
  step?: (string | null) | undefined;
  part?: (string | null) | undefined;
  machine?: (string | null) | undefined;
  operators?: /**
   * Operators running the process when defect occurred (for root cause)
   */
  Array<number> | undefined;
  sampling_method?: /**
   * @minLength 1
   * @maxLength 50
   */
  string | undefined;
  status: QualityReportStatusEnum;
  description?:
    | /**
     * @maxLength 300
     */
    (string | null)
    | undefined;
  file?: (string | null) | undefined;
  measurements: Array<MeasurementResultRequest>;
  sampling_audit_log?:
    | /**
     * Links to the sampling decision that triggered this inspection
     */
    (string | null)
    | undefined;
  detected_by?:
    | /**
     * Inspector/operator who detected the defect (required for new reports)
     */
    (number | null)
    | undefined;
  verified_by?:
    | /**
     * Second signature for critical inspections (aerospace/medical)
     */
    (number | null)
    | undefined;
  is_first_piece?: /**
   * If True, this inspection is a First Piece Inspection (FPI) for setup verification
   */
  boolean | undefined;
  archived?: boolean | undefined;
};
export type QuarantineDispositionRequest = {
  current_state?: CurrentStateEnum | undefined;
  disposition_type?: (DispositionTypeEnum | BlankEnum) | undefined;
  severity?: SeverityEnum | undefined;
  assigned_to?: (number | null) | undefined;
  description?: string | undefined;
  resolution_notes?: string | undefined;
  resolution_completed?: boolean | undefined;
  resolution_completed_by?: (number | null) | undefined;
  resolution_completed_at?: (string | null) | undefined;
  containment_action?: /**
   * Immediate action taken to prevent escape
   */
  string | undefined;
  containment_completed_at?: (string | null) | undefined;
  containment_completed_by?: (number | null) | undefined;
  requires_customer_approval?: boolean | undefined;
  customer_approval_received?: boolean | undefined;
  customer_approval_reference?: /**
   * PO#, email reference, or approval document number
   *
   * @maxLength 100
   */
  string | undefined;
  customer_approval_date?: (string | null) | undefined;
  scrap_verified?: boolean | undefined;
  scrap_verification_method?: /**
   * How product was rendered unusable: crushed, marked, etc.
   *
   * @maxLength 100
   */
  string | undefined;
  scrap_verified_by?: (number | null) | undefined;
  scrap_verified_at?: (string | null) | undefined;
  part?: (string | null) | undefined;
  step?: (string | null) | undefined;
  rework_attempt_at_step?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  quality_reports: Array<string>;
  archived?: boolean | undefined;
};
export type RcaRecordRequest = {
  capa: string;
  rca_method: RcaMethodEnum;
  /**
   * @minLength 1
   */
  problem_description: string;
  root_cause_summary?: (string | null) | undefined;
  conducted_by?: (number | null) | undefined;
  conducted_date?: (string | null) | undefined;
  rca_review_status?: RcaReviewStatusEnum | undefined;
  root_cause_verification_status?: RootCauseVerificationStatusEnum | undefined;
  root_cause_verified_by?: (number | null) | undefined;
  quality_reports?: Array<string> | undefined;
  dispositions?: Array<string> | undefined;
  five_whys_data?: FiveWhysNestedRequest | undefined;
  fishbone_data?: FishboneNestedRequest | undefined;
  archived?: boolean | undefined;
};
export type RootCauseRequest = {
  rca_record: string;
  /**
   * @minLength 1
   */
  description: string;
  category: RootCauseCategoryEnum;
  role?: RoleEnum | undefined;
  sequence?: /**
   * Order in causal chain
   *
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  archived?: boolean | undefined;
};
export type SPCBaseline = {
  id: string;
  /**
   * The measurement definition this baseline applies to
   */
  measurement_definition: string;
  measurement_label: string;
  process_name: string | null;
  step_name: string;
  /**
     * Type of control chart (X-bar R, X-bar S, or I-MR)
    
    * `XBAR_R` - X̄-R
    * `XBAR_S` - X̄-S
    * `I_MR` - I-MR
     */
  chart_type: ChartTypeEnum;
  chart_type_display: string;
  subgroup_size?: /**
   * Number of samples per subgroup (n=2 to 25 for X-bar charts, n=1 for I-MR)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  xbar_ucl?:
    | /**
     * X-bar chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_cl?:
    | /**
     * X-bar chart Center Line (grand mean)
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_lcl?:
    | /**
     * X-bar chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_ucl?:
    | /**
     * Range (or S) chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_cl?:
    | /**
     * Range (or S) chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_lcl?:
    | /**
     * Range (or S) chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_ucl?:
    | /**
     * Individual chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_cl?:
    | /**
     * Individual chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_lcl?:
    | /**
     * Individual chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_ucl?:
    | /**
     * Moving Range chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_cl?:
    | /**
     * Moving Range chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  status?: /**
     * Current status of this baseline
    
    * `ACTIVE` - Active
    * `SUPERSEDED` - Superseded
     */
  BaselineStatusEnum | undefined;
  status_display: string;
  frozen_by?:
    | /**
     * User who froze/created this baseline
     */
    (number | null)
    | undefined;
  frozen_by_name: string | null;
  /**
   * Timestamp when baseline was frozen
   */
  frozen_at: string;
  superseded_by?:
    | /**
     * The baseline that replaced this one
     */
    (string | null)
    | undefined;
  /**
   * Timestamp when this baseline was superseded
   */
  superseded_at: string | null;
  superseded_reason?: /**
   * Reason for superseding this baseline
   */
  string | undefined;
  sample_count?: /**
   * Number of data points used to calculate this baseline
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  notes?: /**
   * Additional notes about this baseline
   */
  string | undefined;
  control_limits: {};
  created_at: string;
  updated_at: string;
};
export type SPCBaselineFreezeRequest = {
  measurement_definition_id: string;
  chart_type: ChartTypeEnum;
  /**
   * @minimum 1
   * @maximum 25
   */
  subgroup_size: number;
  xbar_ucl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_cl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_lcl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_ucl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_cl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_lcl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_ucl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_cl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_lcl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_ucl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_cl?:
    | /**
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  sample_count?: /**
   * @default 0
   */
  number | undefined;
  notes?: /**
   * @default ""
   */
  string | undefined;
};
export type SPCBaselineRequest = {
  /**
   * The measurement definition this baseline applies to
   */
  measurement_definition: string;
  /**
     * Type of control chart (X-bar R, X-bar S, or I-MR)
    
    * `XBAR_R` - X̄-R
    * `XBAR_S` - X̄-S
    * `I_MR` - I-MR
     */
  chart_type: ChartTypeEnum;
  subgroup_size?: /**
   * Number of samples per subgroup (n=2 to 25 for X-bar charts, n=1 for I-MR)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  xbar_ucl?:
    | /**
     * X-bar chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_cl?:
    | /**
     * X-bar chart Center Line (grand mean)
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  xbar_lcl?:
    | /**
     * X-bar chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_ucl?:
    | /**
     * Range (or S) chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_cl?:
    | /**
     * Range (or S) chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  range_lcl?:
    | /**
     * Range (or S) chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_ucl?:
    | /**
     * Individual chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_cl?:
    | /**
     * Individual chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  individual_lcl?:
    | /**
     * Individual chart Lower Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_ucl?:
    | /**
     * Moving Range chart Upper Control Limit
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  mr_cl?:
    | /**
     * Moving Range chart Center Line
     *
     * @pattern ^-?\d{0,10}(?:\.\d{0,6})?$
     */
    (string | null)
    | undefined;
  status?: /**
     * Current status of this baseline
    
    * `ACTIVE` - Active
    * `SUPERSEDED` - Superseded
     */
  BaselineStatusEnum | undefined;
  frozen_by?:
    | /**
     * User who froze/created this baseline
     */
    (number | null)
    | undefined;
  superseded_by?:
    | /**
     * The baseline that replaced this one
     */
    (string | null)
    | undefined;
  superseded_reason?: /**
   * Reason for superseding this baseline
   */
  string | undefined;
  sample_count?: /**
   * Number of data points used to calculate this baseline
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  notes?: /**
   * Additional notes about this baseline
   */
  string | undefined;
};
export type SPCCapabilityResponse = {
  definition: MeasurementDefinitionSPC;
  sample_size: number;
  subgroup_size: number;
  num_subgroups: number;
  usl: number;
  lsl: number;
  mean: number;
  std_dev_within: number;
  std_dev_overall: number;
  cp: number | null;
  cpk: number | null;
  pp: number | null;
  ppk: number | null;
  interpretation: string;
};
export type SPCDataResponse = {
  definition: MeasurementDefinitionSPC;
  process_name: string;
  step_name: string;
  data_points: Array<MeasurementDataPoint>;
  statistics: {};
};
export type MeasurementDataPoint = {
  id: string;
  value: number;
  timestamp: string;
  report_id: string;
  part_erp_id: string;
  operator_name: string | null;
  is_within_spec: boolean;
};
export type SamplingRuleRequest = {
  rule_type: RuleTypeEnum;
  value?:
    | /**
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  order?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  algorithm_description?: /**
   * Description of sampling algorithm for audit purposes
   *
   * @minLength 1
   */
  string | undefined;
  last_validated?: (string | null) | undefined;
  ruleset: string;
  created_by?: (number | null) | undefined;
  modified_by?: (number | null) | undefined;
  archived?: boolean | undefined;
};
export type SamplingRuleUpdateRequest = {
  rule_type: RuleTypeEnum;
  value?: (number | null) | undefined;
  order: number;
};
export type ScheduleSlotRequest = {
  work_center: string;
  shift: string;
  work_order: string;
  scheduled_date: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start?: (string | null) | undefined;
  actual_end?: (string | null) | undefined;
  status?: ScheduleSlotStatusEnum | undefined;
  notes?: string | undefined;
  archived?: boolean | undefined;
};
export type StepEdgeRequest = {
  from_step: string;
  to_step: string;
  edge_type?: EdgeTypeEnum | undefined;
  condition_measurement?:
    | /**
     * Optional: measurement that triggers this edge
     */
    (string | null)
    | undefined;
  condition_operator?: (ConditionOperatorEnum | BlankEnum) | undefined;
  condition_value?:
    | /**
     * Threshold value for measurement-based routing
     *
     * @pattern ^-?\d{0,6}(?:\.\d{0,4})?$
     */
    (string | null)
    | undefined;
};
export type StepExecutionRequest = {
  /**
   * The part being tracked through this step
   */
  part: string;
  /**
   * The step being executed
   */
  step: string;
  visit_number?: /**
   * Which visit this is (1st, 2nd, 3rd time at this step)
   *
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  exited_at?: (string | null) | undefined;
  assigned_to?:
    | /**
     * Operator assigned to this step execution
     */
    (number | null)
    | undefined;
  completed_by?:
    | /**
     * Operator who completed this step
     */
    (number | null)
    | undefined;
  next_step?:
    | /**
     * The step this part moved to (for audit trail)
     */
    (string | null)
    | undefined;
  decision_result?: /**
   * Result of decision: 'pass', 'fail', measurement value, etc.
   *
   * @maxLength 50
   */
  string | undefined;
  status?: StepExecutionStatusEnum | undefined;
  archived?: boolean | undefined;
};
export type StepRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  description?: (string | null) | undefined;
  part_type: string;
  expected_duration?: (string | null) | undefined;
  requires_qa_signoff?: boolean | undefined;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
  block_on_quarantine?: boolean | undefined;
  pass_threshold?: number | undefined;
  step_type?: /**
     * Visual type for flow editor.
    
    * `task` - Task
    * `start` - Start
    * `decision` - Decision
    * `rework` - Rework
    * `timer` - Timer/Wait
    * `terminal` - Terminal
     */
  StepTypeEnum | undefined;
  is_decision_point?: boolean | undefined;
  decision_type?: (DecisionTypeEnum | BlankEnum) | undefined;
  is_terminal?: boolean | undefined;
  terminal_status?: (TerminalStatusEnum | BlankEnum) | undefined;
  max_visits?:
    | /**
     * Max times a part can visit this step. Null = unlimited.
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  revisit_assignment?: RevisitAssignmentEnum | undefined;
};
export type StepSamplingRulesUpdateRequest = {
  rules: Array<SamplingRuleUpdateRequest>;
  fallback_rules?: Array<SamplingRuleUpdateRequest> | undefined;
  fallback_threshold?: number | undefined;
  fallback_duration?: number | undefined;
};
export type StepSummary = {
  step_id: string;
  step_name: string;
  step_order: number;
  status: TravelerStepStatusEnum;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  operator_name: string | null;
  quality_status: QualityStatusEnum | NullEnum | null;
  parts_at_step: number;
  parts_completed: number;
  measurement_count: number;
  defect_count: number;
  attachment_count: number;
};
export type StepsRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  expected_duration?: (string | null) | undefined;
  description?: (string | null) | undefined;
  block_on_quarantine?: boolean | undefined;
  requires_qa_signoff?: boolean | undefined;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
  pass_threshold?: number | undefined;
  requires_first_piece_inspection?: /**
   * If True, first part of each work order at this step requires FPI before others can proceed
   */
  boolean | undefined;
  part_type: string;
  step_type?: /**
     * Visual type for flow editor.
    
    * `task` - Task
    * `start` - Start
    * `decision` - Decision
    * `rework` - Rework
    * `timer` - Timer/Wait
    * `terminal` - Terminal
     */
  StepTypeEnum | undefined;
  is_decision_point?: boolean | undefined;
  decision_type?: (DecisionTypeEnum | BlankEnum) | undefined;
  is_terminal?: boolean | undefined;
  terminal_status?: (TerminalStatusEnum | BlankEnum) | undefined;
  max_visits?:
    | /**
     * Max times a part can visit this step. Null = unlimited.
     *
     * @minimum 0
     * @maximum 2147483647
     */
    (number | null)
    | undefined;
  revisit_assignment?: RevisitAssignmentEnum | undefined;
  revisit_role?:
    | /**
     * Required role when revisit_assignment='role'
     */
    (number | null)
    | undefined;
  archived?: boolean | undefined;
};
export type SubmitProcessForApprovalResponse = {
  process: ProcessWithSteps;
  approval_request_id: string;
  approval_number: string;
};
export type TenantCreate = {
  /**
   * Display name of the organization
   *
   * @maxLength 100
   */
  name: string;
  /**
   * URL-safe identifier, immutable after creation
   *
   * @maxLength 50
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier?: TierEnum | undefined;
  is_demo?: /**
   * Demo tenant with reset capability
   */
  boolean | undefined;
};
export type TenantCreateRequest = {
  /**
   * Display name of the organization
   *
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  /**
   * URL-safe identifier, immutable after creation
   *
   * @minLength 1
   * @maxLength 50
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier?: TierEnum | undefined;
  is_demo?: /**
   * Demo tenant with reset capability
   */
  boolean | undefined;
  /**
   * @minLength 1
   */
  admin_email: string;
  admin_password?: /**
   * @minLength 1
   */
  string | undefined;
  admin_first_name?: /**
   * @default "Admin"
   * @minLength 1
   */
  string | undefined;
  admin_last_name?: /**
   * @default "User"
   * @minLength 1
   */
  string | undefined;
};
export type TenantRequest = {
  /**
   * Display name of the organization
   *
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  /**
   * URL-safe identifier, immutable after creation
   *
   * @minLength 1
   * @maxLength 50
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug: string;
  tier?: TierEnum | undefined;
  status?: TenantStatusEnum | undefined;
  is_active?: boolean | undefined;
  is_demo?: /**
   * Demo tenant with reset capability
   */
  boolean | undefined;
  trial_ends_at?:
    | /**
     * Trial expiration date
     */
    (string | null)
    | undefined;
  settings?: /**
   * Tenant-specific configuration
   */
  unknown | undefined;
  logo?:
    | /**
     * Organization logo (recommended: 200x200 PNG)
     */
    (string | null)
    | undefined;
  contact_email?: /**
   * Primary contact email for the organization
   *
   * @maxLength 254
   */
  string | undefined;
  contact_phone?: /**
   * Primary contact phone number
   *
   * @maxLength 30
   */
  string | undefined;
  website?: /**
   * Organization website URL
   *
   * @maxLength 200
   */
  string | undefined;
  address?: /**
   * Organization mailing address
   */
  string | undefined;
  default_timezone?: /**
   * Default timezone for the organization (IANA format, e.g., 'America/New_York')
   *
   * @minLength 1
   * @maxLength 50
   */
  string | undefined;
};
export type TimeEntryRequest = {
  entry_type: TimeEntryTypeEnum;
  start_time: string;
  end_time?: (string | null) | undefined;
  part?: (string | null) | undefined;
  work_order?: (string | null) | undefined;
  step?: (string | null) | undefined;
  equipment?: (string | null) | undefined;
  work_center?: (string | null) | undefined;
  notes?: string | undefined;
  downtime_reason?: /**
   * @maxLength 100
   */
  string | undefined;
  approved?: boolean | undefined;
  archived?: boolean | undefined;
};
export type UserDetail = {
  id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   *
   * @maxLength 150
   * @pattern ^[\w.@+-]+$
   */
  username: string;
  first_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  last_name?:
    | /**
     * @maxLength 150
     */
    (string | null)
    | undefined;
  email?: /**
   * @maxLength 254
   */
  string | undefined;
  is_staff?: /**
   * Designates whether the user can log into this admin site.
   */
  boolean | undefined;
  is_active?: /**
   * Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
   */
  boolean | undefined;
  date_joined: string;
  parent_company: Company;
};
export type WorkOrder = {
  id: string;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status?: WorkOrderStatusEnum | undefined;
  priority?: /**
     * Work order priority. Lower number = higher priority for scheduling.
    
    * `1` - Urgent
    * `2` - High
    * `3` - Normal
    * `4` - Low
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
  PriorityEnum | undefined;
  quantity?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  related_order?: (string | null) | undefined;
  related_order_info: {};
  related_order_detail: {};
  process?: (string | null) | undefined;
  process_info: {};
  expected_completion?: (string | null) | undefined;
  expected_duration?: (string | null) | undefined;
  true_completion?: (string | null) | undefined;
  true_duration?: (string | null) | undefined;
  notes?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  parts_summary: {};
  is_batch_work_order: boolean;
  created_at: string;
  updated_at: string;
  archived?: boolean | undefined;
};
export type WorkOrderRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status?: WorkOrderStatusEnum | undefined;
  priority?: /**
     * Work order priority. Lower number = higher priority for scheduling.
    
    * `1` - Urgent
    * `2` - High
    * `3` - Normal
    * `4` - Low
     *
     * @minimum -2147483648
     * @maximum 2147483647
     */
  PriorityEnum | undefined;
  quantity?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  related_order?: (string | null) | undefined;
  process?: (string | null) | undefined;
  expected_completion?: (string | null) | undefined;
  expected_duration?: (string | null) | undefined;
  true_completion?: (string | null) | undefined;
  true_duration?: (string | null) | undefined;
  notes?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  archived?: boolean | undefined;
};
export type WorkOrderStepHistoryResponse = {
  work_order_id: string;
  process_name: string | null;
  total_parts: number;
  step_history: Array<StepSummary>;
};

const ApprovalStatusEnum = z.enum([
  "NOT_REQUIRED",
  "PENDING",
  "APPROVED",
  "REJECTED",
  "CANCELLED",
]);
const ApprovalTypeEnum = z.enum([
  "DOCUMENT_RELEASE",
  "CAPA_CRITICAL",
  "CAPA_MAJOR",
  "ECO",
  "TRAINING_CERT",
  "PROCESS_APPROVAL",
]);
const ApprovalFlowTypeEnum = z.enum(["ALL_REQUIRED", "THRESHOLD", "ANY"]);
const ApprovalSequenceEnum = z.enum(["PARALLEL", "SEQUENTIAL"]);
const DelegationPolicyEnum = z.enum(["OPTIONAL", "DISABLED"]);
const DecisionEnum = z.enum(["APPROVED", "REJECTED", "DELEGATED"]);
const VerificationMethodEnum = z.enum(["PASSWORD", "SSO", "NONE"]);
const ApprovalResponse = z
  .object({
    id: z.string().uuid(),
    approval_request: z.string().uuid(),
    approver: z.number().int(),
    approver_info: z.object({}).partial().passthrough().nullable(),
    decision: DecisionEnum,
    decision_display: z.string(),
    decision_date: z.string().datetime({ offset: true }),
    comments: z.string().nullish(),
    signature_data: z.string().nullish(),
    signature_meaning: z.string().max(200).nullish(),
    verified_at: z.string().datetime({ offset: true }).nullable(),
    verification_method: VerificationMethodEnum.optional(),
    verification_method_display: z.string(),
    delegated_to: z.number().int().nullish(),
    delegated_to_info: z.object({}).partial().passthrough().nullable(),
    ip_address: z.string().nullable(),
    self_approved: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const ApprovalRequest = z
  .object({
    id: z.string().uuid(),
    approval_number: z.string(),
    content_type: z.number().int().nullish(),
    object_id: z.string().max(36).nullish(),
    content_object_info: z.object({}).partial().passthrough().nullable(),
    requested_by: z.number().int().nullish(),
    requested_by_info: z.object({}).partial().passthrough().nullable(),
    reason: z.string().nullish(),
    notes: z.string().nullish(),
    status: ApprovalStatusEnum.optional(),
    status_display: z.string(),
    approval_type: ApprovalTypeEnum,
    approval_type_display: z.string(),
    flow_type: ApprovalFlowTypeEnum.optional(),
    flow_type_display: z.string(),
    sequence_type: ApprovalSequenceEnum.optional(),
    threshold: z.number().int().gte(-2147483648).lte(2147483647).nullish(),
    delegation_policy: DelegationPolicyEnum.optional(),
    escalation_day: z.string().nullish(),
    escalate_to: z.number().int().nullish(),
    due_date: z.string().datetime({ offset: true }).nullish(),
    approver_assignments_info: z.array(z.unknown()),
    required_approvers_info: z.array(z.unknown()),
    optional_approvers_info: z.array(z.unknown()),
    approver_groups: z.array(z.string().uuid()),
    approver_groups_info: z.array(z.unknown()),
    responses: z.array(ApprovalResponse),
    pending_approvers: z.array(z.unknown()),
    requested_at: z.string().datetime({ offset: true }),
    completed_at: z.string().datetime({ offset: true }).nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedApprovalRequestList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ApprovalRequest),
  })
  .passthrough();
const ApprovalRequestRequest = z
  .object({
    content_type: z.number().int().nullish(),
    object_id: z.string().max(36).nullish(),
    requested_by: z.number().int().nullish(),
    reason: z.string().nullish(),
    notes: z.string().nullish(),
    status: ApprovalStatusEnum.optional(),
    approval_type: ApprovalTypeEnum,
    flow_type: ApprovalFlowTypeEnum.optional(),
    sequence_type: ApprovalSequenceEnum.optional(),
    threshold: z.number().int().gte(-2147483648).lte(2147483647).nullish(),
    delegation_policy: DelegationPolicyEnum.optional(),
    escalation_day: z.string().nullish(),
    escalate_to: z.number().int().nullish(),
    due_date: z.string().datetime({ offset: true }).nullish(),
  })
  .passthrough();
const PatchedApprovalRequestRequest = z
  .object({
    content_type: z.number().int().nullable(),
    object_id: z.string().max(36).nullable(),
    requested_by: z.number().int().nullable(),
    reason: z.string().nullable(),
    notes: z.string().nullable(),
    status: ApprovalStatusEnum,
    approval_type: ApprovalTypeEnum,
    flow_type: ApprovalFlowTypeEnum,
    sequence_type: ApprovalSequenceEnum,
    threshold: z.number().int().gte(-2147483648).lte(2147483647).nullable(),
    delegation_policy: DelegationPolicyEnum,
    escalation_day: z.string().nullable(),
    escalate_to: z.number().int().nullable(),
    due_date: z.string().datetime({ offset: true }).nullable(),
  })
  .partial()
  .passthrough();
const ListMetadataResponse = z
  .object({
    search_fields: z.array(z.string()),
    search_fields_display: z.array(z.string()),
    ordering_fields: z.array(z.string()),
    ordering_fields_display: z.array(z.string()),
    filterset_fields: z.array(z.string()),
    filters: z.object({}).partial().passthrough(),
  })
  .passthrough();
const PaginatedApprovalResponseList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ApprovalResponse),
  })
  .passthrough();
const ApprovalResponseRequest = z
  .object({
    approval_request: z.string().uuid(),
    approver: z.number().int(),
    decision: DecisionEnum,
    comments: z.string().nullish(),
    signature_data: z.string().nullish(),
    signature_meaning: z.string().max(200).nullish(),
    verification_method: VerificationMethodEnum.optional(),
    delegated_to: z.number().int().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedApprovalResponseRequest = z
  .object({
    approval_request: z.string().uuid(),
    approver: z.number().int(),
    decision: DecisionEnum,
    comments: z.string().nullable(),
    signature_data: z.string().nullable(),
    signature_meaning: z.string().max(200).nullable(),
    verification_method: VerificationMethodEnum,
    delegated_to: z.number().int().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const ApprovalTemplate = z
  .object({
    id: z.string().uuid(),
    template_name: z.string().max(100),
    approval_type: ApprovalTypeEnum,
    approval_type_display: z.string(),
    default_groups: z.array(z.string().uuid()).optional(),
    default_groups_info: z.array(z.unknown()),
    default_approvers: z.array(z.number().int()).optional(),
    default_approvers_info: z.array(z.unknown()),
    default_threshold: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullish(),
    auto_assign_by_role: z.string().max(50).nullish(),
    approval_flow_type: ApprovalFlowTypeEnum.optional(),
    approval_flow_type_display: z.string(),
    delegation_policy: DelegationPolicyEnum.optional(),
    delegation_policy_display: z.string(),
    approval_sequence: ApprovalSequenceEnum.optional(),
    approval_sequence_display: z.string(),
    allow_self_approval: z.boolean().optional(),
    default_due_days: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    escalation_days: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullish(),
    escalate_to: z.number().int().nullish(),
    escalate_to_info: z.object({}).partial().passthrough().nullable(),
    deactivated_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedApprovalTemplateList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ApprovalTemplate),
  })
  .passthrough();
const ApprovalTemplateRequest = z
  .object({
    template_name: z.string().min(1).max(100),
    approval_type: ApprovalTypeEnum,
    default_groups: z.array(z.string().uuid()).optional(),
    default_approvers: z.array(z.number().int()).optional(),
    default_threshold: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullish(),
    auto_assign_by_role: z.string().max(50).nullish(),
    approval_flow_type: ApprovalFlowTypeEnum.optional(),
    delegation_policy: DelegationPolicyEnum.optional(),
    approval_sequence: ApprovalSequenceEnum.optional(),
    allow_self_approval: z.boolean().optional(),
    default_due_days: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    escalation_days: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullish(),
    escalate_to: z.number().int().nullish(),
    deactivated_at: z.string().datetime({ offset: true }).nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedApprovalTemplateRequest = z
  .object({
    template_name: z.string().min(1).max(100),
    approval_type: ApprovalTypeEnum,
    default_groups: z.array(z.string().uuid()),
    default_approvers: z.array(z.number().int()),
    default_threshold: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullable(),
    auto_assign_by_role: z.string().max(50).nullable(),
    approval_flow_type: ApprovalFlowTypeEnum,
    delegation_policy: DelegationPolicyEnum,
    approval_sequence: ApprovalSequenceEnum,
    allow_self_approval: z.boolean(),
    default_due_days: z.number().int().gte(-2147483648).lte(2147483647),
    escalation_days: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .nullable(),
    escalate_to: z.number().int().nullable(),
    deactivated_at: z.string().datetime({ offset: true }).nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const AssemblyUsage = z
  .object({
    id: z.string().uuid(),
    assembly: z.string().uuid(),
    assembly_erp_id: z.string(),
    component: z.string().uuid(),
    component_erp_id: z.string(),
    quantity: z
      .string()
      .regex(/^-?\d{0,6}(?:\.\d{0,4})?$/)
      .optional(),
    bom_line: z.string().uuid().nullish(),
    installed_at: z.string().datetime({ offset: true }),
    installed_by: z.number().int(),
    installed_by_name: z.string(),
    step: z.string().uuid().nullish(),
    removed_at: z.string().datetime({ offset: true }).nullable(),
    removed_by: z.number().int().nullable(),
    removal_reason: z.string(),
    is_installed: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedAssemblyUsageList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(AssemblyUsage),
  })
  .passthrough();
const AssemblyUsageRequest = z
  .object({
    assembly: z.string().uuid(),
    component: z.string().uuid(),
    quantity: z
      .string()
      .regex(/^-?\d{0,6}(?:\.\d{0,4})?$/)
      .optional(),
    bom_line: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedAssemblyUsageRequest = z
  .object({
    assembly: z.string().uuid(),
    component: z.string().uuid(),
    quantity: z.string().regex(/^-?\d{0,6}(?:\.\d{0,4})?$/),
    bom_line: z.string().uuid().nullable(),
    step: z.string().uuid().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const AssemblyRemoveRequest = z
  .object({ reason: z.string().default("") })
  .partial()
  .passthrough();
const BOMLine = z
  .object({
    id: z.string().uuid(),
    bom: z.string().uuid(),
    component_type: z.string().uuid(),
    component_type_name: z.string(),
    quantity: z.string().regex(/^-?\d{0,6}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().max(20).optional(),
    find_number: z.string().max(20).optional(),
    reference_designator: z.string().max(100).optional(),
    is_optional: z.boolean().optional(),
    allow_harvested: z.boolean().optional(),
    notes: z.string().optional(),
    line_number: z.number().int().gte(0).lte(2147483647).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedBOMLineList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(BOMLine),
  })
  .passthrough();
const BOMLineRequest = z
  .object({
    bom: z.string().uuid(),
    component_type: z.string().uuid(),
    quantity: z.string().regex(/^-?\d{0,6}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().min(1).max(20).optional(),
    find_number: z.string().max(20).optional(),
    reference_designator: z.string().max(100).optional(),
    is_optional: z.boolean().optional(),
    allow_harvested: z.boolean().optional(),
    notes: z.string().optional(),
    line_number: z.number().int().gte(0).lte(2147483647).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedBOMLineRequest = z
  .object({
    bom: z.string().uuid(),
    component_type: z.string().uuid(),
    quantity: z.string().regex(/^-?\d{0,6}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().min(1).max(20),
    find_number: z.string().max(20),
    reference_designator: z.string().max(100),
    is_optional: z.boolean(),
    allow_harvested: z.boolean(),
    notes: z.string(),
    line_number: z.number().int().gte(0).lte(2147483647),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const BOMTypeEnum = z.enum(["assembly", "disassembly"]);
const BOMStatusEnum = z.enum(["draft", "released", "obsolete"]);
const BOMList = z
  .object({
    id: z.string().uuid(),
    part_type: z.string().uuid(),
    part_type_name: z.string(),
    revision: z.string().max(10),
    bom_type: BOMTypeEnum.optional(),
    status: BOMStatusEnum.optional(),
    line_count: z.number().int(),
  })
  .passthrough();
const PaginatedBOMListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(BOMList),
  })
  .passthrough();
const BOMRequest = z
  .object({
    part_type: z.string().uuid(),
    revision: z.string().min(1).max(10),
    bom_type: BOMTypeEnum.optional(),
    status: BOMStatusEnum.optional(),
    description: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const BOM = z
  .object({
    id: z.string().uuid(),
    part_type: z.string().uuid(),
    part_type_name: z.string(),
    revision: z.string().max(10),
    bom_type: BOMTypeEnum.optional(),
    status: BOMStatusEnum.optional(),
    description: z.string().optional(),
    effective_date: z.string().nullable(),
    obsolete_date: z.string().nullable(),
    approved_by: z.number().int().nullable(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    lines: z.array(BOMLine),
    line_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedBOMRequest = z
  .object({
    part_type: z.string().uuid(),
    revision: z.string().min(1).max(10),
    bom_type: BOMTypeEnum,
    status: BOMStatusEnum,
    description: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const CapaTypeEnum = z.enum([
  "CORRECTIVE",
  "PREVENTIVE",
  "CUSTOMER_COMPLAINT",
  "INTERNAL_AUDIT",
  "SUPPLIER",
]);
const SeverityEnum = z.enum(["CRITICAL", "MAJOR", "MINOR"]);
const TaskTypeEnum = z.enum(["CONTAINMENT", "CORRECTIVE", "PREVENTIVE"]);
const CapaTaskStatusEnum = z.enum([
  "NOT_STARTED",
  "IN_PROGRESS",
  "COMPLETED",
  "CANCELLED",
]);
const CapaTaskAssignee = z
  .object({
    id: z.string().uuid(),
    task: z.string().uuid(),
    task_info: z.object({}).partial().passthrough().nullable(),
    user: z.number().int(),
    user_info: z.object({}).partial().passthrough().nullable(),
    status: CapaTaskStatusEnum.optional(),
    completed_at: z.string().datetime({ offset: true }).nullable(),
    completion_notes: z.string().nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const CompletionModeEnum = z.enum([
  "SINGLE_OWNER",
  "ANY_ASSIGNEE",
  "ALL_ASSIGNEES",
]);
const CapaTasks = z
  .object({
    id: z.string().uuid(),
    task_number: z.string(),
    capa: z.string().uuid(),
    capa_info: z.object({}).partial().passthrough().nullable(),
    task_type: TaskTypeEnum,
    task_type_display: z.string(),
    description: z.string(),
    assigned_to: z.number().int().nullish(),
    assigned_to_info: z.object({}).partial().passthrough().nullable(),
    assignees: z.array(CapaTaskAssignee),
    completion_mode: CompletionModeEnum.optional(),
    completion_mode_display: z.string(),
    due_date: z.string().nullish(),
    requires_signature: z.boolean().optional(),
    status: CapaTaskStatusEnum.optional(),
    status_display: z.string(),
    completed_by: z.number().int().nullable(),
    completed_by_info: z.object({}).partial().passthrough().nullable(),
    completed_date: z.string().nullable(),
    completion_notes: z.string().nullish(),
    completion_signature: z.string().nullable(),
    is_overdue: z.boolean(),
    documents_info: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const RcaMethodEnum = z.enum(["FIVE_WHYS", "FISHBONE", "FAULT_TREE", "PARETO"]);
const RcaReviewStatusEnum = z.enum(["NOT_REQUIRED", "REQUIRED", "COMPLETED"]);
const RootCauseVerificationStatusEnum = z.enum([
  "UNVERIFIED",
  "VERIFIED",
  "DISPUTED",
]);
const RootCauseCategoryEnum = z.enum([
  "MAN",
  "MACHINE",
  "MATERIAL",
  "METHOD",
  "MEASUREMENT",
  "ENVIRONMENT",
  "OTHER",
]);
const RoleEnum = z.enum(["PRIMARY", "CONTRIBUTING"]);
const RootCause = z
  .object({
    id: z.string().uuid(),
    rca_record: z.string().uuid(),
    rca_record_info: z.object({}).partial().passthrough().nullable(),
    description: z.string(),
    category: RootCauseCategoryEnum,
    category_display: z.string(),
    role: RoleEnum.optional(),
    role_display: z.string(),
    sequence: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const FiveWhys = z
  .object({
    id: z.string().uuid(),
    rca_record: z.string().uuid(),
    rca_record_info: z.object({}).partial().passthrough().nullable(),
    why_1_question: z.string().nullish(),
    why_1_answer: z.string().nullish(),
    why_2_question: z.string().nullish(),
    why_2_answer: z.string().nullish(),
    why_3_question: z.string().nullish(),
    why_3_answer: z.string().nullish(),
    why_4_question: z.string().nullish(),
    why_4_answer: z.string().nullish(),
    why_5_question: z.string().nullish(),
    why_5_answer: z.string().nullish(),
    identified_root_cause: z.string().nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const Fishbone = z
  .object({
    id: z.string().uuid(),
    rca_record: z.string().uuid(),
    rca_record_info: z.object({}).partial().passthrough().nullable(),
    problem_statement: z.string(),
    man_causes: z.unknown().optional(),
    machine_causes: z.unknown().optional(),
    material_causes: z.unknown().optional(),
    method_causes: z.unknown().optional(),
    measurement_causes: z.unknown().optional(),
    environment_causes: z.unknown().optional(),
    identified_root_cause: z.string().nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const RcaRecord = z
  .object({
    id: z.string().uuid(),
    capa: z.string().uuid(),
    capa_info: z.object({}).partial().passthrough().nullable(),
    rca_method: RcaMethodEnum,
    rca_method_display: z.string(),
    problem_description: z.string(),
    root_cause_summary: z.string().nullish(),
    conducted_by: z.number().int().nullish(),
    conducted_by_info: z.object({}).partial().passthrough().nullable(),
    conducted_date: z.string().nullish(),
    rca_review_status: RcaReviewStatusEnum.optional(),
    rca_review_status_display: z.string(),
    root_cause_verification_status: RootCauseVerificationStatusEnum.optional(),
    root_cause_verification_status_display: z.string(),
    root_cause_verified_at: z.string().datetime({ offset: true }).nullable(),
    root_cause_verified_by: z.number().int().nullish(),
    root_cause_verified_by_info: z
      .object({})
      .partial()
      .passthrough()
      .nullable(),
    self_verified: z.boolean(),
    quality_reports: z.array(z.string().uuid()).optional(),
    dispositions: z.array(z.string().uuid()).optional(),
    root_causes: z.array(RootCause),
    five_whys: FiveWhys.nullable(),
    fishbone: Fishbone.nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const EffectivenessResultEnum = z.enum([
  "CONFIRMED",
  "NOT_EFFECTIVE",
  "INCONCLUSIVE",
]);
const CapaVerification = z
  .object({
    id: z.string().uuid(),
    capa: z.string().uuid(),
    capa_info: z.object({}).partial().passthrough().nullable(),
    verification_method: z.string(),
    verification_criteria: z.string(),
    verification_date: z.string().nullish(),
    verified_by: z.number().int().nullish(),
    verified_by_info: z.object({}).partial().passthrough().nullable(),
    effectiveness_result: EffectivenessResultEnum.optional(),
    effectiveness_result_display: z.string(),
    effectiveness_decided_at: z.string().datetime({ offset: true }).nullable(),
    verification_notes: z.string().nullish(),
    self_verified: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const CAPA = z
  .object({
    id: z.string().uuid(),
    capa_number: z.string(),
    capa_type: CapaTypeEnum,
    capa_type_display: z.string(),
    severity: SeverityEnum,
    severity_display: z.string(),
    status: z.string(),
    status_display: z.string(),
    problem_statement: z.string(),
    immediate_action: z.string().nullish(),
    initiated_by: z.number().int().nullish(),
    initiated_by_info: z.object({}).partial().passthrough().nullable(),
    initiated_date: z.string(),
    assigned_to: z.number().int().nullish(),
    assigned_to_info: z.object({}).partial().passthrough().nullable(),
    due_date: z.string().nullish(),
    completed_date: z.string().nullable(),
    verified_by: z.number().int().nullish(),
    verified_by_info: z.object({}).partial().passthrough().nullable(),
    approval_required: z.boolean(),
    approval_status: ApprovalStatusEnum.optional(),
    approval_status_display: z.string(),
    approved_by: z.number().int().nullable(),
    approved_by_info: z.object({}).partial().passthrough().nullable(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    allow_self_verification: z.boolean().optional(),
    part: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    work_order: z.string().uuid().nullish(),
    quality_reports: z.array(z.string().uuid()).optional(),
    dispositions: z.array(z.string().uuid()).optional(),
    tasks: z.array(CapaTasks),
    rca_records: z.array(RcaRecord),
    verifications: z.array(CapaVerification),
    completion_percentage: z.number(),
    is_overdue: z.boolean(),
    blocking_items: z.array(z.unknown()),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedCAPAList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CAPA),
  })
  .passthrough();
const CAPARequest = z
  .object({
    capa_type: CapaTypeEnum,
    severity: SeverityEnum,
    problem_statement: z.string().min(1),
    immediate_action: z.string().nullish(),
    initiated_by: z.number().int().nullish(),
    assigned_to: z.number().int().nullish(),
    due_date: z.string().nullish(),
    verified_by: z.number().int().nullish(),
    approval_status: ApprovalStatusEnum.optional(),
    allow_self_verification: z.boolean().optional(),
    part: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    work_order: z.string().uuid().nullish(),
    quality_reports: z.array(z.string().uuid()).optional(),
    dispositions: z.array(z.string().uuid()).optional(),
  })
  .passthrough();
const PatchedCAPARequest = z
  .object({
    capa_type: CapaTypeEnum,
    severity: SeverityEnum,
    problem_statement: z.string().min(1),
    immediate_action: z.string().nullable(),
    initiated_by: z.number().int().nullable(),
    assigned_to: z.number().int().nullable(),
    due_date: z.string().nullable(),
    verified_by: z.number().int().nullable(),
    approval_status: ApprovalStatusEnum,
    allow_self_verification: z.boolean(),
    part: z.string().uuid().nullable(),
    step: z.string().uuid().nullable(),
    work_order: z.string().uuid().nullable(),
    quality_reports: z.array(z.string().uuid()),
    dispositions: z.array(z.string().uuid()),
  })
  .partial()
  .passthrough();
const ResultEnum = z.enum(["pass", "fail", "limited"]);
const CalibrationTypeEnum = z.enum([
  "scheduled",
  "initial",
  "after_repair",
  "after_adjustment",
  "verification",
]);
const CalibrationRecord = z
  .object({
    id: z.string().uuid(),
    equipment: z.string().uuid(),
    equipment_info: z.object({}).partial().passthrough().nullable(),
    calibration_date: z.string(),
    due_date: z.string(),
    result: ResultEnum.optional(),
    result_display: z.string(),
    calibration_type: CalibrationTypeEnum.optional(),
    calibration_type_display: z.string(),
    performed_by: z.string().max(200).optional(),
    external_lab: z.string().max(200).optional(),
    certificate_number: z.string().max(100).optional(),
    standards_used: z.string().optional(),
    as_found_in_tolerance: z.boolean().nullish(),
    adjustments_made: z.boolean().optional(),
    notes: z.string().optional(),
    status: z.string(),
    is_current: z.boolean(),
    days_until_due: z.number().int(),
    days_overdue: z.number().int().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedCalibrationRecordList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CalibrationRecord),
  })
  .passthrough();
const CalibrationRecordRequest = z
  .object({
    equipment: z.string().uuid(),
    calibration_date: z.string(),
    due_date: z.string(),
    result: ResultEnum.optional(),
    calibration_type: CalibrationTypeEnum.optional(),
    performed_by: z.string().max(200).optional(),
    external_lab: z.string().max(200).optional(),
    certificate_number: z.string().max(100).optional(),
    standards_used: z.string().optional(),
    as_found_in_tolerance: z.boolean().nullish(),
    adjustments_made: z.boolean().optional(),
    notes: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedCalibrationRecordRequest = z
  .object({
    equipment: z.string().uuid(),
    calibration_date: z.string(),
    due_date: z.string(),
    result: ResultEnum,
    calibration_type: CalibrationTypeEnum,
    performed_by: z.string().max(200),
    external_lab: z.string().max(200),
    certificate_number: z.string().max(100),
    standards_used: z.string(),
    as_found_in_tolerance: z.boolean().nullable(),
    adjustments_made: z.boolean(),
    notes: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const CalibrationStats = z
  .object({
    total_equipment: z.number().int(),
    current_calibrations: z.number().int(),
    due_soon: z.number().int(),
    overdue: z.number().int(),
    compliance_rate: z.number(),
  })
  .passthrough();
const PaginatedCapaTasksList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CapaTasks),
  })
  .passthrough();
const CapaTasksRequest = z
  .object({
    capa: z.string().uuid(),
    task_type: TaskTypeEnum,
    description: z.string().min(1),
    assigned_to: z.number().int().nullish(),
    completion_mode: CompletionModeEnum.optional(),
    due_date: z.string().nullish(),
    requires_signature: z.boolean().optional(),
    status: CapaTaskStatusEnum.optional(),
    completion_notes: z.string().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedCapaTasksRequest = z
  .object({
    capa: z.string().uuid(),
    task_type: TaskTypeEnum,
    description: z.string().min(1),
    assigned_to: z.number().int().nullable(),
    completion_mode: CompletionModeEnum,
    due_date: z.string().nullable(),
    requires_signature: z.boolean(),
    status: CapaTaskStatusEnum,
    completion_notes: z.string().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const PaginatedCapaVerificationList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CapaVerification),
  })
  .passthrough();
const CapaVerificationRequest = z
  .object({
    capa: z.string().uuid(),
    verification_method: z.string().min(1),
    verification_criteria: z.string().min(1),
    verification_date: z.string().nullish(),
    verified_by: z.number().int().nullish(),
    effectiveness_result: EffectivenessResultEnum.optional(),
    verification_notes: z.string().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedCapaVerificationRequest = z
  .object({
    capa: z.string().uuid(),
    verification_method: z.string().min(1),
    verification_criteria: z.string().min(1),
    verification_date: z.string().nullable(),
    verified_by: z.number().int().nullable(),
    effectiveness_result: EffectivenessResultEnum,
    verification_notes: z.string().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const ChatSession = z
  .object({
    id: z.number().int(),
    langgraph_thread_id: z.string().max(255),
    title: z.string().max(255).optional(),
    is_archived: z.boolean().optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PaginatedChatSessionList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ChatSession),
  })
  .passthrough();
const ChatSessionRequest = z
  .object({
    langgraph_thread_id: z.string().min(1).max(255),
    title: z.string().min(1).max(255).optional(),
    is_archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedChatSessionRequest = z
  .object({
    langgraph_thread_id: z.string().min(1).max(255),
    title: z.string().min(1).max(255),
    is_archived: z.boolean(),
  })
  .partial()
  .passthrough();
const Company = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    description: z.string(),
    hubspot_api_id: z.string().max(50).nullish(),
    user_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedCompanyList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Company),
  })
  .passthrough();
const CompanyRequest = z
  .object({
    name: z.string().min(1).max(50),
    description: z.string().min(1),
    hubspot_api_id: z.string().max(50).nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedCompanyRequest = z
  .object({
    name: z.string().min(1).max(50),
    description: z.string().min(1),
    hubspot_api_id: z.string().max(50).nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const CoreStatusEnum = z.enum([
  "received",
  "in_disassembly",
  "disassembled",
  "scrapped",
]);
const ConditionGradeEnum = z.enum(["A", "B", "C", "SCRAP"]);
const CoreList = z
  .object({
    id: z.string().uuid(),
    core_number: z.string().max(100),
    core_type: z.string().uuid(),
    core_type_name: z.string(),
    customer_name: z.string().nullable(),
    status: CoreStatusEnum.optional(),
    condition_grade: ConditionGradeEnum,
    received_date: z.string(),
  })
  .passthrough();
const PaginatedCoreListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CoreList),
  })
  .passthrough();
const SourceTypeEnum = z.enum([
  "customer_return",
  "purchased",
  "warranty",
  "trade_in",
]);
const CoreRequest = z
  .object({
    core_number: z.string().min(1).max(100),
    serial_number: z.string().max(100).optional(),
    core_type: z.string().uuid(),
    received_date: z.string(),
    customer: z.string().uuid().nullish(),
    source_type: SourceTypeEnum.optional(),
    source_reference: z.string().max(100).optional(),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string().optional(),
    status: CoreStatusEnum.optional(),
    core_credit_value: z
      .string()
      .regex(/^-?\d{0,8}(?:\.\d{0,2})?$/)
      .nullish(),
    core_credit_issued: z.boolean().optional(),
    work_order: z.string().uuid().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const Core = z
  .object({
    id: z.string().uuid(),
    core_number: z.string().max(100),
    serial_number: z.string().max(100).optional(),
    core_type: z.string().uuid(),
    core_type_name: z.string(),
    received_date: z.string(),
    received_by: z.number().int(),
    received_by_name: z.string().nullable(),
    customer: z.string().uuid().nullish(),
    customer_name: z.string().nullable(),
    source_type: SourceTypeEnum.optional(),
    source_reference: z.string().max(100).optional(),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string().optional(),
    status: CoreStatusEnum.optional(),
    disassembly_started_at: z.string().datetime({ offset: true }).nullable(),
    disassembly_completed_at: z.string().datetime({ offset: true }).nullable(),
    disassembled_by: z.number().int().nullable(),
    disassembled_by_name: z.string().nullable(),
    core_credit_value: z
      .string()
      .regex(/^-?\d{0,8}(?:\.\d{0,2})?$/)
      .nullish(),
    core_credit_issued: z.boolean().optional(),
    core_credit_issued_at: z.string().datetime({ offset: true }).nullable(),
    work_order: z.string().uuid().nullish(),
    harvested_component_count: z.number().int(),
    usable_component_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedCoreRequest = z
  .object({
    core_number: z.string().min(1).max(100),
    serial_number: z.string().max(100),
    core_type: z.string().uuid(),
    received_date: z.string(),
    customer: z.string().uuid().nullable(),
    source_type: SourceTypeEnum,
    source_reference: z.string().max(100),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string(),
    status: CoreStatusEnum,
    core_credit_value: z
      .string()
      .regex(/^-?\d{0,8}(?:\.\d{0,2})?$/)
      .nullable(),
    core_credit_issued: z.boolean(),
    work_order: z.string().uuid().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const HarvestedComponent = z
  .object({
    id: z.string().uuid(),
    core: z.string().uuid(),
    core_number: z.string(),
    component_type: z.string().uuid(),
    component_type_name: z.string(),
    component_part: z.string().uuid().nullable(),
    component_part_erp_id: z.string().nullable(),
    disassembled_at: z.string().datetime({ offset: true }),
    disassembled_by: z.number().int(),
    disassembled_by_name: z.string(),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string().optional(),
    is_scrapped: z.boolean(),
    scrap_reason: z.string(),
    scrapped_at: z.string().datetime({ offset: true }).nullable(),
    scrapped_by: z.number().int().nullable(),
    scrapped_by_name: z.string().nullable(),
    position: z.string().max(50).optional(),
    original_part_number: z.string().max(100).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedHarvestedComponentList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(HarvestedComponent),
  })
  .passthrough();
const CoreScrapRequest = z
  .object({ reason: z.string().default("") })
  .partial()
  .passthrough();
const UserDetail = z
  .object({
    id: z.number().int(),
    username: z
      .string()
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
    email: z.string().max(254).email().optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    date_joined: z.string().datetime({ offset: true }),
    parent_company: Company.nullable(),
  })
  .passthrough();
const UserDetailRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
    email: z.string().max(254).email().optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    parent_company_id: z.string().uuid().optional(),
  })
  .passthrough();
const PatchedUserDetailRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullable(),
    last_name: z.string().max(150).nullable(),
    email: z.string().max(254).email(),
    is_staff: z.boolean(),
    is_active: z.boolean(),
    parent_company_id: z.string().uuid(),
  })
  .partial()
  .passthrough();
const DisassemblyBOMLine = z
  .object({
    id: z.string().uuid(),
    core_type: z.string().uuid(),
    core_type_name: z.string(),
    component_type: z.string().uuid(),
    component_type_name: z.string(),
    expected_qty: z.number().int().gte(0).lte(2147483647).optional(),
    expected_fallout_rate: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,2})?$/)
      .optional(),
    expected_usable_qty: z.number(),
    notes: z.string().optional(),
    line_number: z.number().int().gte(0).lte(2147483647).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedDisassemblyBOMLineList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(DisassemblyBOMLine),
  })
  .passthrough();
const DisassemblyBOMLineRequest = z
  .object({
    core_type: z.string().uuid(),
    component_type: z.string().uuid(),
    expected_qty: z.number().int().gte(0).lte(2147483647).optional(),
    expected_fallout_rate: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,2})?$/)
      .optional(),
    notes: z.string().optional(),
    line_number: z.number().int().gte(0).lte(2147483647).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedDisassemblyBOMLineRequest = z
  .object({
    core_type: z.string().uuid(),
    component_type: z.string().uuid(),
    expected_qty: z.number().int().gte(0).lte(2147483647),
    expected_fallout_rate: z.string().regex(/^-?\d{0,3}(?:\.\d{0,2})?$/),
    notes: z.string(),
    line_number: z.number().int().gte(0).lte(2147483647),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const DocumentType = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    code: z.string().max(20),
    description: z.string().optional(),
    requires_approval: z.boolean().optional(),
    approval_template: z.string().uuid().nullish(),
    approval_template_name: z.string().nullable(),
    default_review_period_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullish(),
    default_retention_days: z.number().int().gte(0).lte(2147483647).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedDocumentTypeList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(DocumentType),
  })
  .passthrough();
const DocumentTypeRequest = z
  .object({
    name: z.string().min(1).max(100),
    code: z.string().min(1).max(20),
    description: z.string().optional(),
    requires_approval: z.boolean().optional(),
    approval_template: z.string().uuid().nullish(),
    default_review_period_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullish(),
    default_retention_days: z.number().int().gte(0).lte(2147483647).nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedDocumentTypeRequest = z
  .object({
    name: z.string().min(1).max(100),
    code: z.string().min(1).max(20),
    description: z.string(),
    requires_approval: z.boolean(),
    approval_template: z.string().uuid().nullable(),
    default_review_period_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullable(),
    default_retention_days: z.number().int().gte(0).lte(2147483647).nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const ClassificationEnum = z.enum([
  "public",
  "internal",
  "confidential",
  "restricted",
  "secret",
]);
const NullEnum = z.unknown();
const DocumentsStatusEnum = z.enum([
  "DRAFT",
  "UNDER_REVIEW",
  "APPROVED",
  "RELEASED",
  "OBSOLETE",
]);
const Documents = z
  .object({
    id: z.string().uuid(),
    classification: z.union([ClassificationEnum, NullEnum]).nullish(),
    ai_readable: z.boolean().optional(),
    is_image: z.boolean().optional(),
    file_name: z.string().max(50),
    file: z.string().url(),
    file_url: z.string(),
    upload_date: z.string(),
    uploaded_by: z.number().int().nullish(),
    uploaded_by_info: z.object({}).partial().passthrough().nullable(),
    content_type: z.number().int().nullish(),
    object_id: z.string().max(36).nullish(),
    content_type_info: z.object({}).partial().passthrough().nullable(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    access_info: z.object({}).partial().passthrough().nullable(),
    auto_properties: z.object({}).partial().passthrough().nullable(),
    status: DocumentsStatusEnum.optional(),
    status_display: z.string(),
    approved_by: z.number().int().nullable(),
    approved_by_info: z.object({}).partial().passthrough().nullable(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    document_type: z.string().uuid().nullish(),
    document_type_info: z.object({}).partial().passthrough().nullable(),
    change_justification: z.string().optional(),
    previous_version: z.string().uuid().nullable(),
    is_current_version: z.boolean(),
    effective_date: z.string().nullable(),
    review_date: z.string().nullable(),
    obsolete_date: z.string().nullable(),
    retention_until: z.string().nullable(),
    is_due_for_review: z.boolean(),
    days_until_review: z.number().int().nullable(),
    is_past_retention: z.boolean(),
    itar_controlled: z.boolean().optional(),
    eccn: z.string().max(20).optional(),
    export_control_reason: z.string().max(100).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PaginatedDocumentsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Documents),
  })
  .passthrough();
const DocumentsRequest = z
  .object({
    classification: z.union([ClassificationEnum, NullEnum]).nullish(),
    ai_readable: z.boolean().optional(),
    is_image: z.boolean().optional(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullish(),
    content_type: z.number().int().nullish(),
    object_id: z.string().max(36).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    status: DocumentsStatusEnum.optional(),
    document_type: z.string().uuid().nullish(),
    document_type_code: z.string().min(1).optional(),
    change_justification: z.string().optional(),
    itar_controlled: z.boolean().optional(),
    eccn: z.string().max(20).optional(),
    export_control_reason: z.string().max(100).optional(),
  })
  .passthrough();
const PatchedDocumentsRequest = z
  .object({
    classification: z.union([ClassificationEnum, NullEnum]).nullable(),
    ai_readable: z.boolean(),
    is_image: z.boolean(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullable(),
    content_type: z.number().int().nullable(),
    object_id: z.string().max(36).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    status: DocumentsStatusEnum,
    document_type: z.string().uuid().nullable(),
    document_type_code: z.string().min(1),
    change_justification: z.string(),
    itar_controlled: z.boolean(),
    eccn: z.string().max(20),
    export_control_reason: z.string().max(100),
  })
  .partial()
  .passthrough();
const DowntimeCategoryEnum = z.enum([
  "planned",
  "unplanned",
  "changeover",
  "calibration",
  "no_work",
  "no_operator",
  "material",
  "quality",
  "other",
]);
const DowntimeEvent = z
  .object({
    id: z.string().uuid(),
    equipment: z.string().uuid().nullish(),
    equipment_name: z.string().nullable(),
    work_center: z.string().uuid().nullish(),
    work_center_name: z.string().nullable(),
    category: DowntimeCategoryEnum,
    reason: z.string().max(200),
    description: z.string().optional(),
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullish(),
    duration_minutes: z.number().nullable(),
    work_order: z.string().uuid().nullish(),
    reported_by: z.number().int(),
    reported_by_name: z.string().nullable(),
    resolved_by: z.number().int().nullable(),
    resolved_by_name: z.string().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedDowntimeEventList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(DowntimeEvent),
  })
  .passthrough();
const DowntimeEventRequest = z
  .object({
    equipment: z.string().uuid().nullish(),
    work_center: z.string().uuid().nullish(),
    category: DowntimeCategoryEnum,
    reason: z.string().min(1).max(200),
    description: z.string().optional(),
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullish(),
    work_order: z.string().uuid().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedDowntimeEventRequest = z
  .object({
    equipment: z.string().uuid().nullable(),
    work_center: z.string().uuid().nullable(),
    category: DowntimeCategoryEnum,
    reason: z.string().min(1).max(200),
    description: z.string(),
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullable(),
    work_order: z.string().uuid().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const UserSelect = z
  .object({
    id: z.number().int(),
    username: z.string(),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
    email: z.string().max(254).email().optional(),
    full_name: z.string(),
    is_active: z.boolean(),
  })
  .passthrough();
const PaginatedUserSelectList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(UserSelect),
  })
  .passthrough();
const EquipmentsStatusEnum = z.enum([
  "in_service",
  "out_of_service",
  "in_calibration",
  "in_maintenance",
  "retired",
]);
const Equipments = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    equipment_type: z.string().uuid().nullish(),
    equipment_type_name: z.string(),
    serial_number: z.string().max(100).optional(),
    manufacturer: z.string().max(100).optional(),
    model_number: z.string().max(100).optional(),
    location: z.string().max(100).optional(),
    status: EquipmentsStatusEnum.optional(),
    notes: z.string().optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedEquipmentsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Equipments),
  })
  .passthrough();
const EquipmentsRequest = z
  .object({
    name: z.string().min(1).max(100),
    equipment_type: z.string().uuid().nullish(),
    serial_number: z.string().max(100).optional(),
    manufacturer: z.string().max(100).optional(),
    model_number: z.string().max(100).optional(),
    location: z.string().max(100).optional(),
    status: EquipmentsStatusEnum.optional(),
    notes: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const EquipmentType = z
  .object({
    id: z.string().uuid(),
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    description: z.string().optional(),
    requires_calibration: z.boolean().optional(),
    default_calibration_interval_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullish(),
    is_portable: z.boolean().optional(),
    track_downtime: z.boolean().optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const PaginatedEquipmentTypeList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(EquipmentType),
  })
  .passthrough();
const EquipmentTypeRequest = z
  .object({
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    description: z.string().optional(),
    requires_calibration: z.boolean().optional(),
    default_calibration_interval_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullish(),
    is_portable: z.boolean().optional(),
    track_downtime: z.boolean().optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const PatchedEquipmentTypeRequest = z
  .object({
    external_id: z.string().max(255).nullable(),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    description: z.string(),
    requires_calibration: z.boolean(),
    default_calibration_interval_days: z
      .number()
      .int()
      .gte(0)
      .lte(2147483647)
      .nullable(),
    is_portable: z.boolean(),
    track_downtime: z.boolean(),
    tenant: z.string().uuid().nullable(),
    previous_version: z.string().uuid().nullable(),
  })
  .partial()
  .passthrough();
const PatchedEquipmentsRequest = z
  .object({
    name: z.string().min(1).max(100),
    equipment_type: z.string().uuid().nullable(),
    serial_number: z.string().max(100),
    manufacturer: z.string().max(100),
    model_number: z.string().max(100),
    location: z.string().max(100),
    status: EquipmentsStatusEnum,
    notes: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const QualityErrorsList = z
  .object({
    id: z.string().uuid(),
    error_name: z.string().max(50),
    error_example: z.string(),
    part_type: z.string().uuid().nullish(),
    part_type_name: z.string(),
    requires_3d_annotation: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedQualityErrorsListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(QualityErrorsList),
  })
  .passthrough();
const QualityErrorsListRequest = z
  .object({
    error_name: z.string().min(1).max(50),
    error_example: z.string().min(1),
    part_type: z.string().uuid().nullish(),
    requires_3d_annotation: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedQualityErrorsListRequest = z
  .object({
    error_name: z.string().min(1).max(50),
    error_example: z.string().min(1),
    part_type: z.string().uuid().nullable(),
    requires_3d_annotation: z.boolean(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const QualityReportStatusEnum = z.enum(["PASS", "FAIL", "PENDING"]);
const QualityReports = z
  .object({
    id: z.string().uuid(),
    report_number: z.string(),
    step: z.string().uuid().nullish(),
    part: z.string().uuid().nullish(),
    machine: z.string().uuid().nullish(),
    operators: z.array(z.number().int()).optional(),
    sampling_method: z.string().max(50).optional(),
    status: QualityReportStatusEnum,
    status_display: z.string(),
    description: z.string().max(300).nullish(),
    file: z.string().uuid().nullish(),
    created_at: z.string().datetime({ offset: true }),
    errors: z.array(z.string().uuid()),
    sampling_audit_log: z.string().uuid().nullish(),
    detected_by: z.number().int().nullish(),
    detected_by_info: z.object({}).partial().passthrough().nullable(),
    verified_by: z.number().int().nullish(),
    verified_by_info: z.object({}).partial().passthrough().nullable(),
    is_first_piece: z.boolean().optional(),
    part_info: z.object({}).partial().passthrough().nullable(),
    step_info: z.object({}).partial().passthrough().nullable(),
    machine_info: z.object({}).partial().passthrough().nullable(),
    operators_info: z.array(z.unknown()),
    errors_info: z.array(z.unknown()),
    file_info: z.object({}).partial().passthrough().nullable(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedQualityReportsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(QualityReports),
  })
  .passthrough();
const ValuePassFailEnum = z.enum(["PASS", "FAIL"]);
const BlankEnum = z.unknown();
const MeasurementResultRequest = z
  .object({
    definition: z.string().uuid(),
    value_numeric: z.number().nullish(),
    value_pass_fail: z
      .union([ValuePassFailEnum, BlankEnum, NullEnum])
      .nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const QualityReportsRequest = z
  .object({
    step: z.string().uuid().nullish(),
    part: z.string().uuid().nullish(),
    machine: z.string().uuid().nullish(),
    operators: z.array(z.number().int()).optional(),
    sampling_method: z.string().min(1).max(50).optional(),
    status: QualityReportStatusEnum,
    description: z.string().max(300).nullish(),
    file: z.string().uuid().nullish(),
    measurements: z.array(MeasurementResultRequest),
    sampling_audit_log: z.string().uuid().nullish(),
    detected_by: z.number().int().nullish(),
    verified_by: z.number().int().nullish(),
    is_first_piece: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedQualityReportsRequest = z
  .object({
    step: z.string().uuid().nullable(),
    part: z.string().uuid().nullable(),
    machine: z.string().uuid().nullable(),
    operators: z.array(z.number().int()),
    sampling_method: z.string().min(1).max(50),
    status: QualityReportStatusEnum,
    description: z.string().max(300).nullable(),
    file: z.string().uuid().nullable(),
    measurements: z.array(MeasurementResultRequest),
    sampling_audit_log: z.string().uuid().nullable(),
    detected_by: z.number().int().nullable(),
    verified_by: z.number().int().nullable(),
    is_first_piece: z.boolean(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const PaginatedFishboneList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Fishbone),
  })
  .passthrough();
const FishboneRequest = z
  .object({
    rca_record: z.string().uuid(),
    problem_statement: z.string().min(1),
    man_causes: z.unknown().optional(),
    machine_causes: z.unknown().optional(),
    material_causes: z.unknown().optional(),
    method_causes: z.unknown().optional(),
    measurement_causes: z.unknown().optional(),
    environment_causes: z.unknown().optional(),
    identified_root_cause: z.string().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedFishboneRequest = z
  .object({
    rca_record: z.string().uuid(),
    problem_statement: z.string().min(1),
    man_causes: z.unknown(),
    machine_causes: z.unknown(),
    material_causes: z.unknown(),
    method_causes: z.unknown(),
    measurement_causes: z.unknown(),
    environment_causes: z.unknown(),
    identified_root_cause: z.string().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const PaginatedFiveWhysList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(FiveWhys),
  })
  .passthrough();
const FiveWhysRequest = z
  .object({
    rca_record: z.string().uuid(),
    why_1_question: z.string().nullish(),
    why_1_answer: z.string().nullish(),
    why_2_question: z.string().nullish(),
    why_2_answer: z.string().nullish(),
    why_3_question: z.string().nullish(),
    why_3_answer: z.string().nullish(),
    why_4_question: z.string().nullish(),
    why_4_answer: z.string().nullish(),
    why_5_question: z.string().nullish(),
    why_5_answer: z.string().nullish(),
    identified_root_cause: z.string().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedFiveWhysRequest = z
  .object({
    rca_record: z.string().uuid(),
    why_1_question: z.string().nullable(),
    why_1_answer: z.string().nullable(),
    why_2_question: z.string().nullable(),
    why_2_answer: z.string().nullable(),
    why_3_question: z.string().nullable(),
    why_3_answer: z.string().nullable(),
    why_4_question: z.string().nullable(),
    why_4_answer: z.string().nullable(),
    why_5_question: z.string().nullable(),
    why_5_answer: z.string().nullable(),
    identified_root_cause: z.string().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const Group = z
  .object({
    id: z.number().int(),
    name: z.string().max(150),
    description: z.string().nullable(),
    user_count: z.number().int(),
    users: z.array(z.object({}).partial().passthrough()),
    permissions: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const PaginatedGroupList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Group),
  })
  .passthrough();
const GroupRequest = z
  .object({ name: z.string().min(1).max(150) })
  .passthrough();
const PatchedGroupRequest = z
  .object({ name: z.string().min(1).max(150) })
  .partial()
  .passthrough();
const GroupAddPermissionsInputRequest = z
  .object({ permission_ids: z.array(z.number().int()) })
  .passthrough();
const GroupAddPermissionsResponse = z
  .object({ detail: z.string(), added_count: z.number().int(), group: Group })
  .passthrough();
const GroupAddUsersInputRequest = z
  .object({ user_ids: z.array(z.number().int()) })
  .passthrough();
const GroupAddUsersResponse = z
  .object({ detail: z.string(), group: Group })
  .passthrough();
const GroupRemovePermissionsInputRequest = z
  .object({ permission_ids: z.array(z.number().int()) })
  .passthrough();
const GroupRemovePermissionsResponse = z
  .object({ detail: z.string(), removed_count: z.number().int(), group: Group })
  .passthrough();
const GroupRemoveUsersInputRequest = z
  .object({ user_ids: z.array(z.number().int()) })
  .passthrough();
const GroupRemoveUsersResponse = z
  .object({ detail: z.string(), group: Group })
  .passthrough();
const GroupSetPermissionsInputRequest = z
  .object({ permission_ids: z.array(z.number().int()) })
  .passthrough();
const GroupSetPermissionsResponse = z
  .object({ detail: z.string(), group: Group })
  .passthrough();
const AvailablePermissionResponse = z
  .object({
    id: z.number().int(),
    codename: z.string(),
    name: z.string(),
    content_type: z.string(),
  })
  .passthrough();
const AvailableUserResponse = z
  .object({
    id: z.number().int(),
    email: z.string().email(),
    first_name: z.string(),
    last_name: z.string(),
    groups: z.array(z.string()),
  })
  .passthrough();
const PaginatedAvailableUserResponseList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(AvailableUserResponse),
  })
  .passthrough();
const HarvestedComponentRequest = z
  .object({
    core: z.string().uuid(),
    component_type: z.string().uuid(),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string().optional(),
    position: z.string().max(50).optional(),
    original_part_number: z.string().max(100).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedHarvestedComponentRequest = z
  .object({
    core: z.string().uuid(),
    component_type: z.string().uuid(),
    condition_grade: ConditionGradeEnum,
    condition_notes: z.string(),
    position: z.string().max(50),
    original_part_number: z.string().max(100),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const HarvestedComponentAcceptRequest = z
  .object({ erp_id: z.string().nullable() })
  .partial()
  .passthrough();
const AcceptToInventoryResponse = z
  .object({
    component: HarvestedComponent,
    part_id: z.string().uuid(),
    part_erp_id: z.string(),
  })
  .passthrough();
const HarvestedComponentScrapRequest = z
  .object({ reason: z.string().default("") })
  .partial()
  .passthrough();
const HeatMapAnnotationsSeverityEnum = z.enum([
  "low",
  "medium",
  "high",
  "critical",
]);
const HeatMapAnnotations = z
  .object({
    id: z.string().uuid(),
    model: z.string().uuid(),
    model_display: z.string(),
    part: z.string().uuid(),
    part_display: z.string(),
    position_x: z.number(),
    position_y: z.number(),
    position_z: z.number(),
    measurement_value: z.number().nullish(),
    defect_type: z.string().max(255).nullish(),
    severity: z
      .union([HeatMapAnnotationsSeverityEnum, BlankEnum, NullEnum])
      .nullish(),
    notes: z.string().optional(),
    quality_reports: z.array(z.string().uuid()).optional(),
    created_by: z.number().int().nullable(),
    created_by_display: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
  })
  .passthrough();
const PaginatedHeatMapAnnotationsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(HeatMapAnnotations),
  })
  .passthrough();
const HeatMapAnnotationsRequest = z
  .object({
    model: z.string().uuid(),
    part: z.string().uuid(),
    position_x: z.number(),
    position_y: z.number(),
    position_z: z.number(),
    measurement_value: z.number().nullish(),
    defect_type: z.string().max(255).nullish(),
    severity: z
      .union([HeatMapAnnotationsSeverityEnum, BlankEnum, NullEnum])
      .nullish(),
    notes: z.string().optional(),
    quality_reports: z.array(z.string().uuid()).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedHeatMapAnnotationsRequest = z
  .object({
    model: z.string().uuid(),
    part: z.string().uuid(),
    position_x: z.number(),
    position_y: z.number(),
    position_z: z.number(),
    measurement_value: z.number().nullable(),
    defect_type: z.string().max(255).nullable(),
    severity: z
      .union([HeatMapAnnotationsSeverityEnum, BlankEnum, NullEnum])
      .nullable(),
    notes: z.string(),
    quality_reports: z.array(z.string().uuid()),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const DefectTypeFacet = z
  .object({ value: z.string(), count: z.number().int() })
  .passthrough();
const SeverityFacet = z
  .object({ value: z.string(), count: z.number().int() })
  .passthrough();
const HeatMapFacetsResponse = z
  .object({
    defect_types: z.array(DefectTypeFacet),
    severities: z.array(SeverityFacet),
    total_count: z.number().int(),
  })
  .passthrough();
const ExternalAPIOrderIdentifier = z
  .object({
    id: z.string().uuid(),
    customer_display_name: z.string(),
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    stage_name: z.string().max(100),
    API_id: z.string().max(50),
    pipeline_id: z.string().max(50).nullish(),
    display_order: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    last_synced_at: z.string().datetime({ offset: true }).nullish(),
    include_in_progress: z.boolean().optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const ExternalAPIOrderIdentifierRequest = z
  .object({
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    stage_name: z.string().min(1).max(100),
    API_id: z.string().min(1).max(50),
    pipeline_id: z.string().max(50).nullish(),
    display_order: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    last_synced_at: z.string().datetime({ offset: true }).nullish(),
    include_in_progress: z.boolean().optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const PatchedExternalAPIOrderIdentifierRequest = z
  .object({
    external_id: z.string().max(255).nullable(),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    stage_name: z.string().min(1).max(100),
    API_id: z.string().min(1).max(50),
    pipeline_id: z.string().max(50).nullable(),
    display_order: z.number().int().gte(-2147483648).lte(2147483647),
    last_synced_at: z.string().datetime({ offset: true }).nullable(),
    include_in_progress: z.boolean(),
    tenant: z.string().uuid().nullable(),
    previous_version: z.string().uuid().nullable(),
  })
  .partial()
  .passthrough();
const MaterialLotStatusEnum = z.enum([
  "received",
  "in_use",
  "consumed",
  "scrapped",
  "quarantine",
]);
const MaterialLot = z
  .object({
    id: z.string().uuid(),
    lot_number: z.string().max(100),
    parent_lot: z.string().uuid().nullish(),
    parent_lot_number: z.string().nullable(),
    material_type: z.string().uuid().nullish(),
    material_type_name: z.string().nullable(),
    material_description: z.string().max(200).optional(),
    supplier: z.string().uuid().nullish(),
    supplier_name: z.string().nullable(),
    supplier_lot_number: z.string().max(100).optional(),
    received_date: z.string(),
    received_by: z.number().int(),
    quantity: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    quantity_remaining: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().max(20),
    status: MaterialLotStatusEnum.optional(),
    manufacture_date: z.string().nullish(),
    expiration_date: z.string().nullish(),
    certificate_of_conformance: z.string().url().nullish(),
    storage_location: z.string().max(100).optional(),
    child_lot_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedMaterialLotList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(MaterialLot),
  })
  .passthrough();
const MaterialLotRequest = z
  .object({
    lot_number: z.string().min(1).max(100),
    parent_lot: z.string().uuid().nullish(),
    material_type: z.string().uuid().nullish(),
    material_description: z.string().max(200).optional(),
    supplier: z.string().uuid().nullish(),
    supplier_lot_number: z.string().max(100).optional(),
    received_date: z.string(),
    quantity: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().min(1).max(20),
    status: MaterialLotStatusEnum.optional(),
    manufacture_date: z.string().nullish(),
    expiration_date: z.string().nullish(),
    certificate_of_conformance: z.instanceof(File).nullish(),
    storage_location: z.string().max(100).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedMaterialLotRequest = z
  .object({
    lot_number: z.string().min(1).max(100),
    parent_lot: z.string().uuid().nullable(),
    material_type: z.string().uuid().nullable(),
    material_description: z.string().max(200),
    supplier: z.string().uuid().nullable(),
    supplier_lot_number: z.string().max(100),
    received_date: z.string(),
    quantity: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    unit_of_measure: z.string().min(1).max(20),
    status: MaterialLotStatusEnum,
    manufacture_date: z.string().nullable(),
    expiration_date: z.string().nullable(),
    certificate_of_conformance: z.instanceof(File).nullable(),
    storage_location: z.string().max(100),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const MaterialLotSplitRequest = z
  .object({
    quantity: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    reason: z.string().optional().default(""),
  })
  .passthrough();
const MaterialUsage = z
  .object({
    id: z.string().uuid(),
    lot: z.string().uuid().nullish(),
    lot_number: z.string().nullable(),
    harvested_component: z.string().uuid().nullish(),
    part: z.string().uuid(),
    part_erp_id: z.string(),
    work_order: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    qty_consumed: z.string().regex(/^-?\d{0,8}(?:\.\d{0,4})?$/),
    consumed_at: z.string().datetime({ offset: true }),
    consumed_by: z.number().int(),
    consumed_by_name: z.string(),
    is_substitute: z.boolean().optional(),
    substitution_reason: z.string().max(200).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedMaterialUsageList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(MaterialUsage),
  })
  .passthrough();
const TypeEnum = z.enum(["NUMERIC", "PASS_FAIL"]);
const MeasurementDefinition = z
  .object({
    id: z.string().uuid(),
    label: z.string().max(100),
    step_name: z.string(),
    unit: z.string().max(50).optional(),
    nominal: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    upper_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    lower_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    required: z.boolean().optional(),
    type: TypeEnum,
    step: z.string().uuid(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedMeasurementDefinitionList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(MeasurementDefinition),
  })
  .passthrough();
const MeasurementDefinitionRequest = z
  .object({
    label: z.string().min(1).max(100),
    unit: z.string().max(50).optional(),
    nominal: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    upper_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    lower_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    required: z.boolean().optional(),
    type: TypeEnum,
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedMeasurementDefinitionRequest = z
  .object({
    label: z.string().min(1).max(100),
    unit: z.string().max(50),
    nominal: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullable(),
    upper_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullable(),
    lower_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullable(),
    required: z.boolean(),
    type: TypeEnum,
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const NotificationTypeEnum = z.enum([
  "WEEKLY_REPORT",
  "CAPA_REMINDER",
  "APPROVAL_REQUEST",
  "APPROVAL_DECISION",
  "APPROVAL_ESCALATION",
]);
const ChannelTypeEnum = z.enum(["email", "in_app", "sms"]);
const NotificationTaskStatusEnum = z.enum([
  "pending",
  "sent",
  "failed",
  "cancelled",
]);
const IntervalTypeEnum = z.enum(["fixed", "deadline_based"]);
const NotificationSchedule = z
  .object({
    interval_type: IntervalTypeEnum,
    day_of_week: z.number().int().gte(0).lte(6).nullish(),
    time: z.string().nullish(),
    interval_weeks: z.number().int().gte(1).nullish(),
    escalation_tiers: z.array(z.array(z.number()).min(2).max(2)).nullish(),
  })
  .passthrough();
const NotificationPreference = z
  .object({
    id: z.number().int(),
    notification_type: NotificationTypeEnum,
    notification_type_display: z.string(),
    channel_type: ChannelTypeEnum.optional(),
    channel_type_display: z.string(),
    status: NotificationTaskStatusEnum,
    status_display: z.string(),
    schedule: NotificationSchedule.optional(),
    next_send_at: z.string().datetime({ offset: true }),
    next_send_at_display: z.string().datetime({ offset: true }).nullable(),
    last_sent_at: z.string().datetime({ offset: true }).nullable(),
    last_sent_at_display: z.string().datetime({ offset: true }).nullable(),
    attempt_count: z.number().int(),
    max_attempts: z.number().int().gte(-2147483648).lte(2147483647).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PaginatedNotificationPreferenceList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(NotificationPreference),
  })
  .passthrough();
const NotificationScheduleRequest = z
  .object({
    interval_type: IntervalTypeEnum,
    day_of_week: z.number().int().gte(0).lte(6).nullish(),
    time: z.string().nullish(),
    interval_weeks: z.number().int().gte(1).nullish(),
    escalation_tiers: z.array(z.array(z.number()).min(2).max(2)).nullish(),
  })
  .passthrough();
const NotificationPreferenceRequest = z
  .object({
    notification_type: NotificationTypeEnum,
    channel_type: ChannelTypeEnum.optional(),
    schedule: NotificationScheduleRequest.optional(),
    max_attempts: z.number().int().gte(-2147483648).lte(2147483647).nullish(),
  })
  .passthrough();
const PatchedNotificationPreferenceRequest = z
  .object({
    notification_type: NotificationTypeEnum,
    channel_type: ChannelTypeEnum,
    schedule: NotificationScheduleRequest,
    max_attempts: z.number().int().gte(-2147483648).lte(2147483647).nullable(),
  })
  .partial()
  .passthrough();
const TestSendResponse = z
  .object({ status: z.string(), message: z.string() })
  .passthrough();
const AvailableNotificationTypes = z
  .object({ notification_types: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const OrdersStatusEnum = z.enum([
  "RFI",
  "PENDING",
  "IN_PROGRESS",
  "COMPLETED",
  "ON_HOLD",
  "CANCELLED",
]);
const Orders = z
  .object({
    id: z.string().uuid(),
    order_number: z.string(),
    name: z.string().max(200),
    customer_note: z.string().nullish(),
    latest_note: z.object({}).partial().passthrough().nullable(),
    notes_timeline: z.array(z.unknown()),
    customer: z.number().int().nullish(),
    customer_info: z.object({}).partial().passthrough().nullable(),
    company: z.string().uuid().nullish(),
    company_info: z.object({}).partial().passthrough().nullable(),
    estimated_completion: z.string().nullish(),
    original_completion_date: z.string().datetime({ offset: true }).nullable(),
    order_status: OrdersStatusEnum,
    current_hubspot_gate: z.string().uuid().nullish(),
    parts_summary: z.object({}).partial().passthrough().nullable(),
    process_stages: z.array(z.unknown()),
    gate_info: z.object({}).partial().passthrough().nullable(),
    customer_first_name: z.string().nullable(),
    customer_last_name: z.string().nullable(),
    company_name: z.string().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedOrdersList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Orders),
  })
  .passthrough();
const OrdersRequest = z
  .object({
    name: z.string().min(1).max(200),
    customer_note: z.string().nullish(),
    customer: z.number().int().nullish(),
    company: z.string().uuid().nullish(),
    estimated_completion: z.string().nullish(),
    order_status: OrdersStatusEnum,
    current_hubspot_gate: z.string().uuid().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedOrdersRequest = z
  .object({
    name: z.string().min(1).max(200),
    customer_note: z.string().nullable(),
    customer: z.number().int().nullable(),
    company: z.string().uuid().nullable(),
    estimated_completion: z.string().nullable(),
    order_status: OrdersStatusEnum,
    current_hubspot_gate: z.string().uuid().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const VisibilityEnum = z.enum(["visible", "internal"]);
const AddNoteInputRequest = z
  .object({
    message: z.string().min(1),
    visibility: VisibilityEnum.optional().default("visible"),
  })
  .passthrough();
const StepIncrementInputRequest = z
  .object({ step_id: z.string().uuid() })
  .passthrough();
const StepIncrementResponse = z
  .object({ advanced: z.number().int(), total: z.number().int() })
  .passthrough();
const PartsStatusEnum = z.enum([
  "PENDING",
  "IN_PROGRESS",
  "AWAITING_QA",
  "READY FOR NEXT STEP",
  "COMPLETED",
  "QUARANTINED",
  "REWORK_NEEDED",
  "REWORK_IN_PROGRESS",
  "SCRAPPED",
  "CANCELLED",
]);
const BulkAddPartsInputRequest = z
  .object({
    part_type: z.string().uuid(),
    step: z.string().uuid(),
    quantity: z.number().int(),
    part_status: PartsStatusEnum.optional().default("PENDING"),
    work_order: z.string().uuid().optional(),
    erp_id_start: z.number().int().optional().default(1),
  })
  .passthrough();
const BulkRemovePartsInputRequest = z
  .object({ ids: z.array(z.string().uuid()) })
  .passthrough();
const StepDistributionResponse = z
  .object({ id: z.string().uuid(), count: z.number().int(), name: z.string() })
  .passthrough();
const PaginatedStepDistributionResponseList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(StepDistributionResponse),
  })
  .passthrough();
const api_Orders_import_create_Body = z
  .object({
    file: z.instanceof(File),
    mode: z.enum(["create", "update", "upsert"]).optional(),
  })
  .passthrough();
const ImportQueued = z
  .object({
    task_id: z.string(),
    status: z.string(),
    total_rows: z.number().int(),
    message: z.string(),
  })
  .passthrough();
const ImportSummary = z
  .object({
    total: z.number().int(),
    created: z.number().int(),
    updated: z.number().int(),
    errors: z.number().int(),
  })
  .passthrough();
const ImportResponse = z
  .object({
    summary: ImportSummary,
    results: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const ImportPreviewResponse = z
  .object({
    total_rows: z.number().int(),
    columns: z.array(z.object({}).partial().passthrough()),
    sample_data: z.array(z.object({}).partial().passthrough()),
    model_fields: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const ImportStatusResponse = z
  .object({
    task_id: z.string(),
    status: z.string(),
    progress: z.object({}).partial().passthrough(),
    result: z.object({}).partial().passthrough().optional(),
  })
  .passthrough();
const PartTypes = z
  .object({
    id: z.string().uuid(),
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    ID_prefix: z.string().max(50).nullish(),
    ERP_id: z.string().max(50).nullish(),
    itar_controlled: z.boolean().optional(),
    eccn: z.string().max(20).optional(),
    usml_category: z.string().max(10).optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const PaginatedPartTypesList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(PartTypes),
  })
  .passthrough();
const PartTypesRequest = z
  .object({
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullish(),
    ERP_id: z.string().max(50).nullish(),
    itar_controlled: z.boolean().optional(),
    eccn: z.string().max(20).optional(),
    usml_category: z.string().max(10).optional(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
  })
  .passthrough();
const PatchedPartTypesRequest = z
  .object({
    external_id: z.string().max(255).nullable(),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullable(),
    ERP_id: z.string().max(50).nullable(),
    itar_controlled: z.boolean(),
    eccn: z.string().max(20),
    usml_category: z.string().max(10),
    tenant: z.string().uuid().nullable(),
    previous_version: z.string().uuid().nullable(),
  })
  .partial()
  .passthrough();
const PartTypeSelect = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    ID_prefix: z.string().max(50).nullish(),
  })
  .passthrough();
const PaginatedPartTypeSelectList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(PartTypeSelect),
  })
  .passthrough();
const Parts = z
  .object({
    id: z.string().uuid(),
    ERP_id: z.string().max(50),
    part_status: PartsStatusEnum.optional(),
    requires_sampling: z.boolean(),
    order: z.string().uuid().optional(),
    part_type: z.string().uuid(),
    part_type_info: z.object({}).partial().passthrough().nullable(),
    step: z.string().uuid(),
    step_info: z.object({}).partial().passthrough().nullable(),
    work_order: z.string().uuid().nullish(),
    quality_info: z.object({}).partial().passthrough().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    has_error: z.boolean(),
    part_type_name: z.string().nullable(),
    process_name: z.string().nullable(),
    order_name: z.string().nullable(),
    step_description: z.string(),
    work_order_erp_id: z.string().nullable(),
    is_from_batch_process: z.boolean(),
    sampling_rule: z.string().uuid().nullish(),
    sampling_ruleset: z.string().uuid().nullish(),
    sampling_context: z.unknown().optional(),
    process: z.string().uuid().nullable(),
    total_rework_count: z.number().int(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedPartsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Parts),
  })
  .passthrough();
const PartsRequest = z
  .object({
    ERP_id: z.string().min(1).max(50),
    part_status: PartsStatusEnum.optional(),
    order: z.string().uuid().optional(),
    part_type: z.string().uuid(),
    step: z.string().uuid(),
    work_order: z.string().uuid().nullish(),
    sampling_rule: z.string().uuid().nullish(),
    sampling_ruleset: z.string().uuid().nullish(),
    sampling_context: z.unknown().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedPartsRequest = z
  .object({
    ERP_id: z.string().min(1).max(50),
    part_status: PartsStatusEnum,
    order: z.string().uuid(),
    part_type: z.string().uuid(),
    step: z.string().uuid(),
    work_order: z.string().uuid().nullable(),
    sampling_rule: z.string().uuid().nullable(),
    sampling_ruleset: z.string().uuid().nullable(),
    sampling_context: z.unknown(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const PartIncrementInputRequest = z
  .object({ decision: z.string().min(1) })
  .partial()
  .passthrough();
const TravelerStepStatusEnum = z.enum([
  "COMPLETED",
  "IN_PROGRESS",
  "PENDING",
  "SKIPPED",
]);
const TravelerOperator = z
  .object({
    id: z.number().int(),
    name: z.string(),
    employee_id: z.string().nullable(),
  })
  .passthrough();
const TravelerApproval = z
  .object({
    id: z.number().int(),
    name: z.string(),
    approved_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const TravelerEquipment = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    calibration_due: z.string().nullable(),
  })
  .passthrough();
const TravelerMeasurement = z
  .object({
    definition_id: z.string().uuid(),
    label: z.string(),
    nominal: z.number().nullable(),
    upper_tol: z.number().nullable(),
    lower_tol: z.number().nullable(),
    actual_value: z.number().nullable(),
    unit: z.string().nullable(),
    passed: z.boolean(),
    recorded_at: z.string().datetime({ offset: true }),
    recorded_by: z.string().nullable(),
  })
  .passthrough();
const QualityStatusEnum = z.enum(["PASS", "FAIL", "CONDITIONAL"]);
const TravelerDefect = z
  .object({
    error_type_id: z.string().uuid().nullable(),
    error_name: z.string(),
    severity: z.string().nullable(),
    disposition: z.string().nullable(),
  })
  .passthrough();
const TravelerMaterial = z
  .object({
    material_name: z.string(),
    lot_number: z.string().nullable(),
    quantity: z.number(),
  })
  .passthrough();
const TravelerAttachment = z
  .object({
    id: z.string().uuid(),
    file_name: z.string(),
    file_url: z.string(),
    uploaded_at: z.string().datetime({ offset: true }),
    classification: z.string().nullable(),
  })
  .passthrough();
const TravelerStepEntry = z
  .object({
    step_id: z.string().uuid(),
    step_name: z.string(),
    step_order: z.number().int(),
    visit_number: z.number().int().optional().default(1),
    status: TravelerStepStatusEnum,
    started_at: z.string().datetime({ offset: true }).nullable(),
    completed_at: z.string().datetime({ offset: true }).nullable(),
    duration_seconds: z.number().int().nullable(),
    operator: TravelerOperator.nullable(),
    approved_by: TravelerApproval.nullable(),
    equipment_used: z.array(TravelerEquipment),
    measurements: z.array(TravelerMeasurement),
    quality_status: z.union([QualityStatusEnum, NullEnum]).nullable(),
    defects_found: z.array(TravelerDefect),
    materials_used: z.array(TravelerMaterial),
    attachments: z.array(TravelerAttachment),
  })
  .passthrough();
const PartTravelerResponse = z
  .object({
    part_id: z.string().uuid(),
    part_erp_id: z.string(),
    work_order_id: z.string().uuid().nullable(),
    process_name: z.string().nullable(),
    current_step_id: z.string().uuid().nullable(),
    current_step_name: z.string().nullable(),
    part_status: z.string(),
    traveler: z.array(TravelerStepEntry),
  })
  .passthrough();
const PartSelect = z
  .object({
    id: z.string().uuid(),
    ERP_id: z.string().max(50),
    part_type: z.string().uuid().nullish(),
    part_type_name: z.string().nullable(),
    part_status: PartsStatusEnum.optional(),
  })
  .passthrough();
const PaginatedPartSelectList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(PartSelect),
  })
  .passthrough();
const StepTypeEnum = z.enum([
  "task",
  "start",
  "decision",
  "rework",
  "timer",
  "terminal",
]);
const DecisionTypeEnum = z.enum(["qa_result", "measurement", "manual"]);
const TerminalStatusEnum = z.enum([
  "completed",
  "shipped",
  "stock",
  "scrapped",
  "returned",
  "awaiting_pickup",
  "core_banked",
  "rma_closed",
]);
const RevisitAssignmentEnum = z.enum(["any", "same", "different", "role"]);
const Step = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    description: z.string().nullish(),
    part_type: z.string().uuid(),
    part_type_name: z.string(),
    expected_duration: z.string().nullish(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    block_on_quarantine: z.boolean().optional(),
    pass_threshold: z.number().optional(),
    step_type: StepTypeEnum.optional(),
    is_decision_point: z.boolean().optional(),
    decision_type: z.union([DecisionTypeEnum, BlankEnum]).optional(),
    is_terminal: z.boolean().optional(),
    terminal_status: z.union([TerminalStatusEnum, BlankEnum]).optional(),
    max_visits: z.number().int().gte(0).lte(2147483647).nullish(),
    revisit_assignment: RevisitAssignmentEnum.optional(),
  })
  .passthrough();
const ProcessStep = z
  .object({
    id: z.number().int(),
    step: Step,
    order: z.number().int().gte(-2147483648).lte(2147483647),
    is_entry_point: z.boolean().optional(),
  })
  .passthrough();
const EdgeTypeEnum = z.enum(["default", "alternate", "escalation"]);
const ConditionOperatorEnum = z.enum(["gte", "lte", "eq"]);
const StepEdge = z
  .object({
    id: z.number().int(),
    from_step: z.string().uuid(),
    to_step: z.string().uuid(),
    edge_type: EdgeTypeEnum.optional(),
    from_step_name: z.string(),
    to_step_name: z.string(),
    condition_measurement: z.string().uuid().nullish(),
    condition_operator: z.union([ConditionOperatorEnum, BlankEnum]).optional(),
    condition_value: z
      .string()
      .regex(/^-?\d{0,6}(?:\.\d{0,4})?$/)
      .nullish(),
  })
  .passthrough();
const ProcessStatusEnum = z.enum([
  "draft",
  "pending_approval",
  "approved",
  "deprecated",
]);
const Processes = z
  .object({
    id: z.string().uuid(),
    part_type_name: z.string(),
    process_steps: z.array(ProcessStep),
    step_edges: z.array(StepEdge),
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    is_remanufactured: z.boolean().optional(),
    is_batch_process: z.boolean().optional(),
    status: ProcessStatusEnum.optional(),
    change_description: z.string().nullish(),
    approved_at: z.string().datetime({ offset: true }).nullish(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
    part_type: z.string().uuid(),
    approved_by: z.number().int().nullish(),
  })
  .passthrough();
const PaginatedProcessesList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Processes),
  })
  .passthrough();
const ProcessesRequest = z
  .object({
    external_id: z.string().max(255).nullish(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean().optional(),
    is_batch_process: z.boolean().optional(),
    status: ProcessStatusEnum.optional(),
    change_description: z.string().nullish(),
    approved_at: z.string().datetime({ offset: true }).nullish(),
    tenant: z.string().uuid().nullish(),
    previous_version: z.string().uuid().nullish(),
    part_type: z.string().uuid(),
    approved_by: z.number().int().nullish(),
  })
  .passthrough();
const PatchedProcessesRequest = z
  .object({
    external_id: z.string().max(255).nullable(),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    is_batch_process: z.boolean(),
    status: ProcessStatusEnum,
    change_description: z.string().nullable(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    tenant: z.string().uuid().nullable(),
    previous_version: z.string().uuid().nullable(),
    part_type: z.string().uuid(),
    approved_by: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const ProcessWithSteps = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    is_remanufactured: z.boolean().optional(),
    part_type: z.string().uuid(),
    is_batch_process: z.boolean().optional(),
    process_steps: z.array(ProcessStep),
    step_edges: z.array(StepEdge),
    status: ProcessStatusEnum.optional(),
    change_description: z.string().nullish(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    approved_by: z.number().int().nullable(),
    version: z.number().int(),
    previous_version: z.string().uuid().nullable(),
    is_current_version: z.boolean(),
  })
  .passthrough();
const PaginatedProcessWithStepsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ProcessWithSteps),
  })
  .passthrough();
const ProcessWithStepsRequest = z
  .object({
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean().optional(),
    part_type: z.string().uuid(),
    is_batch_process: z.boolean().optional(),
    nodes: z.array(z.object({}).partial().passthrough()).optional(),
    edges: z.array(z.object({}).partial().passthrough()).optional(),
    status: ProcessStatusEnum.optional(),
    change_description: z.string().nullish(),
  })
  .passthrough();
const PatchedProcessWithStepsRequest = z
  .object({
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    part_type: z.string().uuid(),
    is_batch_process: z.boolean(),
    nodes: z.array(z.object({}).partial().passthrough()),
    edges: z.array(z.object({}).partial().passthrough()),
    status: ProcessStatusEnum,
    change_description: z.string().nullable(),
  })
  .partial()
  .passthrough();
const DuplicateProcessRequestRequest = z
  .object({ name_suffix: z.string().min(1).default(" (Copy)") })
  .partial()
  .passthrough();
const SubmitProcessForApprovalRequestRequest = z
  .object({ reason: z.string().min(1) })
  .partial()
  .passthrough();
const SubmitProcessForApprovalResponse = z
  .object({
    process: ProcessWithSteps,
    approval_request_id: z.string().uuid(),
    approval_number: z.string(),
  })
  .passthrough();
const CurrentStateEnum = z.enum(["OPEN", "IN_PROGRESS", "CLOSED"]);
const DispositionTypeEnum = z.enum([
  "REWORK",
  "REPAIR",
  "SCRAP",
  "USE_AS_IS",
  "RETURN_TO_SUPPLIER",
]);
const QuarantineDisposition = z
  .object({
    id: z.string().uuid(),
    disposition_number: z.string(),
    current_state: CurrentStateEnum.optional(),
    disposition_type: z.union([DispositionTypeEnum, BlankEnum]).optional(),
    severity: SeverityEnum.optional(),
    severity_display: z.string(),
    assigned_to: z.number().int().nullish(),
    description: z.string().optional(),
    resolution_notes: z.string().optional(),
    resolution_completed: z.boolean().optional(),
    resolution_completed_by: z.number().int().nullish(),
    resolution_completed_by_name: z.string(),
    resolution_completed_at: z.string().datetime({ offset: true }).nullish(),
    containment_action: z.string().optional(),
    containment_completed_at: z.string().datetime({ offset: true }).nullish(),
    containment_completed_by: z.number().int().nullish(),
    containment_completed_by_name: z.string(),
    requires_customer_approval: z.boolean().optional(),
    customer_approval_received: z.boolean().optional(),
    customer_approval_reference: z.string().max(100).optional(),
    customer_approval_date: z.string().nullish(),
    scrap_verified: z.boolean().optional(),
    scrap_verification_method: z.string().max(100).optional(),
    scrap_verified_by: z.number().int().nullish(),
    scrap_verified_by_name: z.string(),
    scrap_verified_at: z.string().datetime({ offset: true }).nullish(),
    part: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    step_info: z.object({}).partial().passthrough().nullable(),
    rework_attempt_at_step: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    rework_limit_exceeded: z.boolean(),
    quality_reports: z.array(z.string().uuid()),
    assignee_name: z.string(),
    choices_data: z.object({}).partial().passthrough().nullable(),
    annotation_status: z.object({}).partial().passthrough(),
    can_be_completed: z.boolean(),
    completion_blockers: z.array(z.string()),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedQuarantineDispositionList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(QuarantineDisposition),
  })
  .passthrough();
const QuarantineDispositionRequest = z
  .object({
    current_state: CurrentStateEnum.optional(),
    disposition_type: z.union([DispositionTypeEnum, BlankEnum]).optional(),
    severity: SeverityEnum.optional(),
    assigned_to: z.number().int().nullish(),
    description: z.string().optional(),
    resolution_notes: z.string().optional(),
    resolution_completed: z.boolean().optional(),
    resolution_completed_by: z.number().int().nullish(),
    resolution_completed_at: z.string().datetime({ offset: true }).nullish(),
    containment_action: z.string().optional(),
    containment_completed_at: z.string().datetime({ offset: true }).nullish(),
    containment_completed_by: z.number().int().nullish(),
    requires_customer_approval: z.boolean().optional(),
    customer_approval_received: z.boolean().optional(),
    customer_approval_reference: z.string().max(100).optional(),
    customer_approval_date: z.string().nullish(),
    scrap_verified: z.boolean().optional(),
    scrap_verification_method: z.string().max(100).optional(),
    scrap_verified_by: z.number().int().nullish(),
    scrap_verified_at: z.string().datetime({ offset: true }).nullish(),
    part: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    rework_attempt_at_step: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    quality_reports: z.array(z.string().uuid()),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedQuarantineDispositionRequest = z
  .object({
    current_state: CurrentStateEnum,
    disposition_type: z.union([DispositionTypeEnum, BlankEnum]),
    severity: SeverityEnum,
    assigned_to: z.number().int().nullable(),
    description: z.string(),
    resolution_notes: z.string(),
    resolution_completed: z.boolean(),
    resolution_completed_by: z.number().int().nullable(),
    resolution_completed_at: z.string().datetime({ offset: true }).nullable(),
    containment_action: z.string(),
    containment_completed_at: z.string().datetime({ offset: true }).nullable(),
    containment_completed_by: z.number().int().nullable(),
    requires_customer_approval: z.boolean(),
    customer_approval_received: z.boolean(),
    customer_approval_reference: z.string().max(100),
    customer_approval_date: z.string().nullable(),
    scrap_verified: z.boolean(),
    scrap_verification_method: z.string().max(100),
    scrap_verified_by: z.number().int().nullable(),
    scrap_verified_at: z.string().datetime({ offset: true }).nullable(),
    part: z.string().uuid().nullable(),
    step: z.string().uuid().nullable(),
    rework_attempt_at_step: z.number().int().gte(-2147483648).lte(2147483647),
    quality_reports: z.array(z.string().uuid()),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const PaginatedRcaRecordList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(RcaRecord),
  })
  .passthrough();
const FiveWhysNestedRequest = z
  .object({
    why_1_question: z.string().nullable(),
    why_1_answer: z.string().nullable(),
    why_2_question: z.string().nullable(),
    why_2_answer: z.string().nullable(),
    why_3_question: z.string().nullable(),
    why_3_answer: z.string().nullable(),
    why_4_question: z.string().nullable(),
    why_4_answer: z.string().nullable(),
    why_5_question: z.string().nullable(),
    why_5_answer: z.string().nullable(),
    identified_root_cause: z.string().nullable(),
  })
  .partial()
  .passthrough();
const FishboneNestedRequest = z
  .object({
    problem_statement: z.string().nullable(),
    man_causes: z.string().nullable(),
    machine_causes: z.string().nullable(),
    material_causes: z.string().nullable(),
    method_causes: z.string().nullable(),
    measurement_causes: z.string().nullable(),
    environment_causes: z.string().nullable(),
    identified_root_cause: z.string().nullable(),
  })
  .partial()
  .passthrough();
const RcaRecordRequest = z
  .object({
    capa: z.string().uuid(),
    rca_method: RcaMethodEnum,
    problem_description: z.string().min(1),
    root_cause_summary: z.string().nullish(),
    conducted_by: z.number().int().nullish(),
    conducted_date: z.string().nullish(),
    rca_review_status: RcaReviewStatusEnum.optional(),
    root_cause_verification_status: RootCauseVerificationStatusEnum.optional(),
    root_cause_verified_by: z.number().int().nullish(),
    quality_reports: z.array(z.string().uuid()).optional(),
    dispositions: z.array(z.string().uuid()).optional(),
    five_whys_data: FiveWhysNestedRequest.optional(),
    fishbone_data: FishboneNestedRequest.optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedRcaRecordRequest = z
  .object({
    capa: z.string().uuid(),
    rca_method: RcaMethodEnum,
    problem_description: z.string().min(1),
    root_cause_summary: z.string().nullable(),
    conducted_by: z.number().int().nullable(),
    conducted_date: z.string().nullable(),
    rca_review_status: RcaReviewStatusEnum,
    root_cause_verification_status: RootCauseVerificationStatusEnum,
    root_cause_verified_by: z.number().int().nullable(),
    quality_reports: z.array(z.string().uuid()),
    dispositions: z.array(z.string().uuid()),
    five_whys_data: FiveWhysNestedRequest,
    fishbone_data: FishboneNestedRequest,
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const SamplingRuleSet = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    origin: z.string().max(100).optional(),
    active: z.boolean().optional(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_fallback: z.boolean().optional(),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullish(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullish(),
    part_type: z.string().uuid(),
    part_type_info: z.object({}).partial().passthrough().nullable(),
    process: z.string().uuid().nullish(),
    process_info: z.object({}).partial().passthrough().nullable(),
    step: z.string().uuid(),
    step_info: z.object({}).partial().passthrough().nullable(),
    rules: z.array(z.unknown()),
    created_by: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    modified_by: z.number().int().nullish(),
    updated_at: z.string().datetime({ offset: true }),
    part_type_name: z.string(),
    process_name: z.string(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedSamplingRuleSetList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(SamplingRuleSet),
  })
  .passthrough();
const SamplingRuleSetRequest = z
  .object({
    name: z.string().min(1).max(100),
    origin: z.string().max(100).optional(),
    active: z.boolean().optional(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_fallback: z.boolean().optional(),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullish(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullish(),
    part_type: z.string().uuid(),
    process: z.string().uuid().nullish(),
    step: z.string().uuid(),
    created_by: z.number().int().nullish(),
    modified_by: z.number().int().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedSamplingRuleSetRequest = z
  .object({
    name: z.string().min(1).max(100),
    origin: z.string().max(100),
    active: z.boolean(),
    version: z.number().int().gte(0).lte(2147483647),
    is_fallback: z.boolean(),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullable(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullable(),
    part_type: z.string().uuid(),
    process: z.string().uuid().nullable(),
    step: z.string().uuid(),
    created_by: z.number().int().nullable(),
    modified_by: z.number().int().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const RuleTypeEnum = z.enum([
  "every_nth_part",
  "percentage",
  "random",
  "first_n_parts",
  "last_n_parts",
  "exact_count",
]);
const SamplingRule = z
  .object({
    id: z.string().uuid(),
    rule_type: RuleTypeEnum,
    rule_type_display: z.string(),
    value: z.number().int().gte(0).lte(2147483647).nullish(),
    order: z.number().int().gte(0).lte(2147483647).optional(),
    algorithm_description: z.string().optional(),
    last_validated: z.string().datetime({ offset: true }).nullish(),
    ruleset: z.string().uuid(),
    ruleset_info: z.object({}).partial().passthrough().nullable(),
    created_by: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    modified_by: z.number().int().nullish(),
    updated_at: z.string().datetime({ offset: true }),
    ruletype_name: z.string(),
    ruleset_name: z.string(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedSamplingRuleList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(SamplingRule),
  })
  .passthrough();
const SamplingRuleRequest = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().gte(0).lte(2147483647).nullish(),
    order: z.number().int().gte(0).lte(2147483647).optional(),
    algorithm_description: z.string().min(1).optional(),
    last_validated: z.string().datetime({ offset: true }).nullish(),
    ruleset: z.string().uuid(),
    created_by: z.number().int().nullish(),
    modified_by: z.number().int().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedSamplingRuleRequest = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().gte(0).lte(2147483647).nullable(),
    order: z.number().int().gte(0).lte(2147483647),
    algorithm_description: z.string().min(1),
    last_validated: z.string().datetime({ offset: true }).nullable(),
    ruleset: z.string().uuid(),
    created_by: z.number().int().nullable(),
    modified_by: z.number().int().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const ScheduleSlotStatusEnum = z.enum([
  "scheduled",
  "in_progress",
  "completed",
  "cancelled",
]);
const ScheduleSlot = z
  .object({
    id: z.string().uuid(),
    work_center: z.string().uuid(),
    work_center_name: z.string(),
    shift: z.string().uuid(),
    shift_name: z.string(),
    work_order: z.string().uuid(),
    work_order_erp_id: z.string(),
    scheduled_date: z.string(),
    scheduled_start: z.string().datetime({ offset: true }),
    scheduled_end: z.string().datetime({ offset: true }),
    actual_start: z.string().datetime({ offset: true }).nullish(),
    actual_end: z.string().datetime({ offset: true }).nullish(),
    status: ScheduleSlotStatusEnum.optional(),
    notes: z.string().optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedScheduleSlotList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ScheduleSlot),
  })
  .passthrough();
const ScheduleSlotRequest = z
  .object({
    work_center: z.string().uuid(),
    shift: z.string().uuid(),
    work_order: z.string().uuid(),
    scheduled_date: z.string(),
    scheduled_start: z.string().datetime({ offset: true }),
    scheduled_end: z.string().datetime({ offset: true }),
    actual_start: z.string().datetime({ offset: true }).nullish(),
    actual_end: z.string().datetime({ offset: true }).nullish(),
    status: ScheduleSlotStatusEnum.optional(),
    notes: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedScheduleSlotRequest = z
  .object({
    work_center: z.string().uuid(),
    shift: z.string().uuid(),
    work_order: z.string().uuid(),
    scheduled_date: z.string(),
    scheduled_start: z.string().datetime({ offset: true }),
    scheduled_end: z.string().datetime({ offset: true }),
    actual_start: z.string().datetime({ offset: true }).nullable(),
    actual_end: z.string().datetime({ offset: true }).nullable(),
    status: ScheduleSlotStatusEnum,
    notes: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const Shift = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    code: z.string().max(10),
    start_time: z.string(),
    end_time: z.string(),
    days_of_week: z.string().max(20).optional(),
    is_active: z.boolean().optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedShiftList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Shift),
  })
  .passthrough();
const ShiftRequest = z
  .object({
    name: z.string().min(1).max(50),
    code: z.string().min(1).max(10),
    start_time: z.string(),
    end_time: z.string(),
    days_of_week: z.string().min(1).max(20).optional(),
    is_active: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedShiftRequest = z
  .object({
    name: z.string().min(1).max(50),
    code: z.string().min(1).max(10),
    start_time: z.string(),
    end_time: z.string(),
    days_of_week: z.string().min(1).max(20),
    is_active: z.boolean(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const StepExecutionStatusEnum = z.enum([
  "pending",
  "in_progress",
  "completed",
  "skipped",
]);
const StepExecutionList = z
  .object({
    id: z.string().uuid(),
    part: z.string().uuid(),
    part_erp_id: z.string(),
    part_status: z.string(),
    step: z.string().uuid(),
    step_name: z.string(),
    step_order: z.number().int().nullable(),
    visit_number: z.number().int().gte(0).lte(2147483647).optional(),
    entered_at: z.string().datetime({ offset: true }),
    exited_at: z.string().datetime({ offset: true }).nullish(),
    status: StepExecutionStatusEnum.optional(),
    assigned_to: z.number().int().nullish(),
    assigned_to_name: z.string().nullable(),
    decision_result: z.string().max(50).optional(),
  })
  .passthrough();
const PaginatedStepExecutionListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(StepExecutionList),
  })
  .passthrough();
const StepExecutionRequest = z
  .object({
    part: z.string().uuid(),
    step: z.string().uuid(),
    visit_number: z.number().int().gte(0).lte(2147483647).optional(),
    exited_at: z.string().datetime({ offset: true }).nullish(),
    assigned_to: z.number().int().nullish(),
    completed_by: z.number().int().nullish(),
    next_step: z.string().uuid().nullish(),
    decision_result: z.string().max(50).optional(),
    status: StepExecutionStatusEnum.optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const StepExecution = z
  .object({
    id: z.string().uuid(),
    part: z.string().uuid(),
    step: z.string().uuid(),
    visit_number: z.number().int().gte(0).lte(2147483647).optional(),
    part_info: z.object({}).partial().passthrough().nullable(),
    step_info: z.object({}).partial().passthrough().nullable(),
    entered_at: z.string().datetime({ offset: true }),
    exited_at: z.string().datetime({ offset: true }).nullish(),
    duration_seconds: z.number().nullable(),
    assigned_to: z.number().int().nullish(),
    assigned_to_info: z.object({}).partial().passthrough().nullable(),
    completed_by: z.number().int().nullish(),
    completed_by_info: z.object({}).partial().passthrough().nullable(),
    next_step: z.string().uuid().nullish(),
    decision_result: z.string().max(50).optional(),
    status: StepExecutionStatusEnum.optional(),
    is_active: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedStepExecutionRequest = z
  .object({
    part: z.string().uuid(),
    step: z.string().uuid(),
    visit_number: z.number().int().gte(0).lte(2147483647),
    exited_at: z.string().datetime({ offset: true }).nullable(),
    assigned_to: z.number().int().nullable(),
    completed_by: z.number().int().nullable(),
    next_step: z.string().uuid().nullable(),
    decision_result: z.string().max(50),
    status: StepExecutionStatusEnum,
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const StepDurationStats = z
  .object({
    step_id: z.string().uuid(),
    step_name: z.string(),
    avg_duration_seconds: z.number(),
    min_duration_seconds: z.number(),
    max_duration_seconds: z.number(),
    completed_count: z.number().int(),
  })
  .passthrough();
const PaginatedStepExecutionList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(StepExecution),
  })
  .passthrough();
const WIPSummary = z
  .object({
    step_id: z.string().uuid(),
    step_name: z.string(),
    step_order: z.number().int(),
    is_decision_point: z.boolean(),
    pending_count: z.number().int(),
    in_progress_count: z.number().int(),
    total_active: z.number().int(),
  })
  .passthrough();
const PaginatedWIPSummaryList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(WIPSummary),
  })
  .passthrough();
const Steps = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    expected_duration: z.string().nullish(),
    description: z.string().nullish(),
    block_on_quarantine: z.boolean().optional(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    pass_threshold: z.number().optional(),
    requires_first_piece_inspection: z.boolean().optional(),
    part_type: z.string().uuid(),
    part_type_info: z.object({}).partial().passthrough().nullable(),
    part_type_name: z.string().nullable(),
    step_type: StepTypeEnum.optional(),
    is_decision_point: z.boolean().optional(),
    decision_type: z.union([DecisionTypeEnum, BlankEnum]).optional(),
    is_terminal: z.boolean().optional(),
    terminal_status: z.union([TerminalStatusEnum, BlankEnum]).optional(),
    max_visits: z.number().int().gte(0).lte(2147483647).nullish(),
    revisit_assignment: RevisitAssignmentEnum.optional(),
    revisit_role: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedStepsList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Steps),
  })
  .passthrough();
const StepsRequest = z
  .object({
    name: z.string().min(1).max(50),
    expected_duration: z.string().nullish(),
    description: z.string().nullish(),
    block_on_quarantine: z.boolean().optional(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    pass_threshold: z.number().optional(),
    requires_first_piece_inspection: z.boolean().optional(),
    part_type: z.string().uuid(),
    step_type: StepTypeEnum.optional(),
    is_decision_point: z.boolean().optional(),
    decision_type: z.union([DecisionTypeEnum, BlankEnum]).optional(),
    is_terminal: z.boolean().optional(),
    terminal_status: z.union([TerminalStatusEnum, BlankEnum]).optional(),
    max_visits: z.number().int().gte(0).lte(2147483647).nullish(),
    revisit_assignment: RevisitAssignmentEnum.optional(),
    revisit_role: z.number().int().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedStepsRequest = z
  .object({
    name: z.string().min(1).max(50),
    expected_duration: z.string().nullable(),
    description: z.string().nullable(),
    block_on_quarantine: z.boolean(),
    requires_qa_signoff: z.boolean(),
    sampling_required: z.boolean(),
    min_sampling_rate: z.number(),
    pass_threshold: z.number(),
    requires_first_piece_inspection: z.boolean(),
    part_type: z.string().uuid(),
    step_type: StepTypeEnum,
    is_decision_point: z.boolean(),
    decision_type: z.union([DecisionTypeEnum, BlankEnum]),
    is_terminal: z.boolean(),
    terminal_status: z.union([TerminalStatusEnum, BlankEnum]),
    max_visits: z.number().int().gte(0).lte(2147483647).nullable(),
    revisit_assignment: RevisitAssignmentEnum,
    revisit_role: z.number().int().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const SamplingRuleUpdateRequest = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().nullish(),
    order: z.number().int(),
  })
  .passthrough();
const StepSamplingRulesUpdateRequest = z
  .object({
    rules: z.array(SamplingRuleUpdateRequest),
    fallback_rules: z.array(SamplingRuleUpdateRequest).optional(),
    fallback_threshold: z.number().int().optional(),
    fallback_duration: z.number().int().optional(),
  })
  .passthrough();
const TenantGroup = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    description: z.string().optional(),
    is_custom: z.boolean(),
    permission_count: z.number().int(),
    member_count: z.number().int(),
    preset_key: z.string().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PaginatedTenantGroupList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(TenantGroup),
  })
  .passthrough();
const TenantGroupRequest = z
  .object({
    name: z.string().min(1).max(100),
    description: z.string().optional(),
  })
  .passthrough();
const TenantGroupDetail = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    description: z.string().optional(),
    is_custom: z.boolean(),
    permission_count: z.number().int(),
    member_count: z.number().int(),
    preset_key: z.string().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    permissions: z.array(z.string()),
  })
  .passthrough();
const PatchedTenantGroupRequest = z
  .object({ name: z.string().min(1).max(100), description: z.string() })
  .partial()
  .passthrough();
const RemoveMemberResponse = z.object({ status: z.string() }).passthrough();
const TierEnum = z.enum(["starter", "pro", "enterprise"]);
const TenantStatusEnum = z.enum([
  "active",
  "trial",
  "suspended",
  "pending_deletion",
]);
const Tenant = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    slug: z
      .string()
      .max(50)
      .regex(/^[-a-zA-Z0-9_]+$/),
    tier: TierEnum.optional(),
    status: TenantStatusEnum.optional(),
    is_active: z.boolean().optional(),
    is_demo: z.boolean().optional(),
    trial_ends_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    settings: z.unknown().optional(),
    user_count: z.number().int(),
    logo: z.string().url().nullish(),
    logo_url: z.string().nullable(),
    contact_email: z.string().max(254).email().optional(),
    contact_phone: z.string().max(30).optional(),
    website: z.string().max(200).url().optional(),
    address: z.string().optional(),
    default_timezone: z.string().max(50).optional(),
  })
  .passthrough();
const PaginatedTenantList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Tenant),
  })
  .passthrough();
const TenantCreateRequest = z
  .object({
    name: z.string().min(1).max(100),
    slug: z
      .string()
      .min(1)
      .max(50)
      .regex(/^[-a-zA-Z0-9_]+$/),
    tier: TierEnum.optional(),
    is_demo: z.boolean().optional(),
    admin_email: z.string().min(1).email(),
    admin_password: z.string().min(1).optional(),
    admin_first_name: z.string().min(1).optional().default("Admin"),
    admin_last_name: z.string().min(1).optional().default("User"),
  })
  .passthrough();
const TenantCreate = z
  .object({
    name: z.string().max(100),
    slug: z
      .string()
      .max(50)
      .regex(/^[-a-zA-Z0-9_]+$/),
    tier: TierEnum.optional(),
    is_demo: z.boolean().optional(),
  })
  .passthrough();
const TenantRequest = z
  .object({
    name: z.string().min(1).max(100),
    slug: z
      .string()
      .min(1)
      .max(50)
      .regex(/^[-a-zA-Z0-9_]+$/),
    tier: TierEnum.optional(),
    status: TenantStatusEnum.optional(),
    is_active: z.boolean().optional(),
    is_demo: z.boolean().optional(),
    trial_ends_at: z.string().datetime({ offset: true }).nullish(),
    settings: z.unknown().optional(),
    logo: z.instanceof(File).nullish(),
    contact_email: z.string().max(254).email().optional(),
    contact_phone: z.string().max(30).optional(),
    website: z.string().max(200).url().optional(),
    address: z.string().optional(),
    default_timezone: z.string().min(1).max(50).optional(),
  })
  .passthrough();
const PatchedTenantRequest = z
  .object({
    name: z.string().min(1).max(100),
    slug: z
      .string()
      .min(1)
      .max(50)
      .regex(/^[-a-zA-Z0-9_]+$/),
    tier: TierEnum,
    status: TenantStatusEnum,
    is_active: z.boolean(),
    is_demo: z.boolean(),
    trial_ends_at: z.string().datetime({ offset: true }).nullable(),
    settings: z.unknown(),
    logo: z.instanceof(File).nullable(),
    contact_email: z.string().max(254).email(),
    contact_phone: z.string().max(30),
    website: z.string().max(200).url(),
    address: z.string(),
    default_timezone: z.string().min(1).max(50),
  })
  .partial()
  .passthrough();
const ProcessingStatusEnum = z.enum([
  "pending",
  "processing",
  "completed",
  "failed",
]);
const ThreeDModel = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(255),
    file: z.string().url(),
    part_type: z.string().uuid(),
    part_type_display: z.string(),
    step: z.string().uuid().nullish(),
    step_display: z.string(),
    uploaded_at: z.string().datetime({ offset: true }),
    file_type: z.string(),
    annotation_count: z.number().int(),
    processing_status: ProcessingStatusEnum,
    processing_error: z.string(),
    processed_at: z.string().datetime({ offset: true }).nullable(),
    is_ready: z.boolean(),
    processing_metrics: z.object({}).partial().passthrough().nullable(),
    original_filename: z.string(),
    original_format: z.string(),
    original_size_bytes: z.number().int().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
  })
  .passthrough();
const PaginatedThreeDModelList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ThreeDModel),
  })
  .passthrough();
const ThreeDModelRequest = z
  .object({
    name: z.string().min(1).max(255),
    file: z.instanceof(File),
    part_type: z.string().uuid(),
    step: z.string().uuid().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedThreeDModelRequest = z
  .object({
    name: z.string().min(1).max(255),
    file: z.instanceof(File),
    part_type: z.string().uuid(),
    step: z.string().uuid().nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const TimeEntryTypeEnum = z.enum([
  "production",
  "setup",
  "rework",
  "downtime",
  "indirect",
]);
const TimeEntry = z
  .object({
    id: z.string().uuid(),
    entry_type: TimeEntryTypeEnum,
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullish(),
    user: z.number().int(),
    user_name: z.string(),
    duration_hours: z.number().nullable(),
    part: z.string().uuid().nullish(),
    part_erp_id: z.string().nullable(),
    work_order: z.string().uuid().nullish(),
    work_order_erp_id: z.string().nullable(),
    step: z.string().uuid().nullish(),
    equipment: z.string().uuid().nullish(),
    work_center: z.string().uuid().nullish(),
    notes: z.string().optional(),
    downtime_reason: z.string().max(100).optional(),
    approved: z.boolean().optional(),
    approved_by: z.number().int().nullable(),
    approved_at: z.string().datetime({ offset: true }).nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedTimeEntryList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(TimeEntry),
  })
  .passthrough();
const TimeEntryRequest = z
  .object({
    entry_type: TimeEntryTypeEnum,
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullish(),
    part: z.string().uuid().nullish(),
    work_order: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    equipment: z.string().uuid().nullish(),
    work_center: z.string().uuid().nullish(),
    notes: z.string().optional(),
    downtime_reason: z.string().max(100).optional(),
    approved: z.boolean().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedTimeEntryRequest = z
  .object({
    entry_type: TimeEntryTypeEnum,
    start_time: z.string().datetime({ offset: true }),
    end_time: z.string().datetime({ offset: true }).nullable(),
    part: z.string().uuid().nullable(),
    work_order: z.string().uuid().nullable(),
    step: z.string().uuid().nullable(),
    equipment: z.string().uuid().nullable(),
    work_center: z.string().uuid().nullable(),
    notes: z.string(),
    downtime_reason: z.string().max(100),
    approved: z.boolean(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const ClockOutInputRequest = z
  .object({ notes: z.string().min(1) })
  .partial()
  .passthrough();
const ClockInRequest = z
  .object({
    entry_type: TimeEntryTypeEnum,
    work_order: z.string().uuid().nullish(),
    part: z.string().uuid().nullish(),
    step: z.string().uuid().nullish(),
    equipment: z.string().uuid().nullish(),
    work_center: z.string().uuid().nullish(),
    notes: z.string().optional().default(""),
  })
  .passthrough();
const CustomerOrder = z
  .object({
    id: z.string().uuid(),
    order_number: z.string(),
    name: z.string(),
    latest_note: z.object({}).partial().passthrough().nullable(),
    notes_timeline: z.array(z.unknown()),
    order_status: z.string(),
    order_status_code: z.string(),
    estimated_completion: z.string().nullable(),
    original_completion_date: z.string().datetime({ offset: true }).nullable(),
    process_stages: z.array(z.unknown()),
    gate_info: z.object({}).partial().passthrough().nullable(),
    parts_summary: z.object({}).partial().passthrough().nullable(),
    company_name: z.string().nullable(),
    customer_first_name: z.string().nullable(),
    customer_last_name: z.string().nullable(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PaginatedCustomerOrderList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(CustomerOrder),
  })
  .passthrough();
const InviteViewerInputRequest = z
  .object({ email: z.string().min(1).email() })
  .passthrough();
const InviteViewerResponse = z
  .object({
    status: z.string(),
    email: z.string().email(),
    invitation_id: z.number().int().nullable(),
    user_created: z.boolean(),
  })
  .passthrough();
const InviteError = z.object({ detail: z.string() }).passthrough();
const TrainingRecord = z
  .object({
    id: z.string().uuid(),
    user: z.number().int(),
    user_info: z.object({}).partial().passthrough().nullable(),
    training_type: z.string().uuid(),
    training_type_info: z.object({}).partial().passthrough().nullable(),
    completed_date: z.string(),
    expires_date: z.string().nullish(),
    trainer: z.number().int().nullish(),
    trainer_info: z.object({}).partial().passthrough().nullable(),
    notes: z.string().optional(),
    status: z.string(),
    is_current: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedTrainingRecordList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(TrainingRecord),
  })
  .passthrough();
const TrainingRecordRequest = z
  .object({
    user: z.number().int(),
    training_type: z.string().uuid(),
    completed_date: z.string(),
    expires_date: z.string().nullish(),
    trainer: z.number().int().nullish(),
    notes: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedTrainingRecordRequest = z
  .object({
    user: z.number().int(),
    training_type: z.string().uuid(),
    completed_date: z.string(),
    expires_date: z.string().nullable(),
    trainer: z.number().int().nullable(),
    notes: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const TrainingStats = z
  .object({
    total_records: z.number().int(),
    current: z.number().int(),
    expiring_soon: z.number().int(),
    expired: z.number().int(),
  })
  .passthrough();
const TrainingRequirement = z
  .object({
    id: z.string().uuid(),
    training_type: z.string().uuid(),
    training_type_info: z.object({}).partial().passthrough().nullable(),
    step: z.string().uuid().nullish(),
    step_info: z.object({}).partial().passthrough().nullable(),
    process: z.string().uuid().nullish(),
    process_info: z.object({}).partial().passthrough().nullable(),
    equipment_type: z.string().uuid().nullish(),
    equipment_type_info: z.object({}).partial().passthrough().nullable(),
    notes: z.string().optional(),
    scope: z.string(),
    scope_display: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedTrainingRequirementList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(TrainingRequirement),
  })
  .passthrough();
const TrainingRequirementRequest = z
  .object({
    training_type: z.string().uuid(),
    step: z.string().uuid().nullish(),
    process: z.string().uuid().nullish(),
    equipment_type: z.string().uuid().nullish(),
    notes: z.string().optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedTrainingRequirementRequest = z
  .object({
    training_type: z.string().uuid(),
    step: z.string().uuid().nullable(),
    process: z.string().uuid().nullable(),
    equipment_type: z.string().uuid().nullable(),
    notes: z.string(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const TrainingType = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    description: z.string().optional(),
    validity_period_days: z.number().int().gte(0).lte(2147483647).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedTrainingTypeList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(TrainingType),
  })
  .passthrough();
const TrainingTypeRequest = z
  .object({
    name: z.string().min(1).max(100),
    description: z.string().optional(),
    validity_period_days: z.number().int().gte(0).lte(2147483647).nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedTrainingTypeRequest = z
  .object({
    name: z.string().min(1).max(100),
    description: z.string(),
    validity_period_days: z.number().int().gte(0).lte(2147483647).nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const User = z
  .object({
    id: z.number().int(),
    username: z
      .string()
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
    email: z.string().max(254).email().optional(),
    full_name: z.string(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    date_joined: z.string().datetime({ offset: true }),
    parent_company: Company.nullable(),
    groups: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const PaginatedUserList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(User),
  })
  .passthrough();
const UserRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
    email: z.string().max(254).email().optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    parent_company_id: z.string().uuid().nullish(),
    group_ids: z.array(z.number().int()).optional(),
  })
  .passthrough();
const PatchedUserRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullable(),
    last_name: z.string().max(150).nullable(),
    email: z.string().max(254).email(),
    is_staff: z.boolean(),
    is_active: z.boolean(),
    parent_company_id: z.string().uuid().nullable(),
    group_ids: z.array(z.number().int()),
  })
  .partial()
  .passthrough();
const BulkUserActivationInputRequest = z
  .object({ user_ids: z.array(z.number().int()), is_active: z.boolean() })
  .passthrough();
const BulkCompanyAssignmentInputRequest = z
  .object({
    user_ids: z.array(z.number().int()),
    company_id: z.string().uuid().nullable(),
  })
  .passthrough();
const SendInvitationInputRequest = z
  .object({ user_id: z.number().int() })
  .passthrough();
const UserInvitation = z
  .object({
    id: z.number().int(),
    user: z.number().int(),
    user_email: z.string().email(),
    user_name: z.string(),
    invited_by: z.number().int().nullish(),
    invited_by_name: z.string(),
    sent_at: z.string().datetime({ offset: true }),
    expires_at: z.string().datetime({ offset: true }),
    accepted_at: z.string().datetime({ offset: true }).nullable(),
    is_expired: z.boolean(),
    is_valid: z.boolean(),
    accepted_ip_address: z.string().nullable(),
    accepted_user_agent: z.string().nullable(),
    invitation_url: z.string(),
  })
  .passthrough();
const PaginatedUserInvitationList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(UserInvitation),
  })
  .passthrough();
const UserInvitationRequest = z
  .object({
    user: z.number().int(),
    invited_by: z.number().int().nullish(),
    expires_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PatchedUserInvitationRequest = z
  .object({
    user: z.number().int(),
    invited_by: z.number().int().nullable(),
    expires_at: z.string().datetime({ offset: true }),
  })
  .partial()
  .passthrough();
const AcceptInvitationInputRequest = z
  .object({
    token: z.string().min(1),
    password: z.string().min(1),
    opt_in_notifications: z.boolean().optional().default(false),
  })
  .passthrough();
const AcceptInvitationResponse = z
  .object({ detail: z.string(), user_id: z.number().int() })
  .passthrough();
const ResendInvitationInputRequest = z
  .object({ invitation_id: z.number().int() })
  .passthrough();
const ValidateTokenInputRequest = z
  .object({ token: z.string().min(1) })
  .passthrough();
const ValidateTokenResponse = z
  .object({
    valid: z.boolean(),
    user_email: z.string().email(),
    expires_at: z.string().datetime({ offset: true }),
    expired: z.boolean(),
  })
  .passthrough();
const WorkCenter = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(100),
    code: z.string().max(20),
    description: z.string().optional(),
    capacity_units: z.string().max(20).optional(),
    default_efficiency: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,2})?$/)
      .optional(),
    equipment: z.array(z.string().uuid()).optional(),
    equipment_names: z.array(z.string()),
    cost_center: z.string().max(50).optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedWorkCenterList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(WorkCenter),
  })
  .passthrough();
const WorkCenterRequest = z
  .object({
    name: z.string().min(1).max(100),
    code: z.string().min(1).max(20),
    description: z.string().optional(),
    capacity_units: z.string().min(1).max(20).optional(),
    default_efficiency: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,2})?$/)
      .optional(),
    equipment: z.array(z.string().uuid()).optional(),
    cost_center: z.string().max(50).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const WorkCenterSelect = z
  .object({
    id: z.string().uuid(),
    code: z.string().max(20),
    name: z.string().max(100),
  })
  .passthrough();
const PatchedWorkCenterRequest = z
  .object({
    name: z.string().min(1).max(100),
    code: z.string().min(1).max(20),
    description: z.string(),
    capacity_units: z.string().min(1).max(20),
    default_efficiency: z.string().regex(/^-?\d{0,3}(?:\.\d{0,2})?$/),
    equipment: z.array(z.string().uuid()),
    cost_center: z.string().max(50),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const WorkOrderStatusEnum = z.enum([
  "PENDING",
  "IN_PROGRESS",
  "COMPLETED",
  "ON_HOLD",
  "CANCELLED",
  "WAITING_FOR_OPERATOR",
]);
const PriorityEnum = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
  z.literal(4),
]);
const WorkOrderList = z
  .object({
    id: z.string().uuid(),
    ERP_id: z.string().max(50),
    workorder_status: WorkOrderStatusEnum.optional(),
    priority: PriorityEnum.optional(),
    quantity: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    related_order: z.string().uuid().nullish(),
    related_order_info: z.object({}).partial().passthrough().nullable(),
    process: z.string().uuid().nullish(),
    process_info: z.object({}).partial().passthrough().nullable(),
    expected_completion: z.string().nullish(),
    true_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
    parts_count: z.number().int(),
    qa_progress: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PaginatedWorkOrderListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(WorkOrderList),
  })
  .passthrough();
const WorkOrderRequest = z
  .object({
    ERP_id: z.string().min(1).max(50),
    workorder_status: WorkOrderStatusEnum.optional(),
    priority: PriorityEnum.optional(),
    quantity: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    related_order: z.string().uuid().nullish(),
    process: z.string().uuid().nullish(),
    expected_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_completion: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const WorkOrder = z
  .object({
    id: z.string().uuid(),
    ERP_id: z.string().max(50),
    workorder_status: WorkOrderStatusEnum.optional(),
    priority: PriorityEnum.optional(),
    quantity: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    related_order: z.string().uuid().nullish(),
    related_order_info: z.object({}).partial().passthrough().nullable(),
    related_order_detail: z.object({}).partial().passthrough().nullable(),
    process: z.string().uuid().nullish(),
    process_info: z.object({}).partial().passthrough().nullable(),
    expected_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_completion: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
    parts_summary: z.object({}).partial().passthrough().nullable(),
    is_batch_work_order: z.boolean(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean().optional(),
  })
  .passthrough();
const PatchedWorkOrderRequest = z
  .object({
    ERP_id: z.string().min(1).max(50),
    workorder_status: WorkOrderStatusEnum,
    priority: PriorityEnum,
    quantity: z.number().int().gte(-2147483648).lte(2147483647),
    related_order: z.string().uuid().nullable(),
    process: z.string().uuid().nullable(),
    expected_completion: z.string().nullable(),
    expected_duration: z.string().nullable(),
    true_completion: z.string().nullable(),
    true_duration: z.string().nullable(),
    notes: z.string().max(500).nullable(),
    archived: z.boolean(),
  })
  .partial()
  .passthrough();
const QADocumentsResponse = z
  .object({
    work_order_documents: z.array(z.object({}).partial().passthrough()),
    current_step_documents: z.array(z.object({}).partial().passthrough()),
    part_type_documents: z.array(z.object({}).partial().passthrough()),
    current_step_id: z.string().uuid().nullable(),
    parts_in_qa: z.number().int(),
  })
  .passthrough();
const StepSummary = z
  .object({
    step_id: z.string().uuid(),
    step_name: z.string(),
    step_order: z.number().int(),
    status: TravelerStepStatusEnum,
    started_at: z.string().datetime({ offset: true }).nullable(),
    completed_at: z.string().datetime({ offset: true }).nullable(),
    duration_seconds: z.number().int().nullable(),
    operator_name: z.string().nullable(),
    quality_status: z.union([QualityStatusEnum, NullEnum]).nullable(),
    parts_at_step: z.number().int(),
    parts_completed: z.number().int(),
    measurement_count: z.number().int(),
    defect_count: z.number().int(),
    attachment_count: z.number().int(),
  })
  .passthrough();
const WorkOrderStepHistoryResponse = z
  .object({
    work_order_id: z.string().uuid(),
    process_name: z.string().nullable(),
    total_parts: z.number().int(),
    step_history: z.array(StepSummary),
  })
  .passthrough();
const EmbedQueryRequestRequest = z
  .object({ query: z.string().min(1) })
  .passthrough();
const EmbedQueryResponse = z
  .object({ embedding: z.array(z.number()) })
  .passthrough();
const ExecuteQueryResponse = z
  .object({
    model: z.string(),
    filters: z.object({}).partial().passthrough(),
    count: z.number().int(),
    limit: z.number().int(),
    results: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const ExecuteQueryRequestRequest = z
  .object({
    model: z.string().min(1),
    filters: z.object({}).partial().passthrough().optional(),
    fields: z.array(z.string().min(1)).optional(),
    limit: z.number().int().optional(),
    aggregate: z.string().min(1).optional(),
  })
  .passthrough();
const QueryRequest = z
  .object({
    model: z.string(),
    filters: z.object({}).partial().passthrough().optional(),
    fields: z.array(z.string()).optional(),
    limit: z.number().int().optional(),
    aggregate: z.string().optional(),
  })
  .passthrough();
const ContextWindowRequestRequest = z
  .object({
    chunk_id: z.string().uuid(),
    window_size: z.number().int().optional(),
  })
  .passthrough();
const ContextWindowResponse = z
  .object({
    center_chunk_id: z.string().uuid(),
    center_index: z.number().int(),
    window_size: z.number().int(),
    doc_name: z.string(),
    chunks: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const HybridSearchRequestRequest = z
  .object({
    query: z.string().min(1),
    embedding: z.array(z.number()),
    limit: z.number().int(),
    vector_threshold: z.number(),
    doc_ids: z.array(z.string().uuid()),
  })
  .partial()
  .passthrough();
const HybridSearchResponse = z
  .object({
    query: z.string(),
    has_embedding: z.boolean(),
    total_results: z.number().int(),
    results: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const KeywordSearchResponse = z
  .object({
    query: z.string(),
    total_results: z.number().int(),
    results: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const VectorSearchRequestRequest = z
  .object({
    embedding: z.array(z.number()),
    limit: z.number().int().optional().default(10),
    threshold: z.number().optional().default(0.7),
    doc_ids: z.array(z.string().uuid()).optional(),
  })
  .passthrough();
const VectorSearchResponse = z
  .object({ results: z.array(z.unknown()) })
  .passthrough();
const ActionEnum = z.union([
  z.literal(0),
  z.literal(1),
  z.literal(2),
  z.literal(3),
]);
const AuditLog = z
  .object({
    id: z.number().int(),
    object_pk: z.string().max(255),
    object_repr: z.string(),
    content_type: z.number().int(),
    content_type_name: z.string(),
    actor: z.number().int().nullish(),
    actor_info: z.object({}).partial().passthrough().nullable(),
    remote_addr: z.string().nullish(),
    timestamp: z.string().datetime({ offset: true }),
    action: ActionEnum,
    changes: z.unknown().nullish(),
  })
  .passthrough();
const PaginatedAuditLogList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(AuditLog),
  })
  .passthrough();
const ContentType = z
  .object({
    id: z.number().int(),
    app_label: z.string().max(100),
    model: z.string().max(100),
  })
  .passthrough();
const CAPAStatusResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total: z.number().int(),
  })
  .passthrough();
const DefectParetoResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total: z.number().int(),
  })
  .passthrough();
const DefectRecordsResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total: z.number().int(),
    filters_applied: z.object({}).partial().passthrough(),
  })
  .passthrough();
const DefectTrendResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    summary: z.object({}).partial().passthrough(),
  })
  .passthrough();
const DefectsByProcessResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total: z.number().int(),
  })
  .passthrough();
const DispositionBreakdownResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total: z.number().int(),
  })
  .passthrough();
const FailedInspectionsResponse = z
  .object({ data: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const FilterOptionsResponse = z
  .object({
    defect_types: z.array(z.object({}).partial().passthrough()),
    processes: z.array(z.object({}).partial().passthrough()),
    part_types: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const FPYTrendResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    average: z.number(),
    total_inspections: z.number().int(),
    total_passed: z.number().int(),
  })
  .passthrough();
const InProcessActionsResponse = z
  .object({ data: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const DashboardKPIsResponse = z
  .object({
    active_capas: z.number().int(),
    open_ncrs: z.number().int(),
    overdue_capas: z.number().int(),
    parts_in_quarantine: z.number().int(),
    current_fpy: z.number().nullable(),
  })
  .passthrough();
const NcrAgingResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    avg_age_days: z.number(),
    overdue_count: z.number().int(),
  })
  .passthrough();
const NcrTrendResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    summary: z.object({}).partial().passthrough(),
  })
  .passthrough();
const NeedsAttentionResponse = z
  .object({ data: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const OpenDispositionsResponse = z
  .object({ data: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const QualityRatesResponse = z
  .object({
    scrap_rate: z.number(),
    rework_rate: z.number(),
    use_as_is_rate: z.number(),
    total_inspected: z.number().int(),
    total_failed: z.number().int(),
  })
  .passthrough();
const RepeatDefectsResponse = z
  .object({
    data: z.array(z.object({}).partial().passthrough()),
    total_repeat_count: z.number().int(),
  })
  .passthrough();
const PermissionListResponse = z
  .object({ permissions: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const PresetListResponse = z
  .object({ presets: z.array(z.object({}).partial().passthrough()) })
  .passthrough();
const ReportTypeEnum = z.enum(["spc", "capa", "quality_report"]);
const GenerateReportRequest = z
  .object({
    report_type: ReportTypeEnum,
    params: z.object({}).partial().passthrough(),
  })
  .passthrough();
const GenerateReportResponse = z
  .object({ message: z.string(), task_id: z.string() })
  .passthrough();
const GeneratedReportStatusEnum = z.enum(["PENDING", "COMPLETED", "FAILED"]);
const GeneratedReport = z
  .object({
    id: z.string().uuid(),
    report_type: z.string(),
    generated_by: z.number().int().nullable(),
    generated_by_name: z.string().nullable(),
    generated_at: z.string().datetime({ offset: true }),
    parameters: z.unknown(),
    document: z.string().uuid().nullable(),
    document_url: z.string().url().nullable(),
    emailed_to: z.string().email().nullable(),
    emailed_at: z.string().datetime({ offset: true }).nullable(),
    status: GeneratedReportStatusEnum,
    error_message: z.string().nullable(),
  })
  .passthrough();
const PaginatedGeneratedReportList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(GeneratedReport),
  })
  .passthrough();
const ReportTypesResponse = z
  .object({
    spc: z.object({}).partial().passthrough(),
    capa: z.object({}).partial().passthrough(),
  })
  .passthrough();
const ChartTypeEnum = z.enum(["XBAR_R", "XBAR_S", "I_MR"]);
const BaselineStatusEnum = z.enum(["ACTIVE", "SUPERSEDED"]);
const SPCBaselineList = z
  .object({
    id: z.string().uuid(),
    measurement_definition: z.string().uuid(),
    measurement_label: z.string(),
    chart_type: ChartTypeEnum,
    chart_type_display: z.string(),
    subgroup_size: z.number().int().gte(0).lte(2147483647).optional(),
    status: BaselineStatusEnum.optional(),
    status_display: z.string(),
    frozen_by: z.number().int().nullish(),
    frozen_by_name: z.string().nullable(),
    frozen_at: z.string().datetime({ offset: true }),
    sample_count: z.number().int().gte(0).lte(2147483647).optional(),
  })
  .passthrough();
const PaginatedSPCBaselineListList = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(SPCBaselineList),
  })
  .passthrough();
const SPCBaselineRequest = z
  .object({
    measurement_definition: z.string().uuid(),
    chart_type: ChartTypeEnum,
    subgroup_size: z.number().int().gte(0).lte(2147483647).optional(),
    xbar_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    status: BaselineStatusEnum.optional(),
    frozen_by: z.number().int().nullish(),
    superseded_by: z.string().uuid().nullish(),
    superseded_reason: z.string().optional(),
    sample_count: z.number().int().gte(0).lte(2147483647).optional(),
    notes: z.string().optional(),
  })
  .passthrough();
const SPCBaseline = z
  .object({
    id: z.string().uuid(),
    measurement_definition: z.string().uuid(),
    measurement_label: z.string(),
    process_name: z.string().nullable(),
    step_name: z.string(),
    chart_type: ChartTypeEnum,
    chart_type_display: z.string(),
    subgroup_size: z.number().int().gte(0).lte(2147483647).optional(),
    xbar_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    status: BaselineStatusEnum.optional(),
    status_display: z.string(),
    frozen_by: z.number().int().nullish(),
    frozen_by_name: z.string().nullable(),
    frozen_at: z.string().datetime({ offset: true }),
    superseded_by: z.string().uuid().nullish(),
    superseded_at: z.string().datetime({ offset: true }).nullable(),
    superseded_reason: z.string().optional(),
    sample_count: z.number().int().gte(0).lte(2147483647).optional(),
    notes: z.string().optional(),
    control_limits: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PatchedSPCBaselineRequest = z
  .object({
    measurement_definition: z.string().uuid(),
    chart_type: ChartTypeEnum,
    subgroup_size: z.number().int().gte(0).lte(2147483647),
    xbar_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    xbar_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    xbar_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    range_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    range_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    range_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    individual_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    individual_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    individual_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    mr_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    mr_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullable(),
    status: BaselineStatusEnum,
    frozen_by: z.number().int().nullable(),
    superseded_by: z.string().uuid().nullable(),
    superseded_reason: z.string(),
    sample_count: z.number().int().gte(0).lte(2147483647),
    notes: z.string(),
  })
  .partial()
  .passthrough();
const SupersedeRequestRequest = z
  .object({ reason: z.string() })
  .partial()
  .passthrough();
const SPCBaselineFreezeRequest = z
  .object({
    measurement_definition_id: z.string().uuid(),
    chart_type: ChartTypeEnum,
    subgroup_size: z.number().int().gte(1).lte(25),
    xbar_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    xbar_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    range_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    individual_lcl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_ucl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    mr_cl: z
      .string()
      .regex(/^-?\d{0,10}(?:\.\d{0,6})?$/)
      .nullish(),
    sample_count: z.number().int().optional().default(0),
    notes: z.string().optional().default(""),
  })
  .passthrough();
const MeasurementDefinitionSPC = z
  .object({
    id: z.string().uuid(),
    label: z.string().max(100),
    type: TypeEnum,
    unit: z.string().max(50).optional(),
    nominal: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    upper_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
    lower_tol: z
      .string()
      .regex(/^-?\d{0,3}(?:\.\d{0,6})?$/)
      .nullish(),
  })
  .passthrough();
const SPCCapabilityResponse = z
  .object({
    definition: MeasurementDefinitionSPC,
    sample_size: z.number().int(),
    subgroup_size: z.number().int(),
    num_subgroups: z.number().int(),
    usl: z.number(),
    lsl: z.number(),
    mean: z.number(),
    std_dev_within: z.number(),
    std_dev_overall: z.number(),
    cp: z.number().nullable(),
    cpk: z.number().nullable(),
    pp: z.number().nullable(),
    ppk: z.number().nullable(),
    interpretation: z.string(),
  })
  .passthrough();
const MeasurementDataPoint = z
  .object({
    id: z.string().uuid(),
    value: z.number(),
    timestamp: z.string().datetime({ offset: true }),
    report_id: z.string().uuid(),
    part_erp_id: z.string(),
    operator_name: z.string().nullable(),
    is_within_spec: z.boolean(),
  })
  .passthrough();
const SPCDataResponse = z
  .object({
    definition: MeasurementDefinitionSPC,
    process_name: z.string(),
    step_name: z.string(),
    data_points: z.array(MeasurementDataPoint),
    statistics: z.object({}).partial().passthrough(),
  })
  .passthrough();
const DimensionalResultsResponse = z
  .object({
    part: z.object({}).partial().passthrough().nullable(),
    work_order: z.object({}).partial().passthrough().nullable(),
    results: z.array(z.object({}).partial().passthrough()),
    summary: z.object({}).partial().passthrough(),
  })
  .passthrough();
const ProcessStepSPC = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    order: z.number().int(),
    measurements: z.array(MeasurementDefinitionSPC),
  })
  .passthrough();
const ProcessSPC = z
  .object({
    id: z.string().uuid(),
    name: z.string().max(50),
    part_type_name: z.string(),
    steps: z.array(ProcessStepSPC),
  })
  .passthrough();
const TenantInfo = z
  .object({
    id: z.string().uuid(),
    name: z.string(),
    slug: z.string().regex(/^[-a-zA-Z0-9_]+$/),
    tier: z.string(),
    status: z.string(),
    is_demo: z.boolean(),
    trial_ends_at: z.string().datetime({ offset: true }).nullable(),
    logo_url: z.string().nullable(),
    primary_color: z.string().nullable(),
    secondary_color: z.string().nullable(),
    contact_email: z.string().email().nullable(),
    contact_phone: z.string().nullable(),
    website: z.string().url().nullable(),
    address: z.string().nullable(),
    default_timezone: z.string(),
  })
  .passthrough();
const ModeEnum = z.enum(["saas", "dedicated"]);
const DeploymentInfo = z
  .object({ mode: ModeEnum, is_saas: z.boolean(), is_dedicated: z.boolean() })
  .passthrough();
const CurrentTenantResponse = z
  .object({
    tenant: TenantInfo.nullable(),
    deployment: DeploymentInfo,
    features: z.object({}).partial().passthrough(),
    limits: z.object({}).partial().passthrough().nullable(),
    user: z.object({}).partial().passthrough().nullable(),
  })
  .passthrough();
const TenantLogoResponse = z
  .object({ logo_url: z.string().nullable() })
  .passthrough();
const TenantLogoDeleteResponse = z
  .object({ logo_url: z.string().nullable() })
  .passthrough();
const TenantSettingsResponse = z
  .object({
    name: z.string(),
    tier: z.string(),
    status: z.string(),
    settings: z.object({}).partial().passthrough(),
    contact_email: z.string().email().nullable(),
    contact_phone: z.string().nullable(),
    website: z.string().url().nullable(),
    address: z.string().nullable(),
    default_timezone: z.string(),
    logo_url: z.string().nullable(),
  })
  .passthrough();
const PatchedTenantSettingsUpdateRequestRequest = z
  .object({
    name: z.string().min(1),
    settings: z.object({}).partial().passthrough(),
    contact_email: z.string().email().nullable(),
    contact_phone: z.string().nullable(),
    website: z.string().url().nullable(),
    address: z.string().nullable(),
    default_timezone: z.string().min(1),
  })
  .partial()
  .passthrough();
const TenantSettingsUpdateResponse = z
  .object({
    name: z.string(),
    tier: z.string(),
    status: z.string(),
    settings: z.object({}).partial().passthrough(),
    contact_email: z.string().email().nullable(),
    contact_phone: z.string().nullable(),
    website: z.string().url().nullable(),
    address: z.string().nullable(),
    default_timezone: z.string(),
    logo_url: z.string().nullable(),
  })
  .passthrough();
const SignupRequest = z
  .object({
    company_name: z.string().min(1).max(100),
    slug: z
      .string()
      .min(1)
      .regex(/^[-a-zA-Z0-9_]+$/)
      .optional(),
    email: z.string().min(1).email(),
    password: z.string().min(8),
    first_name: z.string().min(1).max(30),
    last_name: z.string().min(1).max(30),
  })
  .passthrough();
const SignupResponse = z
  .object({
    message: z.string(),
    tenant: z.object({}).partial().passthrough(),
    user: z.object({}).partial().passthrough(),
  })
  .passthrough();
const EffectivePermissionsResponse = z
  .object({
    user_id: z.string(),
    user_email: z.string(),
    groups: z.array(z.object({}).partial().passthrough()),
    effective_permissions: z.array(z.string()),
    total_count: z.number().int(),
  })
  .passthrough();
const LoginRequest = z
  .object({
    username: z.string().optional(),
    email: z.string().email().optional(),
    password: z.string().min(1),
  })
  .passthrough();
const Token = z.object({ key: z.string().max(40) }).passthrough();
const RestAuthDetail = z.object({ detail: z.string() }).passthrough();
const PasswordChangeRequest = z
  .object({
    new_password1: z.string().min(1).max(128),
    new_password2: z.string().min(1).max(128),
  })
  .passthrough();
const PasswordResetRequest = z
  .object({ email: z.string().min(1).email() })
  .passthrough();
const PasswordResetConfirmRequest = z
  .object({
    new_password1: z.string().min(1).max(128),
    new_password2: z.string().min(1).max(128),
    uid: z.string().min(1),
    token: z.string().min(1),
  })
  .passthrough();
const RegisterRequest = z
  .object({
    username: z.string().min(1).max(150),
    email: z.string().min(1).email(),
    password1: z.string().min(1),
    password2: z.string().min(1),
  })
  .passthrough();
const ResendEmailVerificationRequest = z
  .object({ email: z.string().min(1).email() })
  .passthrough();
const VerifyEmailRequest = z.object({ key: z.string().min(1) }).passthrough();
const UserDetails = z
  .object({
    pk: z.number().int(),
    username: z
      .string()
      .max(150)
      .regex(/^[\w.@+-]+$/),
    email: z.string().email(),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
  })
  .passthrough();
const UserDetailsRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullish(),
    last_name: z.string().max(150).nullish(),
  })
  .passthrough();
const PatchedUserDetailsRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).nullable(),
    last_name: z.string().max(150).nullable(),
  })
  .partial()
  .passthrough();
const CapaTaskAssigneeRequest = z
  .object({
    task: z.string().uuid(),
    user: z.number().int(),
    status: CapaTaskStatusEnum.optional(),
    completion_notes: z.string().nullish(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const FishboneNested = z
  .object({
    problem_statement: z.string().nullable(),
    man_causes: z.string().nullable(),
    machine_causes: z.string().nullable(),
    material_causes: z.string().nullable(),
    method_causes: z.string().nullable(),
    measurement_causes: z.string().nullable(),
    environment_causes: z.string().nullable(),
    identified_root_cause: z.string().nullable(),
  })
  .partial()
  .passthrough();
const FiveWhysNested = z
  .object({
    why_1_question: z.string().nullable(),
    why_1_answer: z.string().nullable(),
    why_2_question: z.string().nullable(),
    why_2_answer: z.string().nullable(),
    why_3_question: z.string().nullable(),
    why_3_answer: z.string().nullable(),
    why_4_question: z.string().nullable(),
    why_4_answer: z.string().nullable(),
    why_5_question: z.string().nullable(),
    why_5_answer: z.string().nullable(),
    identified_root_cause: z.string().nullable(),
  })
  .partial()
  .passthrough();
const MeasurementResult = z
  .object({
    report: z.string(),
    definition: z.string().uuid(),
    value_numeric: z.number().nullish(),
    value_pass_fail: z
      .union([ValuePassFailEnum, BlankEnum, NullEnum])
      .nullish(),
    is_within_spec: z.boolean(),
    created_by: z.number().int(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const ProcessStepRequest = z
  .object({
    step_id: z.string().uuid(),
    order: z.number().int().gte(-2147483648).lte(2147483647),
    is_entry_point: z.boolean().optional(),
  })
  .passthrough();
const RootCauseRequest = z
  .object({
    rca_record: z.string().uuid(),
    description: z.string().min(1),
    category: RootCauseCategoryEnum,
    role: RoleEnum.optional(),
    sequence: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    archived: z.boolean().optional(),
  })
  .passthrough();
const StepEdgeRequest = z
  .object({
    from_step: z.string().uuid(),
    to_step: z.string().uuid(),
    edge_type: EdgeTypeEnum.optional(),
    condition_measurement: z.string().uuid().nullish(),
    condition_operator: z.union([ConditionOperatorEnum, BlankEnum]).optional(),
    condition_value: z
      .string()
      .regex(/^-?\d{0,6}(?:\.\d{0,4})?$/)
      .nullish(),
  })
  .passthrough();
const StepRequest = z
  .object({
    name: z.string().min(1).max(50),
    description: z.string().nullish(),
    part_type: z.string().uuid(),
    expected_duration: z.string().nullish(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    block_on_quarantine: z.boolean().optional(),
    pass_threshold: z.number().optional(),
    step_type: StepTypeEnum.optional(),
    is_decision_point: z.boolean().optional(),
    decision_type: z.union([DecisionTypeEnum, BlankEnum]).optional(),
    is_terminal: z.boolean().optional(),
    terminal_status: z.union([TerminalStatusEnum, BlankEnum]).optional(),
    max_visits: z.number().int().gte(0).lte(2147483647).nullish(),
    revisit_assignment: RevisitAssignmentEnum.optional(),
  })
  .passthrough();

export const schemas = {
  ApprovalStatusEnum,
  ApprovalTypeEnum,
  ApprovalFlowTypeEnum,
  ApprovalSequenceEnum,
  DelegationPolicyEnum,
  DecisionEnum,
  VerificationMethodEnum,
  ApprovalResponse,
  ApprovalRequest,
  PaginatedApprovalRequestList,
  ApprovalRequestRequest,
  PatchedApprovalRequestRequest,
  ListMetadataResponse,
  PaginatedApprovalResponseList,
  ApprovalResponseRequest,
  PatchedApprovalResponseRequest,
  ApprovalTemplate,
  PaginatedApprovalTemplateList,
  ApprovalTemplateRequest,
  PatchedApprovalTemplateRequest,
  AssemblyUsage,
  PaginatedAssemblyUsageList,
  AssemblyUsageRequest,
  PatchedAssemblyUsageRequest,
  AssemblyRemoveRequest,
  BOMLine,
  PaginatedBOMLineList,
  BOMLineRequest,
  PatchedBOMLineRequest,
  BOMTypeEnum,
  BOMStatusEnum,
  BOMList,
  PaginatedBOMListList,
  BOMRequest,
  BOM,
  PatchedBOMRequest,
  CapaTypeEnum,
  SeverityEnum,
  TaskTypeEnum,
  CapaTaskStatusEnum,
  CapaTaskAssignee,
  CompletionModeEnum,
  CapaTasks,
  RcaMethodEnum,
  RcaReviewStatusEnum,
  RootCauseVerificationStatusEnum,
  RootCauseCategoryEnum,
  RoleEnum,
  RootCause,
  FiveWhys,
  Fishbone,
  RcaRecord,
  EffectivenessResultEnum,
  CapaVerification,
  CAPA,
  PaginatedCAPAList,
  CAPARequest,
  PatchedCAPARequest,
  ResultEnum,
  CalibrationTypeEnum,
  CalibrationRecord,
  PaginatedCalibrationRecordList,
  CalibrationRecordRequest,
  PatchedCalibrationRecordRequest,
  CalibrationStats,
  PaginatedCapaTasksList,
  CapaTasksRequest,
  PatchedCapaTasksRequest,
  PaginatedCapaVerificationList,
  CapaVerificationRequest,
  PatchedCapaVerificationRequest,
  ChatSession,
  PaginatedChatSessionList,
  ChatSessionRequest,
  PatchedChatSessionRequest,
  Company,
  PaginatedCompanyList,
  CompanyRequest,
  PatchedCompanyRequest,
  CoreStatusEnum,
  ConditionGradeEnum,
  CoreList,
  PaginatedCoreListList,
  SourceTypeEnum,
  CoreRequest,
  Core,
  PatchedCoreRequest,
  HarvestedComponent,
  PaginatedHarvestedComponentList,
  CoreScrapRequest,
  UserDetail,
  UserDetailRequest,
  PatchedUserDetailRequest,
  DisassemblyBOMLine,
  PaginatedDisassemblyBOMLineList,
  DisassemblyBOMLineRequest,
  PatchedDisassemblyBOMLineRequest,
  DocumentType,
  PaginatedDocumentTypeList,
  DocumentTypeRequest,
  PatchedDocumentTypeRequest,
  ClassificationEnum,
  NullEnum,
  DocumentsStatusEnum,
  Documents,
  PaginatedDocumentsList,
  DocumentsRequest,
  PatchedDocumentsRequest,
  DowntimeCategoryEnum,
  DowntimeEvent,
  PaginatedDowntimeEventList,
  DowntimeEventRequest,
  PatchedDowntimeEventRequest,
  UserSelect,
  PaginatedUserSelectList,
  EquipmentsStatusEnum,
  Equipments,
  PaginatedEquipmentsList,
  EquipmentsRequest,
  EquipmentType,
  PaginatedEquipmentTypeList,
  EquipmentTypeRequest,
  PatchedEquipmentTypeRequest,
  PatchedEquipmentsRequest,
  QualityErrorsList,
  PaginatedQualityErrorsListList,
  QualityErrorsListRequest,
  PatchedQualityErrorsListRequest,
  QualityReportStatusEnum,
  QualityReports,
  PaginatedQualityReportsList,
  ValuePassFailEnum,
  BlankEnum,
  MeasurementResultRequest,
  QualityReportsRequest,
  PatchedQualityReportsRequest,
  PaginatedFishboneList,
  FishboneRequest,
  PatchedFishboneRequest,
  PaginatedFiveWhysList,
  FiveWhysRequest,
  PatchedFiveWhysRequest,
  Group,
  PaginatedGroupList,
  GroupRequest,
  PatchedGroupRequest,
  GroupAddPermissionsInputRequest,
  GroupAddPermissionsResponse,
  GroupAddUsersInputRequest,
  GroupAddUsersResponse,
  GroupRemovePermissionsInputRequest,
  GroupRemovePermissionsResponse,
  GroupRemoveUsersInputRequest,
  GroupRemoveUsersResponse,
  GroupSetPermissionsInputRequest,
  GroupSetPermissionsResponse,
  AvailablePermissionResponse,
  AvailableUserResponse,
  PaginatedAvailableUserResponseList,
  HarvestedComponentRequest,
  PatchedHarvestedComponentRequest,
  HarvestedComponentAcceptRequest,
  AcceptToInventoryResponse,
  HarvestedComponentScrapRequest,
  HeatMapAnnotationsSeverityEnum,
  HeatMapAnnotations,
  PaginatedHeatMapAnnotationsList,
  HeatMapAnnotationsRequest,
  PatchedHeatMapAnnotationsRequest,
  DefectTypeFacet,
  SeverityFacet,
  HeatMapFacetsResponse,
  ExternalAPIOrderIdentifier,
  ExternalAPIOrderIdentifierRequest,
  PatchedExternalAPIOrderIdentifierRequest,
  MaterialLotStatusEnum,
  MaterialLot,
  PaginatedMaterialLotList,
  MaterialLotRequest,
  PatchedMaterialLotRequest,
  MaterialLotSplitRequest,
  MaterialUsage,
  PaginatedMaterialUsageList,
  TypeEnum,
  MeasurementDefinition,
  PaginatedMeasurementDefinitionList,
  MeasurementDefinitionRequest,
  PatchedMeasurementDefinitionRequest,
  NotificationTypeEnum,
  ChannelTypeEnum,
  NotificationTaskStatusEnum,
  IntervalTypeEnum,
  NotificationSchedule,
  NotificationPreference,
  PaginatedNotificationPreferenceList,
  NotificationScheduleRequest,
  NotificationPreferenceRequest,
  PatchedNotificationPreferenceRequest,
  TestSendResponse,
  AvailableNotificationTypes,
  OrdersStatusEnum,
  Orders,
  PaginatedOrdersList,
  OrdersRequest,
  PatchedOrdersRequest,
  VisibilityEnum,
  AddNoteInputRequest,
  StepIncrementInputRequest,
  StepIncrementResponse,
  PartsStatusEnum,
  BulkAddPartsInputRequest,
  BulkRemovePartsInputRequest,
  StepDistributionResponse,
  PaginatedStepDistributionResponseList,
  api_Orders_import_create_Body,
  ImportQueued,
  ImportSummary,
  ImportResponse,
  ImportPreviewResponse,
  ImportStatusResponse,
  PartTypes,
  PaginatedPartTypesList,
  PartTypesRequest,
  PatchedPartTypesRequest,
  PartTypeSelect,
  PaginatedPartTypeSelectList,
  Parts,
  PaginatedPartsList,
  PartsRequest,
  PatchedPartsRequest,
  PartIncrementInputRequest,
  TravelerStepStatusEnum,
  TravelerOperator,
  TravelerApproval,
  TravelerEquipment,
  TravelerMeasurement,
  QualityStatusEnum,
  TravelerDefect,
  TravelerMaterial,
  TravelerAttachment,
  TravelerStepEntry,
  PartTravelerResponse,
  PartSelect,
  PaginatedPartSelectList,
  StepTypeEnum,
  DecisionTypeEnum,
  TerminalStatusEnum,
  RevisitAssignmentEnum,
  Step,
  ProcessStep,
  EdgeTypeEnum,
  ConditionOperatorEnum,
  StepEdge,
  ProcessStatusEnum,
  Processes,
  PaginatedProcessesList,
  ProcessesRequest,
  PatchedProcessesRequest,
  ProcessWithSteps,
  PaginatedProcessWithStepsList,
  ProcessWithStepsRequest,
  PatchedProcessWithStepsRequest,
  DuplicateProcessRequestRequest,
  SubmitProcessForApprovalRequestRequest,
  SubmitProcessForApprovalResponse,
  CurrentStateEnum,
  DispositionTypeEnum,
  QuarantineDisposition,
  PaginatedQuarantineDispositionList,
  QuarantineDispositionRequest,
  PatchedQuarantineDispositionRequest,
  PaginatedRcaRecordList,
  FiveWhysNestedRequest,
  FishboneNestedRequest,
  RcaRecordRequest,
  PatchedRcaRecordRequest,
  SamplingRuleSet,
  PaginatedSamplingRuleSetList,
  SamplingRuleSetRequest,
  PatchedSamplingRuleSetRequest,
  RuleTypeEnum,
  SamplingRule,
  PaginatedSamplingRuleList,
  SamplingRuleRequest,
  PatchedSamplingRuleRequest,
  ScheduleSlotStatusEnum,
  ScheduleSlot,
  PaginatedScheduleSlotList,
  ScheduleSlotRequest,
  PatchedScheduleSlotRequest,
  Shift,
  PaginatedShiftList,
  ShiftRequest,
  PatchedShiftRequest,
  StepExecutionStatusEnum,
  StepExecutionList,
  PaginatedStepExecutionListList,
  StepExecutionRequest,
  StepExecution,
  PatchedStepExecutionRequest,
  StepDurationStats,
  PaginatedStepExecutionList,
  WIPSummary,
  PaginatedWIPSummaryList,
  Steps,
  PaginatedStepsList,
  StepsRequest,
  PatchedStepsRequest,
  SamplingRuleUpdateRequest,
  StepSamplingRulesUpdateRequest,
  TenantGroup,
  PaginatedTenantGroupList,
  TenantGroupRequest,
  TenantGroupDetail,
  PatchedTenantGroupRequest,
  RemoveMemberResponse,
  TierEnum,
  TenantStatusEnum,
  Tenant,
  PaginatedTenantList,
  TenantCreateRequest,
  TenantCreate,
  TenantRequest,
  PatchedTenantRequest,
  ProcessingStatusEnum,
  ThreeDModel,
  PaginatedThreeDModelList,
  ThreeDModelRequest,
  PatchedThreeDModelRequest,
  TimeEntryTypeEnum,
  TimeEntry,
  PaginatedTimeEntryList,
  TimeEntryRequest,
  PatchedTimeEntryRequest,
  ClockOutInputRequest,
  ClockInRequest,
  CustomerOrder,
  PaginatedCustomerOrderList,
  InviteViewerInputRequest,
  InviteViewerResponse,
  InviteError,
  TrainingRecord,
  PaginatedTrainingRecordList,
  TrainingRecordRequest,
  PatchedTrainingRecordRequest,
  TrainingStats,
  TrainingRequirement,
  PaginatedTrainingRequirementList,
  TrainingRequirementRequest,
  PatchedTrainingRequirementRequest,
  TrainingType,
  PaginatedTrainingTypeList,
  TrainingTypeRequest,
  PatchedTrainingTypeRequest,
  User,
  PaginatedUserList,
  UserRequest,
  PatchedUserRequest,
  BulkUserActivationInputRequest,
  BulkCompanyAssignmentInputRequest,
  SendInvitationInputRequest,
  UserInvitation,
  PaginatedUserInvitationList,
  UserInvitationRequest,
  PatchedUserInvitationRequest,
  AcceptInvitationInputRequest,
  AcceptInvitationResponse,
  ResendInvitationInputRequest,
  ValidateTokenInputRequest,
  ValidateTokenResponse,
  WorkCenter,
  PaginatedWorkCenterList,
  WorkCenterRequest,
  WorkCenterSelect,
  PatchedWorkCenterRequest,
  WorkOrderStatusEnum,
  PriorityEnum,
  WorkOrderList,
  PaginatedWorkOrderListList,
  WorkOrderRequest,
  WorkOrder,
  PatchedWorkOrderRequest,
  QADocumentsResponse,
  StepSummary,
  WorkOrderStepHistoryResponse,
  EmbedQueryRequestRequest,
  EmbedQueryResponse,
  ExecuteQueryResponse,
  ExecuteQueryRequestRequest,
  QueryRequest,
  ContextWindowRequestRequest,
  ContextWindowResponse,
  HybridSearchRequestRequest,
  HybridSearchResponse,
  KeywordSearchResponse,
  VectorSearchRequestRequest,
  VectorSearchResponse,
  ActionEnum,
  AuditLog,
  PaginatedAuditLogList,
  ContentType,
  CAPAStatusResponse,
  DefectParetoResponse,
  DefectRecordsResponse,
  DefectTrendResponse,
  DefectsByProcessResponse,
  DispositionBreakdownResponse,
  FailedInspectionsResponse,
  FilterOptionsResponse,
  FPYTrendResponse,
  InProcessActionsResponse,
  DashboardKPIsResponse,
  NcrAgingResponse,
  NcrTrendResponse,
  NeedsAttentionResponse,
  OpenDispositionsResponse,
  QualityRatesResponse,
  RepeatDefectsResponse,
  PermissionListResponse,
  PresetListResponse,
  ReportTypeEnum,
  GenerateReportRequest,
  GenerateReportResponse,
  GeneratedReportStatusEnum,
  GeneratedReport,
  PaginatedGeneratedReportList,
  ReportTypesResponse,
  ChartTypeEnum,
  BaselineStatusEnum,
  SPCBaselineList,
  PaginatedSPCBaselineListList,
  SPCBaselineRequest,
  SPCBaseline,
  PatchedSPCBaselineRequest,
  SupersedeRequestRequest,
  SPCBaselineFreezeRequest,
  MeasurementDefinitionSPC,
  SPCCapabilityResponse,
  MeasurementDataPoint,
  SPCDataResponse,
  DimensionalResultsResponse,
  ProcessStepSPC,
  ProcessSPC,
  TenantInfo,
  ModeEnum,
  DeploymentInfo,
  CurrentTenantResponse,
  TenantLogoResponse,
  TenantLogoDeleteResponse,
  TenantSettingsResponse,
  PatchedTenantSettingsUpdateRequestRequest,
  TenantSettingsUpdateResponse,
  SignupRequest,
  SignupResponse,
  EffectivePermissionsResponse,
  LoginRequest,
  Token,
  RestAuthDetail,
  PasswordChangeRequest,
  PasswordResetRequest,
  PasswordResetConfirmRequest,
  RegisterRequest,
  ResendEmailVerificationRequest,
  VerifyEmailRequest,
  UserDetails,
  UserDetailsRequest,
  PatchedUserDetailsRequest,
  CapaTaskAssigneeRequest,
  FishboneNested,
  FiveWhysNested,
  MeasurementResult,
  ProcessStepRequest,
  RootCauseRequest,
  StepEdgeRequest,
  StepRequest,
};

const endpoints = makeApi([
  {
    method: "post",
    path: "/api/ai/embedding/embed_query/",
    alias: "api_ai_embedding_embed_query_create",
    description: `Embed a single query for vector search`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ query: z.string().min(1) }).passthrough(),
      },
    ],
    response: EmbedQueryResponse,
  },
  {
    method: "get",
    path: "/api/ai/query/execute_read_only/",
    alias: "api_ai_query_execute_read_only_retrieve",
    description: `Execute SAFE READ-ONLY ORM queries with strict validation.

GET: Returns usage information and allowed models/operations.
POST: Executes the query.`,
    requestFormat: "json",
    response: ExecuteQueryResponse,
  },
  {
    method: "post",
    path: "/api/ai/query/execute_read_only/",
    alias: "api_ai_query_execute_read_only_create",
    description: `Execute SAFE READ-ONLY ORM queries with strict validation.

GET: Returns usage information and allowed models/operations.
POST: Executes the query.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ExecuteQueryRequestRequest,
      },
    ],
    response: ExecuteQueryResponse,
  },
  {
    method: "get",
    path: "/api/ai/query/schema_info/",
    alias: "api_ai_query_schema_info_retrieve",
    description: `Return model schema information for safe ORM query building`,
    requestFormat: "json",
    response: QueryRequest,
  },
  {
    method: "post",
    path: "/api/ai/search/get_context_window/",
    alias: "api_ai_search_get_context_window_create",
    description: `Get chunk plus surrounding chunks using span_meta ordering`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ContextWindowRequestRequest,
      },
    ],
    response: ContextWindowResponse,
  },
  {
    method: "post",
    path: "/api/ai/search/hybrid_search/",
    alias: "api_ai_search_hybrid_search_create",
    description: `Combine vector similarity and keyword search results`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HybridSearchRequestRequest,
      },
    ],
    response: HybridSearchResponse,
  },
  {
    method: "get",
    path: "/api/ai/search/keyword_search/",
    alias: "api_ai_search_keyword_search_retrieve",
    description: `Full-text search on document chunks`,
    requestFormat: "json",
    parameters: [
      {
        name: "doc_ids",
        type: "Query",
        schema: z.array(z.number().int()).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "q",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: KeywordSearchResponse,
  },
  {
    method: "post",
    path: "/api/ai/search/vector_search/",
    alias: "api_ai_search_vector_search_create",
    description: `Vector similarity search on document chunks`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: VectorSearchRequestRequest,
      },
    ],
    response: z.object({ results: z.array(z.unknown()) }).passthrough(),
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/",
    alias: "api_ApprovalRequests_list",
    description: `List approval requests with filtering and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "approval_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "content_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "object_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "overdue",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "requested_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedApprovalRequestList,
  },
  {
    method: "post",
    path: "/api/ApprovalRequests/",
    alias: "api_ApprovalRequests_create",
    description: `Create a new approval request`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalRequestRequest,
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/:id/",
    alias: "api_ApprovalRequests_retrieve",
    description: `Retrieve a specific approval request`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "put",
    path: "/api/ApprovalRequests/:id/",
    alias: "api_ApprovalRequests_update",
    description: `Update an approval request`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalRequestRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "patch",
    path: "/api/ApprovalRequests/:id/",
    alias: "api_ApprovalRequests_partial_update",
    description: `Partially update an approval request`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedApprovalRequestRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "delete",
    path: "/api/ApprovalRequests/:id/",
    alias: "api_ApprovalRequests_destroy",
    description: `Cancel an approval request`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/:id/pending-approvers/",
    alias: "api_ApprovalRequests_pending_approvers_retrieve",
    description: `Get list of pending approvers for this request`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "post",
    path: "/api/ApprovalRequests/:id/submit-response/",
    alias: "api_ApprovalRequests_submit_response_create",
    description: `Submit an approval response (approve/reject/delegate)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalRequestRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalRequest,
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/export-excel/",
    alias: "api_ApprovalRequests_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/metadata/",
    alias: "api_ApprovalRequests_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/ApprovalRequests/my-pending/",
    alias: "api_ApprovalRequests_my_pending_list",
    description: `Get all approval requests pending for current user`,
    requestFormat: "json",
    parameters: [
      {
        name: "approval_type",
        type: "Query",
        schema: z
          .enum([
            "CAPA_CRITICAL",
            "CAPA_MAJOR",
            "DOCUMENT_RELEASE",
            "ECO",
            "PROCESS_APPROVAL",
            "TRAINING_CERT",
          ])
          .optional(),
      },
      {
        name: "content_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "object_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "requested_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum([
            "APPROVED",
            "CANCELLED",
            "NOT_REQUIRED",
            "PENDING",
            "REJECTED",
          ])
          .optional(),
      },
    ],
    response: PaginatedApprovalRequestList,
  },
  {
    method: "get",
    path: "/api/ApprovalResponses/",
    alias: "api_ApprovalResponses_list",
    description: `List approval responses with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "approval_request",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "approver",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "decision",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "verification_method",
        type: "Query",
        schema: z.enum(["NONE", "PASSWORD", "SSO"]).optional(),
      },
    ],
    response: PaginatedApprovalResponseList,
  },
  {
    method: "post",
    path: "/api/ApprovalResponses/",
    alias: "api_ApprovalResponses_create",
    description: `Create a new approval response`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalResponseRequest,
      },
    ],
    response: ApprovalResponse,
  },
  {
    method: "get",
    path: "/api/ApprovalResponses/:id/",
    alias: "api_ApprovalResponses_retrieve",
    description: `Retrieve a specific approval response`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalResponse,
  },
  {
    method: "put",
    path: "/api/ApprovalResponses/:id/",
    alias: "api_ApprovalResponses_update",
    description: `Update an approval response`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalResponseRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalResponse,
  },
  {
    method: "patch",
    path: "/api/ApprovalResponses/:id/",
    alias: "api_ApprovalResponses_partial_update",
    description: `Partially update an approval response`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedApprovalResponseRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalResponse,
  },
  {
    method: "delete",
    path: "/api/ApprovalResponses/:id/",
    alias: "api_ApprovalResponses_destroy",
    description: `ViewSet for managing approval responses.

Approval responses record individual approver decisions with signature capture,
identity verification, and delegation support.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/ApprovalResponses/:id/delegate/",
    alias: "api_ApprovalResponses_delegate_create",
    description: `Delegate this approval to another user`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalResponseRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalResponse,
  },
  {
    method: "get",
    path: "/api/ApprovalResponses/export-excel/",
    alias: "api_ApprovalResponses_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/ApprovalResponses/metadata/",
    alias: "api_ApprovalResponses_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/ApprovalTemplates/",
    alias: "api_ApprovalTemplates_list",
    description: `List approval templates with filtering and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "active",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "approval_flow_type",
        type: "Query",
        schema: z.enum(["ALL_REQUIRED", "ANY", "THRESHOLD"]).optional(),
      },
      {
        name: "approval_sequence",
        type: "Query",
        schema: z.enum(["PARALLEL", "SEQUENTIAL"]).optional(),
      },
      {
        name: "approval_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "delegation_policy",
        type: "Query",
        schema: z.enum(["DISABLED", "OPTIONAL"]).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedApprovalTemplateList,
  },
  {
    method: "post",
    path: "/api/ApprovalTemplates/",
    alias: "api_ApprovalTemplates_create",
    description: `Create a new approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalTemplateRequest,
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "get",
    path: "/api/ApprovalTemplates/:id/",
    alias: "api_ApprovalTemplates_retrieve",
    description: `Retrieve a specific approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "put",
    path: "/api/ApprovalTemplates/:id/",
    alias: "api_ApprovalTemplates_update",
    description: `Update an approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalTemplateRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "patch",
    path: "/api/ApprovalTemplates/:id/",
    alias: "api_ApprovalTemplates_partial_update",
    description: `Partially update an approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedApprovalTemplateRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "delete",
    path: "/api/ApprovalTemplates/:id/",
    alias: "api_ApprovalTemplates_destroy",
    description: `Soft delete an approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/ApprovalTemplates/:id/activate/",
    alias: "api_ApprovalTemplates_activate_create",
    description: `Reactivate an approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalTemplateRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "post",
    path: "/api/ApprovalTemplates/:id/deactivate/",
    alias: "api_ApprovalTemplates_deactivate_create",
    description: `Deactivate an approval template`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApprovalTemplateRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ApprovalTemplate,
  },
  {
    method: "get",
    path: "/api/ApprovalTemplates/export-excel/",
    alias: "api_ApprovalTemplates_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/ApprovalTemplates/metadata/",
    alias: "api_ApprovalTemplates_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/AssemblyUsages/",
    alias: "api_AssemblyUsages_list",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "assembly",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "bom_line",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "component",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedAssemblyUsageList,
  },
  {
    method: "post",
    path: "/api/AssemblyUsages/",
    alias: "api_AssemblyUsages_create",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AssemblyUsageRequest,
      },
    ],
    response: AssemblyUsage,
  },
  {
    method: "get",
    path: "/api/AssemblyUsages/:id/",
    alias: "api_AssemblyUsages_retrieve",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: AssemblyUsage,
  },
  {
    method: "put",
    path: "/api/AssemblyUsages/:id/",
    alias: "api_AssemblyUsages_update",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AssemblyUsageRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: AssemblyUsage,
  },
  {
    method: "patch",
    path: "/api/AssemblyUsages/:id/",
    alias: "api_AssemblyUsages_partial_update",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedAssemblyUsageRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: AssemblyUsage,
  },
  {
    method: "delete",
    path: "/api/AssemblyUsages/:id/",
    alias: "api_AssemblyUsages_destroy",
    description: `Assembly component tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/AssemblyUsages/:id/remove/",
    alias: "api_AssemblyUsages_remove_create",
    description: `Remove a component from an assembly`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ reason: z.string().default("") })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: AssemblyUsage,
  },
  {
    method: "get",
    path: "/api/auditlog/",
    alias: "api_auditlog_list",
    requestFormat: "json",
    parameters: [
      {
        name: "action",
        type: "Query",
        schema: z
          .union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)])
          .optional(),
      },
      {
        name: "actor",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "content_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "object_pk",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedAuditLogList,
  },
  {
    method: "get",
    path: "/api/auditlog/:id/",
    alias: "api_auditlog_retrieve",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: AuditLog,
  },
  {
    method: "get",
    path: "/api/BOMLines/",
    alias: "api_BOMLines_list",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "bom",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "component_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "is_optional",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedBOMLineList,
  },
  {
    method: "post",
    path: "/api/BOMLines/",
    alias: "api_BOMLines_create",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BOMLineRequest,
      },
    ],
    response: BOMLine,
  },
  {
    method: "get",
    path: "/api/BOMLines/:id/",
    alias: "api_BOMLines_retrieve",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOMLine,
  },
  {
    method: "put",
    path: "/api/BOMLines/:id/",
    alias: "api_BOMLines_update",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BOMLineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOMLine,
  },
  {
    method: "patch",
    path: "/api/BOMLines/:id/",
    alias: "api_BOMLines_partial_update",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedBOMLineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOMLine,
  },
  {
    method: "delete",
    path: "/api/BOMLines/:id/",
    alias: "api_BOMLines_destroy",
    description: `BOM line item management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/BOMs/",
    alias: "api_BOMs_list",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "bom_type",
        type: "Query",
        schema: z.enum(["assembly", "disassembly"]).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.enum(["draft", "obsolete", "released"]).optional(),
      },
    ],
    response: PaginatedBOMListList,
  },
  {
    method: "post",
    path: "/api/BOMs/",
    alias: "api_BOMs_create",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BOMRequest,
      },
    ],
    response: BOM,
  },
  {
    method: "get",
    path: "/api/BOMs/:id/",
    alias: "api_BOMs_retrieve",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOM,
  },
  {
    method: "put",
    path: "/api/BOMs/:id/",
    alias: "api_BOMs_update",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BOMRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOM,
  },
  {
    method: "patch",
    path: "/api/BOMs/:id/",
    alias: "api_BOMs_partial_update",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedBOMRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOM,
  },
  {
    method: "delete",
    path: "/api/BOMs/:id/",
    alias: "api_BOMs_destroy",
    description: `Bill of Materials management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/BOMs/:id/obsolete/",
    alias: "api_BOMs_obsolete_create",
    description: `Mark a BOM as obsolete`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOM,
  },
  {
    method: "post",
    path: "/api/BOMs/:id/release/",
    alias: "api_BOMs_release_create",
    description: `Release a BOM for production use`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: BOM,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/",
    alias: "api_CalibrationRecords_list",
    description: `List calibration records with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "calibration_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "equipment",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "result",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCalibrationRecordList,
  },
  {
    method: "post",
    path: "/api/CalibrationRecords/",
    alias: "api_CalibrationRecords_create",
    description: `Create a new calibration record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CalibrationRecordRequest,
      },
    ],
    response: CalibrationRecord,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/:id/",
    alias: "api_CalibrationRecords_retrieve",
    description: `Retrieve a specific calibration record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CalibrationRecord,
  },
  {
    method: "put",
    path: "/api/CalibrationRecords/:id/",
    alias: "api_CalibrationRecords_update",
    description: `Update a calibration record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CalibrationRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CalibrationRecord,
  },
  {
    method: "patch",
    path: "/api/CalibrationRecords/:id/",
    alias: "api_CalibrationRecords_partial_update",
    description: `Partially update a calibration record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCalibrationRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CalibrationRecord,
  },
  {
    method: "delete",
    path: "/api/CalibrationRecords/:id/",
    alias: "api_CalibrationRecords_destroy",
    description: `Soft delete a calibration record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/due-soon/",
    alias: "api_CalibrationRecords_due_soon_list",
    description: `Get calibration records due within N days (default 30)`,
    requestFormat: "json",
    parameters: [
      {
        name: "calibration_type",
        type: "Query",
        schema: z
          .enum([
            "after_adjustment",
            "after_repair",
            "initial",
            "scheduled",
            "verification",
          ])
          .optional(),
      },
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "equipment",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "result",
        type: "Query",
        schema: z.enum(["fail", "limited", "pass"]).optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCalibrationRecordList,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/export-excel/",
    alias: "api_CalibrationRecords_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/for-equipment/",
    alias: "api_CalibrationRecords_for_equipment_list",
    description: `Get calibration history for a specific piece of equipment`,
    requestFormat: "json",
    parameters: [
      {
        name: "calibration_type",
        type: "Query",
        schema: z
          .enum([
            "after_adjustment",
            "after_repair",
            "initial",
            "scheduled",
            "verification",
          ])
          .optional(),
      },
      {
        name: "equipment",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "equipment_id",
        type: "Query",
        schema: z.string(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "result",
        type: "Query",
        schema: z.enum(["fail", "limited", "pass"]).optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCalibrationRecordList,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/metadata/",
    alias: "api_CalibrationRecords_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/overdue/",
    alias: "api_CalibrationRecords_overdue_list",
    description: `Get all overdue calibration records`,
    requestFormat: "json",
    parameters: [
      {
        name: "calibration_type",
        type: "Query",
        schema: z
          .enum([
            "after_adjustment",
            "after_repair",
            "initial",
            "scheduled",
            "verification",
          ])
          .optional(),
      },
      {
        name: "equipment",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "result",
        type: "Query",
        schema: z.enum(["fail", "limited", "pass"]).optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCalibrationRecordList,
  },
  {
    method: "get",
    path: "/api/CalibrationRecords/stats/",
    alias: "api_CalibrationRecords_stats_retrieve",
    description: `Get calibration statistics summary`,
    requestFormat: "json",
    response: CalibrationStats,
  },
  {
    method: "get",
    path: "/api/CAPAs/",
    alias: "api_CAPAs_list",
    description: `List CAPAs with filtering and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "capa_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "initiated_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "overdue",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "severity",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCAPAList,
  },
  {
    method: "post",
    path: "/api/CAPAs/",
    alias: "api_CAPAs_create",
    description: `Create a new CAPA`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CAPARequest,
      },
    ],
    response: CAPA,
  },
  {
    method: "get",
    path: "/api/CAPAs/:id/",
    alias: "api_CAPAs_retrieve",
    description: `Retrieve a specific CAPA`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "put",
    path: "/api/CAPAs/:id/",
    alias: "api_CAPAs_update",
    description: `Update a CAPA`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CAPARequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "patch",
    path: "/api/CAPAs/:id/",
    alias: "api_CAPAs_partial_update",
    description: `Partially update a CAPA`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCAPARequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "delete",
    path: "/api/CAPAs/:id/",
    alias: "api_CAPAs_destroy",
    description: `Soft delete a CAPA`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/CAPAs/:id/blocking-items/",
    alias: "api_CAPAs_blocking_items_retrieve",
    description: `Get list of blocking items preventing closure`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "get",
    path: "/api/CAPAs/:id/completion-percentage/",
    alias: "api_CAPAs_completion_percentage_retrieve",
    description: `Get completion percentage of CAPA tasks`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "post",
    path: "/api/CAPAs/:id/request-approval/",
    alias: "api_CAPAs_request_approval_create",
    description: `Manually request approval for CAPA (typically for Critical/Major severity)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CAPARequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CAPA,
  },
  {
    method: "get",
    path: "/api/CAPAs/export-excel/",
    alias: "api_CAPAs_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/CAPAs/metadata/",
    alias: "api_CAPAs_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/CAPAs/my-assigned/",
    alias: "api_CAPAs_my_assigned_retrieve",
    description: `Get all CAPAs assigned to current user`,
    requestFormat: "json",
    response: CAPA,
  },
  {
    method: "get",
    path: "/api/CAPAs/stats/",
    alias: "api_CAPAs_stats_retrieve",
    description: `Get aggregated CAPA statistics for dashboard display`,
    requestFormat: "json",
    response: z
      .object({
        total: z.number().int(),
        by_status: z
          .object({
            open: z.number().int(),
            in_progress: z.number().int(),
            pending_verification: z.number().int(),
            closed: z.number().int(),
          })
          .partial()
          .passthrough(),
        by_severity: z
          .object({
            CRITICAL: z.number().int(),
            MAJOR: z.number().int(),
            MINOR: z.number().int(),
          })
          .partial()
          .passthrough(),
        overdue: z.number().int(),
      })
      .partial()
      .passthrough(),
  },
  {
    method: "get",
    path: "/api/CapaTasks/",
    alias: "api_CapaTasks_list",
    description: `List CAPA tasks with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "capa",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "completion_mode",
        type: "Query",
        schema: z
          .enum(["ALL_ASSIGNEES", "ANY_ASSIGNEE", "SINGLE_OWNER"])
          .optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "overdue",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "task_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCapaTasksList,
  },
  {
    method: "post",
    path: "/api/CapaTasks/",
    alias: "api_CapaTasks_create",
    description: `Create a new CAPA task`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CapaTasksRequest,
      },
    ],
    response: CapaTasks,
  },
  {
    method: "get",
    path: "/api/CapaTasks/:id/",
    alias: "api_CapaTasks_retrieve",
    description: `Retrieve a specific CAPA task`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaTasks,
  },
  {
    method: "put",
    path: "/api/CapaTasks/:id/",
    alias: "api_CapaTasks_update",
    description: `Update a CAPA task`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CapaTasksRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaTasks,
  },
  {
    method: "patch",
    path: "/api/CapaTasks/:id/",
    alias: "api_CapaTasks_partial_update",
    description: `Partially update a CAPA task`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCapaTasksRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaTasks,
  },
  {
    method: "delete",
    path: "/api/CapaTasks/:id/",
    alias: "api_CapaTasks_destroy",
    description: `Soft delete a CAPA task`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/CapaTasks/:id/complete/",
    alias: "api_CapaTasks_complete_create",
    description: `Mark task as complete

If task.requires_signature is True, signature_data and password are required.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CapaTasksRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaTasks,
  },
  {
    method: "get",
    path: "/api/CapaTasks/export-excel/",
    alias: "api_CapaTasks_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/CapaTasks/metadata/",
    alias: "api_CapaTasks_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/CapaTasks/my-tasks/",
    alias: "api_CapaTasks_my_tasks_list",
    description: `Get all tasks assigned to current user`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "capa",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "completion_mode",
        type: "Query",
        schema: z
          .enum(["ALL_ASSIGNEES", "ANY_ASSIGNEE", "SINGLE_OWNER"])
          .optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["CANCELLED", "COMPLETED", "IN_PROGRESS", "NOT_STARTED"])
          .optional(),
      },
      {
        name: "task_type",
        type: "Query",
        schema: z.enum(["CONTAINMENT", "CORRECTIVE", "PREVENTIVE"]).optional(),
      },
    ],
    response: PaginatedCapaTasksList,
  },
  {
    method: "get",
    path: "/api/CapaVerifications/",
    alias: "api_CapaVerifications_list",
    description: `List CAPA verifications with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "capa",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "effectiveness_result",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "verified_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedCapaVerificationList,
  },
  {
    method: "post",
    path: "/api/CapaVerifications/",
    alias: "api_CapaVerifications_create",
    description: `Create a new CAPA verification`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CapaVerificationRequest,
      },
    ],
    response: CapaVerification,
  },
  {
    method: "get",
    path: "/api/CapaVerifications/:id/",
    alias: "api_CapaVerifications_retrieve",
    description: `Retrieve a specific CAPA verification`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaVerification,
  },
  {
    method: "put",
    path: "/api/CapaVerifications/:id/",
    alias: "api_CapaVerifications_update",
    description: `Update a CAPA verification`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CapaVerificationRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaVerification,
  },
  {
    method: "patch",
    path: "/api/CapaVerifications/:id/",
    alias: "api_CapaVerifications_partial_update",
    description: `Partially update a CAPA verification`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCapaVerificationRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CapaVerification,
  },
  {
    method: "delete",
    path: "/api/CapaVerifications/:id/",
    alias: "api_CapaVerifications_destroy",
    description: `Soft delete a CAPA verification`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/CapaVerifications/export-excel/",
    alias: "api_CapaVerifications_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/CapaVerifications/metadata/",
    alias: "api_CapaVerifications_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/ChatSessions/",
    alias: "api_ChatSessions_list",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedChatSessionList,
  },
  {
    method: "post",
    path: "/api/ChatSessions/",
    alias: "api_ChatSessions_create",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ChatSessionRequest,
      },
    ],
    response: ChatSession,
  },
  {
    method: "get",
    path: "/api/ChatSessions/:id/",
    alias: "api_ChatSessions_retrieve",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ChatSession,
  },
  {
    method: "put",
    path: "/api/ChatSessions/:id/",
    alias: "api_ChatSessions_update",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ChatSessionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ChatSession,
  },
  {
    method: "patch",
    path: "/api/ChatSessions/:id/",
    alias: "api_ChatSessions_partial_update",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedChatSessionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ChatSession,
  },
  {
    method: "delete",
    path: "/api/ChatSessions/:id/",
    alias: "api_ChatSessions_destroy",
    description: `ViewSet for managing AI chat sessions.

Users can only see and manage their own chat sessions.
Provides list, create, retrieve, update, and delete operations.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/ChatSessions/:id/archive/",
    alias: "api_ChatSessions_archive_create",
    description: `Archive a chat session.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ChatSessionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ChatSession,
  },
  {
    method: "post",
    path: "/api/ChatSessions/:id/unarchive/",
    alias: "api_ChatSessions_unarchive_create",
    description: `Unarchive a chat session.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ChatSessionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ChatSession,
  },
  {
    method: "get",
    path: "/api/Companies/",
    alias: "api_Companies_list",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCompanyList,
  },
  {
    method: "post",
    path: "/api/Companies/",
    alias: "api_Companies_create",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CompanyRequest,
      },
    ],
    response: Company,
  },
  {
    method: "get",
    path: "/api/Companies/:id/",
    alias: "api_Companies_retrieve",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Company,
  },
  {
    method: "put",
    path: "/api/Companies/:id/",
    alias: "api_Companies_update",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CompanyRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Company,
  },
  {
    method: "patch",
    path: "/api/Companies/:id/",
    alias: "api_Companies_partial_update",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCompanyRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Company,
  },
  {
    method: "delete",
    path: "/api/Companies/:id/",
    alias: "api_Companies_destroy",
    description: `Company management - scoped to tenant and user permissions.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Companies/export-excel/",
    alias: "api_Companies_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Companies/metadata/",
    alias: "api_Companies_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/content-types/",
    alias: "api_content_types_list",
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(ContentType),
  },
  {
    method: "get",
    path: "/api/content-types/:id/",
    alias: "api_content_types_retrieve",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ContentType,
  },
  {
    method: "get",
    path: "/api/Cores/",
    alias: "api_Cores_list",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "condition_grade",
        type: "Query",
        schema: z.enum(["A", "B", "C", "SCRAP"]).optional(),
      },
      {
        name: "core_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "customer",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "source_type",
        type: "Query",
        schema: z
          .enum(["customer_return", "purchased", "trade_in", "warranty"])
          .optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["disassembled", "in_disassembly", "received", "scrapped"])
          .optional(),
      },
    ],
    response: PaginatedCoreListList,
  },
  {
    method: "post",
    path: "/api/Cores/",
    alias: "api_Cores_create",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CoreRequest,
      },
    ],
    response: Core,
  },
  {
    method: "get",
    path: "/api/Cores/:id/",
    alias: "api_Cores_retrieve",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "put",
    path: "/api/Cores/:id/",
    alias: "api_Cores_update",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: CoreRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "patch",
    path: "/api/Cores/:id/",
    alias: "api_Cores_partial_update",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedCoreRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "delete",
    path: "/api/Cores/:id/",
    alias: "api_Cores_destroy",
    description: `Remanufacturing core management with disassembly workflow.

Workflow:
1. Create core (status: received)
2. start_disassembly -&gt; status: in_disassembly
3. Create HarvestedComponents as components are extracted
4. complete_disassembly -&gt; status: disassembled

Alternative: scrap -&gt; status: scrapped (if core not suitable)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Cores/:id/complete_disassembly/",
    alias: "api_Cores_complete_disassembly_create",
    description: `Complete disassembly of a core`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "get",
    path: "/api/Cores/:id/components/",
    alias: "api_Cores_components_list",
    description: `List all harvested components from this core`,
    requestFormat: "json",
    parameters: [
      {
        name: "condition_grade",
        type: "Query",
        schema: z.enum(["A", "B", "C", "SCRAP"]).optional(),
      },
      {
        name: "core_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "customer",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "source_type",
        type: "Query",
        schema: z
          .enum(["customer_return", "purchased", "trade_in", "warranty"])
          .optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["disassembled", "in_disassembly", "received", "scrapped"])
          .optional(),
      },
    ],
    response: PaginatedHarvestedComponentList,
  },
  {
    method: "post",
    path: "/api/Cores/:id/issue_credit/",
    alias: "api_Cores_issue_credit_create",
    description: `Issue core credit to customer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "post",
    path: "/api/Cores/:id/scrap/",
    alias: "api_Cores_scrap_create",
    description: `Scrap a core (not suitable for disassembly)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ reason: z.string().default("") })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "post",
    path: "/api/Cores/:id/start_disassembly/",
    alias: "api_Cores_start_disassembly_create",
    description: `Start disassembly of a core`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Core,
  },
  {
    method: "get",
    path: "/api/Cores/export-excel/",
    alias: "api_Cores_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Customers/",
    alias: "api_Customers_list",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(UserDetail),
  },
  {
    method: "post",
    path: "/api/Customers/",
    alias: "api_Customers_create",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserDetailRequest,
      },
    ],
    response: UserDetail,
  },
  {
    method: "get",
    path: "/api/Customers/:id/",
    alias: "api_Customers_retrieve",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserDetail,
  },
  {
    method: "put",
    path: "/api/Customers/:id/",
    alias: "api_Customers_update",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserDetailRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserDetail,
  },
  {
    method: "patch",
    path: "/api/Customers/:id/",
    alias: "api_Customers_partial_update",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedUserDetailRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserDetail,
  },
  {
    method: "delete",
    path: "/api/Customers/:id/",
    alias: "api_Customers_destroy",
    description: `Customer (non-staff user) management.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Customers/export-excel/",
    alias: "api_Customers_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Customers/metadata/",
    alias: "api_Customers_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/capa-status/",
    alias: "api_dashboard_capa_status_retrieve",
    description: `Get CAPA status distribution for pie chart.

Response:
{
    &quot;data&quot;: [
        {&quot;status&quot;: &quot;Open&quot;, &quot;value&quot;: 2},
        {&quot;status&quot;: &quot;In Progress&quot;, &quot;value&quot;: 4},
        {&quot;status&quot;: &quot;Pending Verification&quot;, &quot;value&quot;: 2}
    ],
    &quot;total&quot;: 8
}`,
    requestFormat: "json",
    response: CAPAStatusResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/defect-pareto/",
    alias: "api_dashboard_defect_pareto_retrieve",
    description: `Get defect counts by error type for Pareto analysis.

Query params:
    days (optional): Number of days to include (default: 30)
    limit (optional): Max number of error types (default: 10)

Response:
{
    &quot;data&quot;: [
        {&quot;error_type&quot;: &quot;Dimensional&quot;, &quot;count&quot;: 18, &quot;cumulative&quot;: 33},
        {&quot;error_type&quot;: &quot;Scratch&quot;, &quot;count&quot;: 14, &quot;cumulative&quot;: 59},
        ...
    ],
    &quot;total&quot;: 54
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
    ],
    response: DefectParetoResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/defect-records/",
    alias: "api_dashboard_defect_records_retrieve",
    description: `Get filtered defect (failed quality report) records for drill-down table.

Query params:
    days (optional): Number of days to include (default: 30)
    defect_type (optional): Filter by error type name
    process (optional): Filter by step/process name
    part_type (optional): Filter by part type name
    limit (optional): Max number of records (default: 50)
    offset (optional): Pagination offset (default: 0)

Response:
{
    &quot;data&quot;: [
        {
            &quot;id&quot;: 123,
            &quot;part_erp_id&quot;: &quot;CRI-0042&quot;,
            &quot;part_id&quot;: 456,
            &quot;part_type&quot;: &quot;Common Rail Injector&quot;,
            &quot;part_type_id&quot;: 1,
            &quot;step&quot;: &quot;Flow Testing&quot;,
            &quot;step_id&quot;: 5,
            &quot;error_types&quot;: [&quot;Dimensional&quot;, &quot;Surface&quot;],
            &quot;inspector&quot;: &quot;J. Smith&quot;,
            &quot;date&quot;: &quot;2025-01-02&quot;,
            &quot;date_formatted&quot;: &quot;Jan 02&quot;,
            &quot;order&quot;: &quot;ORD-2501-003&quot;,
            &quot;order_id&quot;: 789,
            &quot;work_order&quot;: &quot;WO-2501-CRI-01&quot;,
            &quot;work_order_id&quot;: 101,
            &quot;disposition_status&quot;: &quot;OPEN&quot;,
            &quot;disposition_type&quot;: &quot;REWORK&quot;,
            &quot;description&quot;: &quot;Flow rate below specification...&quot;
        },
        ...
    ],
    &quot;total&quot;: 127,
    &quot;filters_applied&quot;: {
        &quot;defect_type&quot;: &quot;Dimensional&quot;,
        &quot;process&quot;: null,
        &quot;part_type&quot;: null,
        &quot;days&quot;: 30
    }
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "defect_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(50),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional().default(0),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: DefectRecordsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/defect-trend/",
    alias: "api_dashboard_defect_trend_retrieve",
    description: `Get defect count trend over time.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;data&quot;: [
        {&quot;date&quot;: &quot;2025-01-01&quot;, &quot;label&quot;: &quot;Jan 1&quot;, &quot;count&quot;: 5, &quot;ts&quot;: 1704067200000},
        ...
    ],
    &quot;summary&quot;: {
        &quot;total&quot;: 127,
        &quot;daily_avg&quot;: 4.2,
        &quot;trend_direction&quot;: &quot;down&quot;,
        &quot;trend_change&quot;: -12.5
    }
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: DefectTrendResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/defects-by-process/",
    alias: "api_dashboard_defects_by_process_retrieve",
    description: `Get defect counts grouped by process step.

Query params:
    days (optional): Number of days to include (default: 30)
    limit (optional): Max number of processes (default: 10)

Response:
{
    &quot;data&quot;: [
        {&quot;process_name&quot;: &quot;Final Assembly&quot;, &quot;count&quot;: 18},
        {&quot;process_name&quot;: &quot;Machining&quot;, &quot;count&quot;: 12},
        ...
    ],
    &quot;total&quot;: 54
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
    ],
    response: DefectsByProcessResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/disposition-breakdown/",
    alias: "api_dashboard_disposition_breakdown_retrieve",
    description: `Get disposition counts by type for pie/donut chart.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;data&quot;: [
        {&quot;type&quot;: &quot;Rework&quot;, &quot;count&quot;: 15, &quot;percentage&quot;: 45},
        {&quot;type&quot;: &quot;Scrap&quot;, &quot;count&quot;: 8, &quot;percentage&quot;: 24},
        {&quot;type&quot;: &quot;Use As-Is&quot;, &quot;count&quot;: 10, &quot;percentage&quot;: 31}
    ],
    &quot;total&quot;: 33
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: DispositionBreakdownResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/failed-inspections/",
    alias: "api_dashboard_failed_inspections_retrieve",
    description: `Get recent failed quality inspections.

Query params:
    limit (optional): Max number of items (default: 10)
    days (optional): Number of days to look back (default: 14)

Response:
{
    &quot;data&quot;: [
        {
            &quot;id&quot;: 1,
            &quot;part&quot;: &quot;PN-2025-1847-003&quot;,
            &quot;step&quot;: &quot;Final Assembly&quot;,
            &quot;error_type&quot;: &quot;Dimensional&quot;,
            &quot;inspector&quot;: &quot;Chen&quot;,
            &quot;date&quot;: &quot;Dec 14&quot;
        },
        ...
    ]
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(14),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
    ],
    response: FailedInspectionsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/filter-options/",
    alias: "api_dashboard_filter_options_retrieve",
    description: `Get available filter options for defect analysis drill-down.
Returns lists of defect types, processes, and part types that have defects.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;defect_types&quot;: [
        {&quot;value&quot;: &quot;Dimensional&quot;, &quot;label&quot;: &quot;Dimensional&quot;, &quot;count&quot;: 45},
        ...
    ],
    &quot;processes&quot;: [
        {&quot;value&quot;: &quot;Flow Testing&quot;, &quot;label&quot;: &quot;Flow Testing&quot;, &quot;count&quot;: 32},
        ...
    ],
    &quot;part_types&quot;: [
        {&quot;value&quot;: &quot;Common Rail Injector&quot;, &quot;label&quot;: &quot;Common Rail Injector&quot;, &quot;count&quot;: 28},
        ...
    ]
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: FilterOptionsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/fpy-trend/",
    alias: "api_dashboard_fpy_trend_retrieve",
    description: `Get First Pass Yield trend over time.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;data&quot;: [
        {&quot;date&quot;: &quot;2025-01-01&quot;, &quot;label&quot;: &quot;Jan 1&quot;, &quot;fpy&quot;: 94.5, &quot;total&quot;: 50, &quot;passed&quot;: 47},
        ...
    ],
    &quot;average&quot;: 93.2
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: FPYTrendResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/in-process-actions/",
    alias: "api_dashboard_in_process_actions_retrieve",
    description: `Get list of active CAPAs for the actions table.

Query params:
    limit (optional): Max number of items (default: 10)

Response:
{
    &quot;data&quot;: [
        {
            &quot;id&quot;: &quot;CAPA-2025-008&quot;,
            &quot;type&quot;: &quot;CAPA&quot;,
            &quot;title&quot;: &quot;Seal leak failures&quot;,
            &quot;assignee&quot;: &quot;J. Gomez&quot;,
            &quot;due&quot;: &quot;2025-12-18&quot;,
            &quot;status&quot;: &quot;IN_PROGRESS&quot;
        },
        ...
    ]
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
    ],
    response: InProcessActionsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/kpis/",
    alias: "api_dashboard_kpis_retrieve",
    description: `Get key performance indicators for dashboard cards.

Response:
{
    &quot;active_capas&quot;: 8,
    &quot;open_ncrs&quot;: 12,
    &quot;overdue_capas&quot;: 2,
    &quot;parts_in_quarantine&quot;: 5,
    &quot;current_fpy&quot;: 93.5
}`,
    requestFormat: "json",
    response: DashboardKPIsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/ncr-aging/",
    alias: "api_dashboard_ncr_aging_retrieve",
    description: `Get NCR aging buckets for currently open NCRs.

Response:
{
    &quot;data&quot;: [
        {&quot;bucket&quot;: &quot;0-3 days&quot;, &quot;count&quot;: 8},
        {&quot;bucket&quot;: &quot;4-7 days&quot;, &quot;count&quot;: 5},
        {&quot;bucket&quot;: &quot;8-14 days&quot;, &quot;count&quot;: 3},
        {&quot;bucket&quot;: &quot;&gt;14 days&quot;, &quot;count&quot;: 2}
    ],
    &quot;avg_age_days&quot;: 5.2,
    &quot;overdue_count&quot;: 2
}`,
    requestFormat: "json",
    response: NcrAgingResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/ncr-trend/",
    alias: "api_dashboard_ncr_trend_retrieve",
    description: `Get NCR (failed inspections) created/closed trend over time.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;data&quot;: [
        {&quot;date&quot;: &quot;2025-01-01&quot;, &quot;created&quot;: 3, &quot;closed&quot;: 2, &quot;net_open&quot;: 1},
        ...
    ],
    &quot;summary&quot;: {
        &quot;total_created&quot;: 45,
        &quot;total_closed&quot;: 38,
        &quot;net_change&quot;: 7
    }
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: NcrTrendResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/needs-attention/",
    alias: "api_dashboard_needs_attention_retrieve",
    description: `Get priority items that need attention for the overview dashboard.

Response:
{
    &quot;data&quot;: [
        {
            &quot;type&quot;: &quot;ncr&quot;,
            &quot;message&quot;: &quot;NCRs open &gt; 7 days&quot;,
            &quot;count&quot;: 3,
            &quot;severity&quot;: &quot;high&quot;,
            &quot;link&quot;: &quot;/quality/ncrs&quot;,
            &quot;linkParams&quot;: {&quot;aging&quot;: &quot;overdue&quot;}
        },
        ...
    ]
}`,
    requestFormat: "json",
    response: NeedsAttentionResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/open-dispositions/",
    alias: "api_dashboard_open_dispositions_retrieve",
    description: `Get open/pending dispositions.

Query params:
    limit (optional): Max number of items (default: 10)

Response:
{
    &quot;data&quot;: [
        {
            &quot;id&quot;: 1,
            &quot;part&quot;: &quot;PN-2025-1847-003&quot;,
            &quot;disposition&quot;: &quot;REWORK&quot;,
            &quot;reason&quot;: &quot;Dim out of spec&quot;,
            &quot;assignee&quot;: &quot;Rivera&quot;,
            &quot;created&quot;: &quot;Dec 14&quot;
        },
        ...
    ]
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
    ],
    response: OpenDispositionsResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/quality-rates/",
    alias: "api_dashboard_quality_rates_retrieve",
    description: `Get scrap and rework rates for the specified period.

Query params:
    days (optional): Number of days to include (default: 30)

Response:
{
    &quot;scrap_rate&quot;: 1.2,
    &quot;rework_rate&quot;: 3.4,
    &quot;use_as_is_rate&quot;: 0.8,
    &quot;total_inspected&quot;: 500,
    &quot;total_failed&quot;: 27
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
    ],
    response: QualityRatesResponse,
  },
  {
    method: "get",
    path: "/api/dashboard/repeat-defects/",
    alias: "api_dashboard_repeat_defects_retrieve",
    description: `Get recurring defects (same error type appearing multiple times).

Query params:
    days (optional): Number of days to include (default: 30)
    min_occurrences (optional): Min occurrences to be considered repeat (default: 3)
    limit (optional): Max number of items (default: 10)

Response:
{
    &quot;data&quot;: [
        {
            &quot;error_type&quot;: &quot;Dimensional&quot;,
            &quot;count&quot;: 12,
            &quot;part_types_affected&quot;: [&quot;Bracket&quot;, &quot;Housing&quot;],
            &quot;processes_affected&quot;: [&quot;Machining&quot;, &quot;Assembly&quot;]
        },
        ...
    ],
    &quot;total_repeat_count&quot;: 28
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(10),
      },
      {
        name: "min_occurrences",
        type: "Query",
        schema: z.number().int().optional().default(3),
      },
    ],
    response: RepeatDefectsResponse,
  },
  {
    method: "get",
    path: "/api/DisassemblyBOMLines/",
    alias: "api_DisassemblyBOMLines_list",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "component_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "core_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedDisassemblyBOMLineList,
  },
  {
    method: "post",
    path: "/api/DisassemblyBOMLines/",
    alias: "api_DisassemblyBOMLines_create",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DisassemblyBOMLineRequest,
      },
    ],
    response: DisassemblyBOMLine,
  },
  {
    method: "get",
    path: "/api/DisassemblyBOMLines/:id/",
    alias: "api_DisassemblyBOMLines_retrieve",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DisassemblyBOMLine,
  },
  {
    method: "put",
    path: "/api/DisassemblyBOMLines/:id/",
    alias: "api_DisassemblyBOMLines_update",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DisassemblyBOMLineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DisassemblyBOMLine,
  },
  {
    method: "patch",
    path: "/api/DisassemblyBOMLines/:id/",
    alias: "api_DisassemblyBOMLines_partial_update",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedDisassemblyBOMLineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DisassemblyBOMLine,
  },
  {
    method: "delete",
    path: "/api/DisassemblyBOMLines/:id/",
    alias: "api_DisassemblyBOMLines_destroy",
    description: `Disassembly BOM line management (expected yields from cores)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Documents/",
    alias: "api_Documents_list",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "json",
    parameters: [
      {
        name: "content_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "is_image",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "object_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["APPROVED", "DRAFT", "OBSOLETE", "RELEASED", "UNDER_REVIEW"])
          .optional(),
      },
    ],
    response: PaginatedDocumentsList,
  },
  {
    method: "post",
    path: "/api/Documents/",
    alias: "api_Documents_create",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
    ],
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/:id/",
    alias: "api_Documents_retrieve",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "put",
    path: "/api/Documents/:id/",
    alias: "api_Documents_update",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "patch",
    path: "/api/Documents/:id/",
    alias: "api_Documents_partial_update",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedDocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "delete",
    path: "/api/Documents/:id/",
    alias: "api_Documents_destroy",
    description: `ViewSet for managing document attachments (universal infrastructure)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Documents/:id/download/",
    alias: "api_Documents_download_retrieve",
    description: `Download the actual file`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "post",
    path: "/api/Documents/:id/mark-obsolete/",
    alias: "api_Documents_mark_obsolete_create",
    description: `Mark a released/approved document as obsolete.

Sets status to OBSOLETE and records the obsolete_date.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "post",
    path: "/api/Documents/:id/release/",
    alias: "api_Documents_release_create",
    description: `Release an approved document.

Sets status to RELEASED and calculates compliance dates (effective_date,
review_date, retention_until) based on document_type settings.

Optional body:
- effective_date: Override the effective date (ISO format, defaults to today)`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "post",
    path: "/api/Documents/:id/revise/",
    alias: "api_Documents_revise_create",
    description: `Create a new revision of this document.

Requires:
- file: The new file for the revision (optional - can keep same file)
- change_justification: Reason for the revision (required)

The new version will:
- Increment the version number
- Link to the previous version
- Reset status to DRAFT
- Preserve document_type, classification, and linked object`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "post",
    path: "/api/Documents/:id/submit-for-approval/",
    alias: "api_Documents_submit_for_approval_create",
    description: `Submit document for approval workflow`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/:id/version-history/",
    alias: "api_Documents_version_history_retrieve",
    description: `Get the full version history for this document`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/due-for-review/",
    alias: "api_Documents_due_for_review_retrieve",
    description: `Get documents that are due for periodic review.

Returns documents where review_date &lt;&#x3D; today.`,
    requestFormat: "json",
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/export-excel/",
    alias: "api_Documents_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Documents/metadata/",
    alias: "api_Documents_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Documents/my-uploads/",
    alias: "api_Documents_my_uploads_retrieve",
    description: `Get documents uploaded by the current user`,
    requestFormat: "json",
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/recent/",
    alias: "api_Documents_recent_retrieve",
    description: `Get recently updated documents`,
    requestFormat: "json",
    response: Documents,
  },
  {
    method: "get",
    path: "/api/Documents/stats/",
    alias: "api_Documents_stats_retrieve",
    description: `Get document statistics for dashboard`,
    requestFormat: "json",
    response: Documents,
  },
  {
    method: "get",
    path: "/api/DocumentTypes/",
    alias: "api_DocumentTypes_list",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "requires_approval",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedDocumentTypeList,
  },
  {
    method: "post",
    path: "/api/DocumentTypes/",
    alias: "api_DocumentTypes_create",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentTypeRequest,
      },
    ],
    response: DocumentType,
  },
  {
    method: "get",
    path: "/api/DocumentTypes/:id/",
    alias: "api_DocumentTypes_retrieve",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DocumentType,
  },
  {
    method: "put",
    path: "/api/DocumentTypes/:id/",
    alias: "api_DocumentTypes_update",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DocumentType,
  },
  {
    method: "patch",
    path: "/api/DocumentTypes/:id/",
    alias: "api_DocumentTypes_partial_update",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedDocumentTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DocumentType,
  },
  {
    method: "delete",
    path: "/api/DocumentTypes/:id/",
    alias: "api_DocumentTypes_destroy",
    description: `ViewSet for managing document types`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/DocumentTypes/export-excel/",
    alias: "api_DocumentTypes_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/DocumentTypes/metadata/",
    alias: "api_DocumentTypes_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/DowntimeEvents/",
    alias: "api_DowntimeEvents_list",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "category",
        type: "Query",
        schema: z
          .enum([
            "calibration",
            "changeover",
            "material",
            "no_operator",
            "no_work",
            "other",
            "planned",
            "quality",
            "unplanned",
          ])
          .optional(),
      },
      {
        name: "equipment",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "work_center",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedDowntimeEventList,
  },
  {
    method: "post",
    path: "/api/DowntimeEvents/",
    alias: "api_DowntimeEvents_create",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DowntimeEventRequest,
      },
    ],
    response: DowntimeEvent,
  },
  {
    method: "get",
    path: "/api/DowntimeEvents/:id/",
    alias: "api_DowntimeEvents_retrieve",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DowntimeEvent,
  },
  {
    method: "put",
    path: "/api/DowntimeEvents/:id/",
    alias: "api_DowntimeEvents_update",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DowntimeEventRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DowntimeEvent,
  },
  {
    method: "patch",
    path: "/api/DowntimeEvents/:id/",
    alias: "api_DowntimeEvents_partial_update",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedDowntimeEventRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DowntimeEvent,
  },
  {
    method: "delete",
    path: "/api/DowntimeEvents/:id/",
    alias: "api_DowntimeEvents_destroy",
    description: `Equipment/work center downtime tracking`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/DowntimeEvents/:id/resolve/",
    alias: "api_DowntimeEvents_resolve_create",
    description: `Mark downtime event as resolved`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: DowntimeEvent,
  },
  {
    method: "get",
    path: "/api/DowntimeEvents/export-excel/",
    alias: "api_DowntimeEvents_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Employees-Options/",
    alias: "api_Employees_Options_list",
    description: `Select list for employees (staff users).`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedUserSelectList,
  },
  {
    method: "get",
    path: "/api/Employees-Options/:id/",
    alias: "api_Employees_Options_retrieve",
    description: `Select list for employees (staff users).`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserSelect,
  },
  {
    method: "get",
    path: "/api/Equipment-Options/",
    alias: "api_Equipment_Options_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedEquipmentsList,
  },
  {
    method: "get",
    path: "/api/Equipment-Options/:id/",
    alias: "api_Equipment_Options_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Equipments,
  },
  {
    method: "get",
    path: "/api/Equipment-types/",
    alias: "api_Equipment_types_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedEquipmentTypeList,
  },
  {
    method: "post",
    path: "/api/Equipment-types/",
    alias: "api_Equipment_types_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: EquipmentTypeRequest,
      },
    ],
    response: EquipmentType,
  },
  {
    method: "get",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "put",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: EquipmentTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "patch",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedEquipmentTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "delete",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Equipment-types/export-excel/",
    alias: "api_Equipment_types_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Equipment-types/metadata/",
    alias: "api_Equipment_types_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Equipment/",
    alias: "api_Equipment_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "equipment_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "location",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum([
            "in_calibration",
            "in_maintenance",
            "in_service",
            "out_of_service",
            "retired",
          ])
          .optional(),
      },
    ],
    response: PaginatedEquipmentsList,
  },
  {
    method: "post",
    path: "/api/Equipment/",
    alias: "api_Equipment_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: EquipmentsRequest,
      },
    ],
    response: Equipments,
  },
  {
    method: "get",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Equipments,
  },
  {
    method: "put",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: EquipmentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Equipments,
  },
  {
    method: "patch",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedEquipmentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Equipments,
  },
  {
    method: "delete",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Equipment/export-excel/",
    alias: "api_Equipment_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Equipment/metadata/",
    alias: "api_Equipment_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Error-types/",
    alias: "api_Error_types_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "error_name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedQualityErrorsListList,
  },
  {
    method: "post",
    path: "/api/Error-types/",
    alias: "api_Error_types_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QualityErrorsListRequest,
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "get",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "put",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QualityErrorsListRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "patch",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedQualityErrorsListRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "delete",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Error-types/export-excel/",
    alias: "api_Error_types_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Error-types/metadata/",
    alias: "api_Error_types_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/ErrorReports/",
    alias: "api_ErrorReports_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "machine",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "part__work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.enum(["FAIL", "PASS", "PENDING"]).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedQualityReportsList,
  },
  {
    method: "post",
    path: "/api/ErrorReports/",
    alias: "api_ErrorReports_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QualityReportsRequest,
      },
    ],
    response: QualityReports,
  },
  {
    method: "get",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "put",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QualityReportsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "patch",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedQualityReportsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "delete",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/ErrorReports/export-excel/",
    alias: "api_ErrorReports_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/ErrorReports/metadata/",
    alias: "api_ErrorReports_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Fishbone/",
    alias: "api_Fishbone_list",
    description: `List Fishbone diagrams with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "rca_record",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedFishboneList,
  },
  {
    method: "post",
    path: "/api/Fishbone/",
    alias: "api_Fishbone_create",
    description: `Create a new Fishbone diagram`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: FishboneRequest,
      },
    ],
    response: Fishbone,
  },
  {
    method: "get",
    path: "/api/Fishbone/:id/",
    alias: "api_Fishbone_retrieve",
    description: `Retrieve a specific Fishbone diagram`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Fishbone,
  },
  {
    method: "put",
    path: "/api/Fishbone/:id/",
    alias: "api_Fishbone_update",
    description: `Update a Fishbone diagram`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: FishboneRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Fishbone,
  },
  {
    method: "patch",
    path: "/api/Fishbone/:id/",
    alias: "api_Fishbone_partial_update",
    description: `Partially update a Fishbone diagram`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedFishboneRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Fishbone,
  },
  {
    method: "delete",
    path: "/api/Fishbone/:id/",
    alias: "api_Fishbone_destroy",
    description: `Delete a Fishbone diagram`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Fishbone/export-excel/",
    alias: "api_Fishbone_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Fishbone/metadata/",
    alias: "api_Fishbone_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/FiveWhys/",
    alias: "api_FiveWhys_list",
    description: `List 5 Whys analyses with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "rca_record",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedFiveWhysList,
  },
  {
    method: "post",
    path: "/api/FiveWhys/",
    alias: "api_FiveWhys_create",
    description: `Create a new 5 Whys analysis`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: FiveWhysRequest,
      },
    ],
    response: FiveWhys,
  },
  {
    method: "get",
    path: "/api/FiveWhys/:id/",
    alias: "api_FiveWhys_retrieve",
    description: `Retrieve a specific 5 Whys analysis`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: FiveWhys,
  },
  {
    method: "put",
    path: "/api/FiveWhys/:id/",
    alias: "api_FiveWhys_update",
    description: `Update a 5 Whys analysis`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: FiveWhysRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: FiveWhys,
  },
  {
    method: "patch",
    path: "/api/FiveWhys/:id/",
    alias: "api_FiveWhys_partial_update",
    description: `Partially update a 5 Whys analysis`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedFiveWhysRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: FiveWhys,
  },
  {
    method: "delete",
    path: "/api/FiveWhys/:id/",
    alias: "api_FiveWhys_destroy",
    description: `Delete a 5 Whys analysis`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/FiveWhys/export-excel/",
    alias: "api_FiveWhys_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/FiveWhys/metadata/",
    alias: "api_FiveWhys_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Groups/",
    alias: "api_Groups_list",
    description: `ViewSet for Django Groups with user and permission management`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedGroupList,
  },
  {
    method: "post",
    path: "/api/Groups/",
    alias: "api_Groups_create",
    description: `ViewSet for Django Groups with user and permission management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ name: z.string().min(1).max(150) }).passthrough(),
      },
    ],
    response: Group,
  },
  {
    method: "get",
    path: "/api/Groups/:id/",
    alias: "api_Groups_retrieve",
    description: `ViewSet for Django Groups with user and permission management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Group,
  },
  {
    method: "patch",
    path: "/api/Groups/:id/",
    alias: "api_Groups_partial_update",
    description: `ViewSet for Django Groups with user and permission management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ name: z.string().min(1).max(150) })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Group,
  },
  {
    method: "delete",
    path: "/api/Groups/:id/",
    alias: "api_Groups_destroy",
    description: `ViewSet for Django Groups with user and permission management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Groups/:id/add-permissions/",
    alias: "api_Groups_add_permissions_create",
    description: `Add permissions to this group`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GroupAddPermissionsInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: GroupAddPermissionsResponse,
  },
  {
    method: "post",
    path: "/api/Groups/:id/add-users/",
    alias: "api_Groups_add_users_create",
    description: `Add users to this group`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GroupAddUsersInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: GroupAddUsersResponse,
  },
  {
    method: "post",
    path: "/api/Groups/:id/remove-permissions/",
    alias: "api_Groups_remove_permissions_create",
    description: `Remove permissions from this group`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GroupRemovePermissionsInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: GroupRemovePermissionsResponse,
  },
  {
    method: "post",
    path: "/api/Groups/:id/remove-users/",
    alias: "api_Groups_remove_users_create",
    description: `Remove users from this group`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GroupRemoveUsersInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: GroupRemoveUsersResponse,
  },
  {
    method: "post",
    path: "/api/Groups/:id/set-permissions/",
    alias: "api_Groups_set_permissions_create",
    description: `Replace all permissions on this group with the provided list`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GroupSetPermissionsInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: GroupSetPermissionsResponse,
  },
  {
    method: "get",
    path: "/api/Groups/available-permissions/",
    alias: "api_Groups_available_permissions_list",
    description: `Get all available permissions that can be assigned to groups`,
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(AvailablePermissionResponse),
  },
  {
    method: "get",
    path: "/api/Groups/available-users/",
    alias: "api_Groups_available_users_list",
    description: `Get all users available to add to groups`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedAvailableUserResponseList,
  },
  {
    method: "get",
    path: "/api/HarvestedComponents/",
    alias: "api_HarvestedComponents_list",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "component_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "condition_grade",
        type: "Query",
        schema: z.enum(["A", "B", "C", "SCRAP"]).optional(),
      },
      {
        name: "core",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "is_scrapped",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedHarvestedComponentList,
  },
  {
    method: "post",
    path: "/api/HarvestedComponents/",
    alias: "api_HarvestedComponents_create",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HarvestedComponentRequest,
      },
    ],
    response: HarvestedComponent,
  },
  {
    method: "get",
    path: "/api/HarvestedComponents/:id/",
    alias: "api_HarvestedComponents_retrieve",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HarvestedComponent,
  },
  {
    method: "put",
    path: "/api/HarvestedComponents/:id/",
    alias: "api_HarvestedComponents_update",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HarvestedComponentRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HarvestedComponent,
  },
  {
    method: "patch",
    path: "/api/HarvestedComponents/:id/",
    alias: "api_HarvestedComponents_partial_update",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedHarvestedComponentRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HarvestedComponent,
  },
  {
    method: "delete",
    path: "/api/HarvestedComponents/:id/",
    alias: "api_HarvestedComponents_destroy",
    description: `Harvested component management.

Components are created during core disassembly, then either:
- accept_to_inventory -&gt; Creates a Parts record for reuse
- scrap -&gt; Marks as scrapped`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/HarvestedComponents/:id/accept_to_inventory/",
    alias: "api_HarvestedComponents_accept_to_inventory_create",
    description: `Accept a harvested component into inventory as a Part`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ erp_id: z.string().nullable() })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: AcceptToInventoryResponse,
  },
  {
    method: "post",
    path: "/api/HarvestedComponents/:id/scrap/",
    alias: "api_HarvestedComponents_scrap_create",
    description: `Scrap a harvested component`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ reason: z.string().default("") })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HarvestedComponent,
  },
  {
    method: "get",
    path: "/api/HarvestedComponents/export-excel/",
    alias: "api_HarvestedComponents_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/HeatMapAnnotation/",
    alias: "api_HeatMapAnnotation_list",
    description: `List heatmap annotations with filtering and search capabilities`,
    requestFormat: "json",
    parameters: [
      {
        name: "created_at",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "defect_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "defect_type__icontains",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "measurement_value",
        type: "Query",
        schema: z.number().optional(),
      },
      {
        name: "measurement_value__gte",
        type: "Query",
        schema: z.number().optional(),
      },
      {
        name: "measurement_value__lte",
        type: "Query",
        schema: z.number().optional(),
      },
      {
        name: "model",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "model__file_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part__work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "severity",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "updated_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "updated_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
    ],
    response: PaginatedHeatMapAnnotationsList,
  },
  {
    method: "post",
    path: "/api/HeatMapAnnotation/",
    alias: "api_HeatMapAnnotation_create",
    description: `Create a new heatmap annotation on a 3D model`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HeatMapAnnotationsRequest,
      },
    ],
    response: HeatMapAnnotations,
  },
  {
    method: "get",
    path: "/api/HeatMapAnnotation/:id/",
    alias: "api_HeatMapAnnotation_retrieve",
    description: `Retrieve a specific heatmap annotation`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HeatMapAnnotations,
  },
  {
    method: "put",
    path: "/api/HeatMapAnnotation/:id/",
    alias: "api_HeatMapAnnotation_update",
    description: `Update a heatmap annotation`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HeatMapAnnotationsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HeatMapAnnotations,
  },
  {
    method: "patch",
    path: "/api/HeatMapAnnotation/:id/",
    alias: "api_HeatMapAnnotation_partial_update",
    description: `Partially update a heatmap annotation`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedHeatMapAnnotationsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: HeatMapAnnotations,
  },
  {
    method: "delete",
    path: "/api/HeatMapAnnotation/:id/",
    alias: "api_HeatMapAnnotation_destroy",
    description: `Soft delete a heatmap annotation`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/HeatMapAnnotation/export-excel/",
    alias: "api_HeatMapAnnotation_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/HeatMapAnnotation/facets/",
    alias: "api_HeatMapAnnotation_facets_retrieve",
    description: `Returns aggregated facet counts for defect_type and severity.
Accepts the same filter parameters as the list endpoint for efficient filtering.`,
    requestFormat: "json",
    parameters: [
      {
        name: "created_at__gte",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "created_at__lte",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "model",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part__work_order",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: HeatMapFacetsResponse,
  },
  {
    method: "get",
    path: "/api/HeatMapAnnotation/metadata/",
    alias: "api_HeatMapAnnotation_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/HubspotGates/",
    alias: "api_HubspotGates_list",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(ExternalAPIOrderIdentifier),
  },
  {
    method: "post",
    path: "/api/HubspotGates/",
    alias: "api_HubspotGates_create",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ExternalAPIOrderIdentifierRequest,
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "get",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_retrieve",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "put",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_update",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ExternalAPIOrderIdentifierRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "patch",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_partial_update",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedExternalAPIOrderIdentifierRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "delete",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_destroy",
    description: `ViewSet for managing HubSpot gate/milestone data`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/HubspotGates/export-excel/",
    alias: "api_HubspotGates_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/MaterialLots/",
    alias: "api_MaterialLots_list",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "material_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["consumed", "in_use", "quarantine", "received", "scrapped"])
          .optional(),
      },
      {
        name: "supplier",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedMaterialLotList,
  },
  {
    method: "post",
    path: "/api/MaterialLots/",
    alias: "api_MaterialLots_create",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: MaterialLotRequest,
      },
    ],
    response: MaterialLot,
  },
  {
    method: "get",
    path: "/api/MaterialLots/:id/",
    alias: "api_MaterialLots_retrieve",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MaterialLot,
  },
  {
    method: "put",
    path: "/api/MaterialLots/:id/",
    alias: "api_MaterialLots_update",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: MaterialLotRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MaterialLot,
  },
  {
    method: "patch",
    path: "/api/MaterialLots/:id/",
    alias: "api_MaterialLots_partial_update",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedMaterialLotRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MaterialLot,
  },
  {
    method: "delete",
    path: "/api/MaterialLots/:id/",
    alias: "api_MaterialLots_destroy",
    description: `Material lot tracking with split capability`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/MaterialLots/:id/split/",
    alias: "api_MaterialLots_split_create",
    description: `Split a lot into a child lot`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: MaterialLotSplitRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MaterialLot,
  },
  {
    method: "get",
    path: "/api/MaterialLots/export-excel/",
    alias: "api_MaterialLots_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/MaterialUsages/",
    alias: "api_MaterialUsages_list",
    description: `Material consumption records (read-only, created via lot consumption)`,
    requestFormat: "json",
    parameters: [
      {
        name: "is_substitute",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "lot",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedMaterialUsageList,
  },
  {
    method: "get",
    path: "/api/MaterialUsages/:id/",
    alias: "api_MaterialUsages_retrieve",
    description: `Material consumption records (read-only, created via lot consumption)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MaterialUsage,
  },
  {
    method: "get",
    path: "/api/MeasurementDefinitions/",
    alias: "api_MeasurementDefinitions_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "label",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__name",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedMeasurementDefinitionList,
  },
  {
    method: "post",
    path: "/api/MeasurementDefinitions/",
    alias: "api_MeasurementDefinitions_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: MeasurementDefinitionRequest,
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "get",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "put",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: MeasurementDefinitionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "patch",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedMeasurementDefinitionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "delete",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/MeasurementDefinitions/export-excel/",
    alias: "api_MeasurementDefinitions_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/MeasurementDefinitions/metadata/",
    alias: "api_MeasurementDefinitions_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/NotificationPreferences/",
    alias: "api_NotificationPreferences_list",
    description: `List user&#x27;s notification preferences`,
    requestFormat: "json",
    parameters: [
      {
        name: "channel_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "notification_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedNotificationPreferenceList,
  },
  {
    method: "post",
    path: "/api/NotificationPreferences/",
    alias: "api_NotificationPreferences_create",
    description: `Create a new notification preference for the current user`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: NotificationPreferenceRequest,
      },
    ],
    response: NotificationPreference,
  },
  {
    method: "get",
    path: "/api/NotificationPreferences/:id/",
    alias: "api_NotificationPreferences_retrieve",
    description: `Retrieve a specific notification preference`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: NotificationPreference,
  },
  {
    method: "put",
    path: "/api/NotificationPreferences/:id/",
    alias: "api_NotificationPreferences_update",
    description: `Update a notification preference`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: NotificationPreferenceRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: NotificationPreference,
  },
  {
    method: "patch",
    path: "/api/NotificationPreferences/:id/",
    alias: "api_NotificationPreferences_partial_update",
    description: `Partially update a notification preference`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedNotificationPreferenceRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: NotificationPreference,
  },
  {
    method: "delete",
    path: "/api/NotificationPreferences/:id/",
    alias: "api_NotificationPreferences_destroy",
    description: `Delete a notification preference`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/NotificationPreferences/:id/test-send/",
    alias: "api_NotificationPreferences_test_send_create",
    description: `Test send a notification immediately (for testing purposes)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: TestSendResponse,
  },
  {
    method: "get",
    path: "/api/NotificationPreferences/available-types/",
    alias: "api_NotificationPreferences_available_types_retrieve",
    description: `Get available notification types that users can configure`,
    requestFormat: "json",
    response: AvailableNotificationTypes,
  },
  {
    method: "get",
    path: "/api/Orders/",
    alias: "api_Orders_list",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "active_pipeline",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "archived",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "company",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "created_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "customer",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "estimated_completion__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "estimated_completion__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedOrdersList,
  },
  {
    method: "post",
    path: "/api/Orders/",
    alias: "api_Orders_create",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: OrdersRequest,
      },
    ],
    response: Orders,
  },
  {
    method: "get",
    path: "/api/Orders/:id/",
    alias: "api_Orders_retrieve",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Orders,
  },
  {
    method: "put",
    path: "/api/Orders/:id/",
    alias: "api_Orders_update",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: OrdersRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Orders,
  },
  {
    method: "patch",
    path: "/api/Orders/:id/",
    alias: "api_Orders_partial_update",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedOrdersRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Orders,
  },
  {
    method: "delete",
    path: "/api/Orders/:id/",
    alias: "api_Orders_destroy",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Orders/:id/add-note/",
    alias: "api_Orders_add_note_create",
    description: `Add a note to the order timeline.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AddNoteInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Orders,
  },
  {
    method: "post",
    path: "/api/Orders/:id/increment-step/",
    alias: "api_Orders_increment_step_create",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ step_id: z.string().uuid() }).passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: StepIncrementResponse,
  },
  {
    method: "post",
    path: "/api/Orders/:id/parts/bulk-add/",
    alias: "api_Orders_parts_bulk_add_create",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BulkAddPartsInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/Orders/:id/parts/bulk-remove/",
    alias: "api_Orders_parts_bulk_remove_create",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BulkRemovePartsInputRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/Orders/:id/step-distribution/",
    alias: "api_Orders_step_distribution_list",
    description: `Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "active_pipeline",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedStepDistributionResponseList,
  },
  {
    method: "get",
    path: "/api/orders/:order_id/parts/",
    alias: "api_orders_parts_list",
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "order_id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedPartsList,
  },
  {
    method: "get",
    path: "/api/Orders/export/",
    alias: "api_Orders_export_retrieve",
    description: `Export filtered data to CSV or Excel format.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/Orders/import-preview/",
    alias: "api_Orders_import_preview_create",
    description: `Preview a file before importing. Returns columns, suggested mappings, and sample data.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
    ],
    response: ImportPreviewResponse,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/Orders/import-status/:task_id/",
    alias: "api_Orders_import_status_retrieve",
    description: `Check status of a background import task.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ImportStatusResponse,
  },
  {
    method: "get",
    path: "/api/Orders/import-template/",
    alias: "api_Orders_import_template_retrieve",
    description: `Download an import template with headers, hints, and FK lookups (Excel only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/Orders/import/",
    alias: "api_Orders_import_create",
    description: `Import data from CSV or Excel file. Small imports return immediate results (207). Large imports are queued and return task_id (202).`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: api_Orders_import_create_Body,
      },
    ],
    response: ImportQueued,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/Orders/metadata/",
    alias: "api_Orders_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Parts/",
    alias: "api_Parts_list",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "ERP_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "archived",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "created_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "requires_sampling",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedPartsList,
  },
  {
    method: "post",
    path: "/api/Parts/",
    alias: "api_Parts_create",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PartsRequest,
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: Parts,
  },
  {
    method: "get",
    path: "/api/Parts/:id/",
    alias: "api_Parts_retrieve",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: Parts,
  },
  {
    method: "put",
    path: "/api/Parts/:id/",
    alias: "api_Parts_update",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PartsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: Parts,
  },
  {
    method: "patch",
    path: "/api/Parts/:id/",
    alias: "api_Parts_partial_update",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedPartsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: Parts,
  },
  {
    method: "delete",
    path: "/api/Parts/:id/",
    alias: "api_Parts_destroy",
    description: `Parts CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Parts/:id/increment/",
    alias: "api_Parts_increment_create",
    description: `Advance part to next step.

For decision point steps, provide the decision parameter:
- qa_result decisions: &#x27;pass&#x27; or &#x27;fail&#x27;
- manual decisions: &#x27;default&#x27; or &#x27;alternate&#x27;
- measurement decisions: the measurement value (will be compared to threshold)

If no decision is provided for qa_result decisions, the latest QualityReport status is used.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ decision: z.string().min(1) })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/Parts/:id/traveler/",
    alias: "api_Parts_traveler_retrieve",
    description: `Get full traveler history for a part showing what happened at each step`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: PartTravelerResponse,
  },
  {
    method: "get",
    path: "/api/Parts/export/",
    alias: "api_Parts_export_retrieve",
    description: `Export filtered data to CSV or Excel format.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/Parts/import-preview/",
    alias: "api_Parts_import_preview_create",
    description: `Preview a file before importing. Returns columns, suggested mappings, and sample data.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: ImportPreviewResponse,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/Parts/import-status/:task_id/",
    alias: "api_Parts_import_status_retrieve",
    description: `Check status of a background import task.`,
    requestFormat: "json",
    parameters: [
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ImportStatusResponse,
  },
  {
    method: "get",
    path: "/api/Parts/import-template/",
    alias: "api_Parts_import_template_retrieve",
    description: `Download an import template with headers, hints, and FK lookups (Excel only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/Parts/import/",
    alias: "api_Parts_import_create",
    description: `Import data from CSV or Excel file. Small imports return immediate results (207). Large imports are queued and return task_id (202).`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: api_Orders_import_create_Body,
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: ImportQueued,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/Parts/metadata/",
    alias: "api_Parts_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    parameters: [
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Parts/select/",
    alias: "api_Parts_select_list",
    description: `Lightweight endpoint for dropdown/combobox selections`,
    requestFormat: "json",
    parameters: [
      {
        name: "ERP_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "archived",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "created_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "created_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "requires_sampling",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedPartSelectList,
  },
  {
    method: "get",
    path: "/api/PartTypes/",
    alias: "api_PartTypes_list",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedPartTypesList,
  },
  {
    method: "post",
    path: "/api/PartTypes/",
    alias: "api_PartTypes_create",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PartTypesRequest,
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "get",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_retrieve",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "put",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_update",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PartTypesRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "patch",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_partial_update",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedPartTypesRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "delete",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_destroy",
    description: `Part Types CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/PartTypes/export/",
    alias: "api_PartTypes_export_retrieve",
    description: `Export filtered data to CSV or Excel format.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/PartTypes/import-preview/",
    alias: "api_PartTypes_import_preview_create",
    description: `Preview a file before importing. Returns columns, suggested mappings, and sample data.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: ImportPreviewResponse,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/PartTypes/import-status/:task_id/",
    alias: "api_PartTypes_import_status_retrieve",
    description: `Check status of a background import task.`,
    requestFormat: "json",
    parameters: [
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ImportStatusResponse,
  },
  {
    method: "get",
    path: "/api/PartTypes/import-template/",
    alias: "api_PartTypes_import_template_retrieve",
    description: `Download an import template with headers, hints, and FK lookups (Excel only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/PartTypes/import/",
    alias: "api_PartTypes_import_create",
    description: `Import data from CSV or Excel file. Small imports return immediate results (207). Large imports are queued and return task_id (202).`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: api_Orders_import_create_Body,
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: ImportQueued,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/PartTypes/metadata/",
    alias: "api_PartTypes_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    parameters: [
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/PartTypes/select/",
    alias: "api_PartTypes_select_list",
    description: `Lightweight endpoint for dropdown/combobox selections`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedPartTypeSelectList,
  },
  {
    method: "get",
    path: "/api/permissions/",
    alias: "api_permissions_retrieve",
    description: `List all available permissions, optionally grouped by category.

Used by frontend permission picker UI.`,
    requestFormat: "json",
    parameters: [
      {
        name: "grouped",
        type: "Query",
        schema: z.boolean().optional(),
      },
    ],
    response: PermissionListResponse,
  },
  {
    method: "get",
    path: "/api/presets/",
    alias: "api_presets_retrieve",
    description: `List available group presets.`,
    requestFormat: "json",
    response: PresetListResponse,
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/",
    alias: "api_Processes_with_steps_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["approved", "deprecated", "draft", "pending_approval"])
          .optional(),
      },
    ],
    response: PaginatedProcessWithStepsList,
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/",
    alias: "api_Processes_with_steps_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProcessWithStepsRequest,
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "put",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProcessWithStepsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "patch",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedProcessWithStepsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "delete",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/:id/approve/",
    alias: "api_Processes_with_steps_approve_create",
    description: `Directly approve a draft process for production use (bypasses formal approval workflow). Once approved, the process cannot be modified.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/:id/deprecate/",
    alias: "api_Processes_with_steps_deprecate_create",
    description: `Mark an approved process as deprecated. It can still be used by existing work orders but won&#x27;t appear for new ones.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/:id/duplicate/",
    alias: "api_Processes_with_steps_duplicate_create",
    description: `Create a copy of this process for customization. The copy starts as DRAFT.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ name_suffix: z.string().min(1).default(" (Copy)") })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/:id/submit_for_approval/",
    alias: "api_Processes_with_steps_submit_for_approval_create",
    description: `Submit a draft process for formal approval workflow. Creates an ApprovalRequest that must be approved before the process can be used.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ reason: z.string().min(1) })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SubmitProcessForApprovalResponse,
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/available/",
    alias: "api_Processes_with_steps_available_list",
    description: `List all approved processes available for work orders`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["approved", "deprecated", "draft", "pending_approval"])
          .optional(),
      },
    ],
    response: PaginatedProcessWithStepsList,
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/export-excel/",
    alias: "api_Processes_with_steps_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Processes/",
    alias: "api_Processes_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["approved", "deprecated", "draft", "pending_approval"])
          .optional(),
      },
    ],
    response: PaginatedProcessesList,
  },
  {
    method: "post",
    path: "/api/Processes/",
    alias: "api_Processes_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProcessesRequest,
      },
    ],
    response: Processes,
  },
  {
    method: "get",
    path: "/api/Processes/:id/",
    alias: "api_Processes_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Processes,
  },
  {
    method: "put",
    path: "/api/Processes/:id/",
    alias: "api_Processes_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProcessesRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Processes,
  },
  {
    method: "patch",
    path: "/api/Processes/:id/",
    alias: "api_Processes_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedProcessesRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Processes,
  },
  {
    method: "delete",
    path: "/api/Processes/:id/",
    alias: "api_Processes_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Processes/export-excel/",
    alias: "api_Processes_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Processes/metadata/",
    alias: "api_Processes_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/QuarantineDispositions/",
    alias: "api_QuarantineDispositions_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "current_state",
        type: "Query",
        schema: z.enum(["CLOSED", "IN_PROGRESS", "OPEN"]).optional(),
      },
      {
        name: "disposition_number",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "disposition_type",
        type: "Query",
        schema: z
          .enum([
            "REPAIR",
            "RETURN_TO_SUPPLIER",
            "REWORK",
            "SCRAP",
            "USE_AS_IS",
          ])
          .optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "part__ERP_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part__part_type__name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "resolution_completed",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "resolution_completed_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedQuarantineDispositionList,
  },
  {
    method: "post",
    path: "/api/QuarantineDispositions/",
    alias: "api_QuarantineDispositions_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QuarantineDispositionRequest,
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "get",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "put",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: QuarantineDispositionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "patch",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedQuarantineDispositionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "delete",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/QuarantineDispositions/export-excel/",
    alias: "api_QuarantineDispositions_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/QuarantineDispositions/metadata/",
    alias: "api_QuarantineDispositions_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/RcaRecords/",
    alias: "api_RcaRecords_list",
    description: `List RCA records with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "capa",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "conducted_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "rca_method",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "rca_review_status",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "root_cause_verified_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedRcaRecordList,
  },
  {
    method: "post",
    path: "/api/RcaRecords/",
    alias: "api_RcaRecords_create",
    description: `Create a new RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RcaRecordRequest,
      },
    ],
    response: RcaRecord,
  },
  {
    method: "get",
    path: "/api/RcaRecords/:id/",
    alias: "api_RcaRecords_retrieve",
    description: `Retrieve a specific RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RcaRecord,
  },
  {
    method: "put",
    path: "/api/RcaRecords/:id/",
    alias: "api_RcaRecords_update",
    description: `Update an RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RcaRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RcaRecord,
  },
  {
    method: "patch",
    path: "/api/RcaRecords/:id/",
    alias: "api_RcaRecords_partial_update",
    description: `Partially update an RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedRcaRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RcaRecord,
  },
  {
    method: "delete",
    path: "/api/RcaRecords/:id/",
    alias: "api_RcaRecords_destroy",
    description: `Soft delete an RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/RcaRecords/:id/approve/",
    alias: "api_RcaRecords_approve_create",
    description: `Approve RCA record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RcaRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RcaRecord,
  },
  {
    method: "post",
    path: "/api/RcaRecords/:id/submit-for-review/",
    alias: "api_RcaRecords_submit_for_review_create",
    description: `Submit RCA for review`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RcaRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RcaRecord,
  },
  {
    method: "get",
    path: "/api/RcaRecords/export-excel/",
    alias: "api_RcaRecords_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/RcaRecords/metadata/",
    alias: "api_RcaRecords_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "post",
    path: "/api/reports/download/",
    alias: "api_reports_download_create",
    description: `Generate and download a PDF report directly (synchronous).

This endpoint generates the PDF and returns it immediately for download,
rather than emailing it. Use for on-device saves.

Request body:
{
    &quot;report_type&quot;: &quot;spc&quot;,
    &quot;params&quot;: {
        &quot;processId&quot;: 1,
        &quot;stepId&quot;: 101,
        &quot;measurementId&quot;: 1001,
        &quot;mode&quot;: &quot;xbar-r&quot;
    }
}

Returns: PDF file as binary response`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GenerateReportRequest,
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/reports/generate/",
    alias: "api_reports_generate_create",
    description: `Generate and email a PDF report.

Request body:
{
    &quot;report_type&quot;: &quot;spc&quot;,
    &quot;params&quot;: {
        &quot;process_id&quot;: 1,
        &quot;step_id&quot;: 101,
        &quot;measurement_id&quot;: 1001,
        &quot;mode&quot;: &quot;xbar-r&quot;
    }
}

Response:
{
    &quot;message&quot;: &quot;Report is being generated. You&#x27;ll receive an email shortly.&quot;,
    &quot;report_id&quot;: 123
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: GenerateReportRequest,
      },
    ],
    response: GenerateReportResponse,
  },
  {
    method: "get",
    path: "/api/reports/history/",
    alias: "api_reports_history_list",
    description: `List the current user&#x27;s generated reports.

Query params:
    report_type: Filter by report type (optional)
    status: Filter by status (optional)
    limit: Number of results (default 50)`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedGeneratedReportList,
  },
  {
    method: "get",
    path: "/api/reports/types/",
    alias: "api_reports_types_retrieve",
    description: `List available report types with their configurations.

Response:
{
    &quot;spc&quot;: {&quot;title&quot;: &quot;SPC Report&quot;, &quot;route&quot;: &quot;/spc/print&quot;},
    &quot;capa&quot;: {&quot;title&quot;: &quot;CAPA Report&quot;, &quot;route&quot;: &quot;/quality/capas/{id}/print&quot;},
    ...
}`,
    requestFormat: "json",
    response: ReportTypesResponse,
  },
  {
    method: "get",
    path: "/api/Sampling-rule-sets/",
    alias: "api_Sampling_rule_sets_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "active",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "version",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedSamplingRuleSetList,
  },
  {
    method: "post",
    path: "/api/Sampling-rule-sets/",
    alias: "api_Sampling_rule_sets_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SamplingRuleSetRequest,
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "get",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "put",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SamplingRuleSetRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "patch",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedSamplingRuleSetRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "delete",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Sampling-rule-sets/export-excel/",
    alias: "api_Sampling_rule_sets_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Sampling-rule-sets/metadata/",
    alias: "api_Sampling_rule_sets_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/Sampling-rules/",
    alias: "api_Sampling_rules_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "rule_type",
        type: "Query",
        schema: z
          .enum([
            "every_nth_part",
            "exact_count",
            "first_n_parts",
            "last_n_parts",
            "percentage",
            "random",
          ])
          .optional(),
      },
      {
        name: "ruleset",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedSamplingRuleList,
  },
  {
    method: "post",
    path: "/api/Sampling-rules/",
    alias: "api_Sampling_rules_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SamplingRuleRequest,
      },
    ],
    response: SamplingRule,
  },
  {
    method: "get",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "put",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SamplingRuleRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "patch",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedSamplingRuleRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "delete",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Sampling-rules/export-excel/",
    alias: "api_Sampling_rules_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Sampling-rules/metadata/",
    alias: "api_Sampling_rules_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/ScheduleSlots/",
    alias: "api_ScheduleSlots_list",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "scheduled_date",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "shift",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["cancelled", "completed", "in_progress", "scheduled"])
          .optional(),
      },
      {
        name: "work_center",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedScheduleSlotList,
  },
  {
    method: "post",
    path: "/api/ScheduleSlots/",
    alias: "api_ScheduleSlots_create",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ScheduleSlotRequest,
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "get",
    path: "/api/ScheduleSlots/:id/",
    alias: "api_ScheduleSlots_retrieve",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "put",
    path: "/api/ScheduleSlots/:id/",
    alias: "api_ScheduleSlots_update",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ScheduleSlotRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "patch",
    path: "/api/ScheduleSlots/:id/",
    alias: "api_ScheduleSlots_partial_update",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedScheduleSlotRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "delete",
    path: "/api/ScheduleSlots/:id/",
    alias: "api_ScheduleSlots_destroy",
    description: `Production schedule management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/ScheduleSlots/:id/complete/",
    alias: "api_ScheduleSlots_complete_create",
    description: `Mark schedule slot as completed`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "post",
    path: "/api/ScheduleSlots/:id/start/",
    alias: "api_ScheduleSlots_start_create",
    description: `Mark schedule slot as started`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ScheduleSlot,
  },
  {
    method: "get",
    path: "/api/schema/",
    alias: "api_schema_retrieve",
    description: `OpenApi3 schema for this API. Format can be selected via content negotiation.

- YAML: application/vnd.oai.openapi
- JSON: application/vnd.oai.openapi+json`,
    requestFormat: "json",
    parameters: [
      {
        name: "format",
        type: "Query",
        schema: z.enum(["json", "yaml"]).optional(),
      },
      {
        name: "lang",
        type: "Query",
        schema: z
          .enum([
            "af",
            "ar",
            "ar-dz",
            "ast",
            "az",
            "be",
            "bg",
            "bn",
            "br",
            "bs",
            "ca",
            "ckb",
            "cs",
            "cy",
            "da",
            "de",
            "dsb",
            "el",
            "en",
            "en-au",
            "en-gb",
            "eo",
            "es",
            "es-ar",
            "es-co",
            "es-mx",
            "es-ni",
            "es-ve",
            "et",
            "eu",
            "fa",
            "fi",
            "fr",
            "fy",
            "ga",
            "gd",
            "gl",
            "he",
            "hi",
            "hr",
            "hsb",
            "hu",
            "hy",
            "ia",
            "id",
            "ig",
            "io",
            "is",
            "it",
            "ja",
            "ka",
            "kab",
            "kk",
            "km",
            "kn",
            "ko",
            "ky",
            "lb",
            "lt",
            "lv",
            "mk",
            "ml",
            "mn",
            "mr",
            "ms",
            "my",
            "nb",
            "ne",
            "nl",
            "nn",
            "os",
            "pa",
            "pl",
            "pt",
            "pt-br",
            "ro",
            "ru",
            "sk",
            "sl",
            "sq",
            "sr",
            "sr-latn",
            "sv",
            "sw",
            "ta",
            "te",
            "tg",
            "th",
            "tk",
            "tr",
            "tt",
            "udm",
            "ug",
            "uk",
            "ur",
            "uz",
            "vi",
            "zh-hans",
            "zh-hant",
          ])
          .optional(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/scope/",
    alias: "api_scope_list",
    description: `Query related objects across the model graph from a root object.`,
    requestFormat: "json",
    parameters: [
      {
        name: "classification",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "direction",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "include",
        type: "Query",
        schema: z.string(),
      },
      {
        name: "root",
        type: "Query",
        schema: z.string(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Shifts/",
    alias: "api_Shifts_list",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "is_active",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedShiftList,
  },
  {
    method: "post",
    path: "/api/Shifts/",
    alias: "api_Shifts_create",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ShiftRequest,
      },
    ],
    response: Shift,
  },
  {
    method: "get",
    path: "/api/Shifts/:id/",
    alias: "api_Shifts_retrieve",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Shift,
  },
  {
    method: "put",
    path: "/api/Shifts/:id/",
    alias: "api_Shifts_update",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ShiftRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Shift,
  },
  {
    method: "patch",
    path: "/api/Shifts/:id/",
    alias: "api_Shifts_partial_update",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedShiftRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: Shift,
  },
  {
    method: "delete",
    path: "/api/Shifts/:id/",
    alias: "api_Shifts_destroy",
    description: `Shift definition management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/spc-baselines/",
    alias: "api_spc_baselines_list",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "chart_type",
        type: "Query",
        schema: z.enum(["I_MR", "XBAR_R", "XBAR_S"]).optional(),
      },
      {
        name: "frozen_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "measurement_definition",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.enum(["ACTIVE", "SUPERSEDED"]).optional(),
      },
    ],
    response: PaginatedSPCBaselineListList,
  },
  {
    method: "post",
    path: "/api/spc-baselines/",
    alias: "api_spc_baselines_create",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SPCBaselineRequest,
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "get",
    path: "/api/spc-baselines/:id/",
    alias: "api_spc_baselines_retrieve",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "put",
    path: "/api/spc-baselines/:id/",
    alias: "api_spc_baselines_update",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SPCBaselineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "patch",
    path: "/api/spc-baselines/:id/",
    alias: "api_spc_baselines_partial_update",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedSPCBaselineRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "delete",
    path: "/api/spc-baselines/:id/",
    alias: "api_spc_baselines_destroy",
    description: `ViewSet for SPC Baselines (frozen control limits).

Standard CRUD plus custom actions:
    POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
    POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
    GET /api/spc-baselines/active/?measurement_id&#x3D;X - Get active baseline`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/spc-baselines/:id/supersede/",
    alias: "api_spc_baselines_supersede_create",
    description: `Supersede (unfreeze) a baseline.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ reason: z.string() }).partial().passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "get",
    path: "/api/spc-baselines/active/",
    alias: "api_spc_baselines_active_retrieve",
    description: `Get active baseline for a measurement.`,
    requestFormat: "json",
    parameters: [
      {
        name: "measurement_id",
        type: "Query",
        schema: z.string(),
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "get",
    path: "/api/spc-baselines/export-excel/",
    alias: "api_spc_baselines_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/spc-baselines/freeze/",
    alias: "api_spc_baselines_freeze_create",
    description: `Freeze control limits as new baseline. Auto-supersedes existing active baseline.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SPCBaselineFreezeRequest,
      },
    ],
    response: SPCBaseline,
  },
  {
    method: "get",
    path: "/api/spc-baselines/metadata/",
    alias: "api_spc_baselines_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/spc/capability/",
    alias: "api_spc_capability_retrieve",
    description: `Calculate process capability metrics (Cp, Cpk, Pp, Ppk).

Query params:
    measurement_id (required): ID of the MeasurementDefinition
    days (optional): Number of days of data (default: 90)
    subgroup_size (optional): Size for subgroup calculations (default: 5)

Response:
{
    &quot;definition&quot;: { ... },
    &quot;sample_size&quot;: 150,
    &quot;usl&quot;: 25.1,
    &quot;lsl&quot;: 24.9,
    &quot;mean&quot;: 25.01,
    &quot;std_dev_within&quot;: 0.025,
    &quot;std_dev_overall&quot;: 0.030,
    &quot;cp&quot;: 1.33,
    &quot;cpk&quot;: 1.20,
    &quot;pp&quot;: 1.11,
    &quot;ppk&quot;: 1.00,
    &quot;interpretation&quot;: &quot;Process is capable but not centered&quot;
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(90),
      },
      {
        name: "measurement_id",
        type: "Query",
        schema: z.string(),
      },
      {
        name: "subgroup_size",
        type: "Query",
        schema: z.number().int().optional().default(5),
      },
    ],
    response: SPCCapabilityResponse,
  },
  {
    method: "get",
    path: "/api/spc/data/",
    alias: "api_spc_data_retrieve",
    description: `Get measurement data for SPC control charts.

Query params:
    measurement_id (required): ID of the MeasurementDefinition
    days (optional): Number of days of data to return (default: 90)
    limit (optional): Max number of data points (default: 500)

Response:
{
    &quot;definition&quot;: { ... measurement definition ... },
    &quot;process_name&quot;: &quot;CNC Machining&quot;,
    &quot;step_name&quot;: &quot;Rough Turning&quot;,
    &quot;data_points&quot;: [
        {
            &quot;id&quot;: &quot;019c4a7e-...&quot;,
            &quot;value&quot;: 25.02,
            &quot;timestamp&quot;: &quot;2025-01-15T10:30:00Z&quot;,
            &quot;report_id&quot;: &quot;019c4a8f-...&quot;,
            &quot;part_erp_id&quot;: &quot;PART-001&quot;,
            &quot;operator_name&quot;: &quot;John Smith&quot;,
            &quot;is_within_spec&quot;: true
        }
    ],
    &quot;statistics&quot;: {
        &quot;count&quot;: 150,
        &quot;mean&quot;: 25.01,
        &quot;std_dev&quot;: 0.03,
        &quot;min&quot;: 24.95,
        &quot;max&quot;: 25.08,
        &quot;within_spec_count&quot;: 148,
        &quot;out_of_spec_count&quot;: 2
    }
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(90),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(500),
      },
      {
        name: "measurement_id",
        type: "Query",
        schema: z.string(),
      },
    ],
    response: SPCDataResponse,
  },
  {
    method: "get",
    path: "/api/spc/dimensional-results/",
    alias: "api_spc_dimensional_results_retrieve",
    description: `Get all dimensional measurement results for a part or work order.

Useful for PPAP dimensional reports (Element 9).

Query params:
    part_id (optional): ID of a specific Part
    work_order_id (optional): ID of a WorkOrder (returns all parts&#x27; results)
    At least one must be provided.

Response:
{
    &quot;part&quot;: { &quot;id&quot;: 1, &quot;erp_id&quot;: &quot;PART-001&quot;, ... } or null,
    &quot;work_order&quot;: { &quot;id&quot;: 1, &quot;identifier&quot;: &quot;WO-001&quot;, ... } or null,
    &quot;results&quot;: [
        {
            &quot;part_erp_id&quot;: &quot;PART-001&quot;,
            &quot;step_name&quot;: &quot;Finish Turning&quot;,
            &quot;measurement_label&quot;: &quot;Outer Diameter&quot;,
            &quot;nominal&quot;: 25.0,
            &quot;upper_tol&quot;: 0.1,
            &quot;lower_tol&quot;: 0.1,
            &quot;usl&quot;: 25.1,
            &quot;lsl&quot;: 24.9,
            &quot;actual&quot;: 25.02,
            &quot;deviation&quot;: 0.02,
            &quot;unit&quot;: &quot;mm&quot;,
            &quot;is_within_spec&quot;: true,
            &quot;timestamp&quot;: &quot;2025-01-15T10:30:00Z&quot;,
            &quot;operator&quot;: &quot;John Smith&quot;
        }
    ],
    &quot;summary&quot;: {
        &quot;total_measurements&quot;: 50,
        &quot;within_spec&quot;: 48,
        &quot;out_of_spec&quot;: 2,
        &quot;pass_rate&quot;: 96.0
    }
}`,
    requestFormat: "json",
    parameters: [
      {
        name: "part_id",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "work_order_id",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: DimensionalResultsResponse,
  },
  {
    method: "get",
    path: "/api/spc/hierarchy/",
    alias: "api_spc_hierarchy_list",
    description: `Get the full process → step → measurement hierarchy.

Used to populate the SPC page dropdowns.
Only returns processes that have steps with numeric measurement definitions.

Response:
[
    {
        &quot;id&quot;: &quot;019c4a2b-...&quot;,
        &quot;name&quot;: &quot;CNC Machining&quot;,
        &quot;part_type_name&quot;: &quot;Valve Body&quot;,
        &quot;steps&quot;: [
            {
                &quot;id&quot;: &quot;019c4a3f-...&quot;,
                &quot;name&quot;: &quot;Rough Turning&quot;,
                &quot;order&quot;: 1,
                &quot;measurements&quot;: [
                    {
                        &quot;id&quot;: &quot;019c4a5d-...&quot;,
                        &quot;label&quot;: &quot;Outer Diameter&quot;,
                        &quot;type&quot;: &quot;NUMERIC&quot;,
                        &quot;unit&quot;: &quot;mm&quot;,
                        &quot;nominal&quot;: 25.0,
                        &quot;upper_tol&quot;: 0.1,
                        &quot;lower_tol&quot;: 0.1
                    }
                ]
            }
        ]
    }
]`,
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(ProcessSPC),
  },
  {
    method: "get",
    path: "/api/StepExecutions/",
    alias: "api_StepExecutions_list",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "assigned_to__isnull",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["completed", "in_progress", "pending", "skipped"])
          .optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "visit_number",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__gte",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__lte",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedStepExecutionListList,
  },
  {
    method: "post",
    path: "/api/StepExecutions/",
    alias: "api_StepExecutions_create",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: StepExecutionRequest,
      },
    ],
    response: StepExecution,
  },
  {
    method: "get",
    path: "/api/StepExecutions/:id/",
    alias: "api_StepExecutions_retrieve",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: StepExecution,
  },
  {
    method: "put",
    path: "/api/StepExecutions/:id/",
    alias: "api_StepExecutions_update",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: StepExecutionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: StepExecution,
  },
  {
    method: "patch",
    path: "/api/StepExecutions/:id/",
    alias: "api_StepExecutions_partial_update",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedStepExecutionRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: StepExecution,
  },
  {
    method: "delete",
    path: "/api/StepExecutions/:id/",
    alias: "api_StepExecutions_destroy",
    description: `ViewSet for step execution tracking (workflow engine).

Provides:
- CRUD for step executions
- WIP queries (work in progress)
- Operator workload tracking
- Step history for parts

Used by the workflow engine for tracking part progression through steps.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/StepExecutions/:id/claim/",
    alias: "api_StepExecutions_claim_create",
    description: `POST /step-executions/{id}/claim/

Operator claims a pending step execution.
Sets assigned_to to current user and status to in_progress.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: StepExecution,
  },
  {
    method: "get",
    path: "/api/StepExecutions/duration_stats/",
    alias: "api_StepExecutions_duration_stats_retrieve",
    description: `Get duration statistics for steps in a process`,
    requestFormat: "json",
    response: StepDurationStats,
  },
  {
    method: "get",
    path: "/api/StepExecutions/metadata/",
    alias: "api_StepExecutions_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/StepExecutions/my_workload/",
    alias: "api_StepExecutions_my_workload_list",
    description: `Get current operator&#x27;s assigned work`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "assigned_to__isnull",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["completed", "in_progress", "pending", "skipped"])
          .optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "visit_number",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__gte",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__lte",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedStepExecutionListList,
  },
  {
    method: "get",
    path: "/api/StepExecutions/part_step_history/",
    alias: "api_StepExecutions_part_step_history_list",
    description: `Get visit history for a part at a specific step`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "assigned_to__isnull",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["completed", "in_progress", "pending", "skipped"])
          .optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "visit_number",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__gte",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__lte",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedStepExecutionList,
  },
  {
    method: "get",
    path: "/api/StepExecutions/wip_at_step/",
    alias: "api_StepExecutions_wip_at_step_list",
    description: `Get all active WIP at a specific step`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "assigned_to__isnull",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["completed", "in_progress", "pending", "skipped"])
          .optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "visit_number",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__gte",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__lte",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedStepExecutionListList,
  },
  {
    method: "get",
    path: "/api/StepExecutions/wip_summary/",
    alias: "api_StepExecutions_wip_summary_list",
    description: `Get WIP summary grouped by step for a process`,
    requestFormat: "json",
    parameters: [
      {
        name: "assigned_to",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "assigned_to__isnull",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z
          .enum(["completed", "in_progress", "pending", "skipped"])
          .optional(),
      },
      {
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step__process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "visit_number",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__gte",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "visit_number__lte",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedWIPSummaryList,
  },
  {
    method: "get",
    path: "/api/Steps/",
    alias: "api_Steps_list",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process_memberships__process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "process_memberships__process__part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedStepsList,
  },
  {
    method: "post",
    path: "/api/Steps/",
    alias: "api_Steps_create",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: StepsRequest,
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "get",
    path: "/api/Steps/:id/",
    alias: "api_Steps_retrieve",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "put",
    path: "/api/Steps/:id/",
    alias: "api_Steps_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: StepsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "patch",
    path: "/api/Steps/:id/",
    alias: "api_Steps_partial_update",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedStepsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "delete",
    path: "/api/Steps/:id/",
    alias: "api_Steps_destroy",
    description: `Mixin that filters all querysets to the current tenant and applies user permissions.

This is the primary mixin for most ViewSets. It:
- Enforces tenant-scoped permissions (TenantModelPermissions)
- Filters queryset to current tenant
- Applies for_user() filtering (permission-based data scoping)
- Auto-assigns tenant on create
- Prevents cross-tenant access

Permission Enforcement:
- GET/HEAD/OPTIONS -&gt; view_{model} permission
- POST -&gt; add_{model} permission
- PUT/PATCH -&gt; change_{model} permission
- DELETE -&gt; delete_{model} permission

Superusers bypass both permission checks and tenant filtering.

Query parameters:
- include_archived&#x3D;true: Include soft-deleted records (default: false)
- tenant&#x3D;&lt;uuid&gt;: (superuser only) Filter to specific tenant

Usage:
    class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset &#x3D; Order.objects.all()
        serializer_class &#x3D; OrderSerializer`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Steps/:id/resolved_rules/",
    alias: "api_Steps_resolved_rules_retrieve",
    description: `GET /steps/:id/resolved_rules/
Returns the active + fallback rulesets for a given step`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "post",
    path: "/api/Steps/:id/update_sampling_rules/",
    alias: "api_Steps_update_sampling_rules_create",
    description: `Update or create a sampling rule set for this step`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: StepSamplingRulesUpdateRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "get",
    path: "/api/Steps/export-excel/",
    alias: "api_Steps_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Steps/metadata/",
    alias: "api_Steps_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    parameters: [
      {
        name: "part_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/tenant/current/",
    alias: "api_tenant_current_retrieve",
    description: `Get current tenant information and deployment mode.

This endpoint is used by the frontend to:
- Determine which UI elements to show based on deployment mode
- Get tenant branding (logo, colors)
- Check feature flags and limits
- Display tenant name in header

Authentication is optional - unauthenticated requests get deployment info only.`,
    requestFormat: "json",
    response: CurrentTenantResponse,
  },
  {
    method: "post",
    path: "/api/tenant/logo/",
    alias: "api_tenant_logo_create",
    description: `Upload or delete tenant logo.

POST: Upload a new logo (multipart/form-data with &#x27;logo&#x27; file field)
DELETE: Remove the current logo`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ logo: z.instanceof(File) })
          .partial()
          .passthrough(),
      },
    ],
    response: z.object({ logo_url: z.string().nullable() }).passthrough(),
  },
  {
    method: "delete",
    path: "/api/tenant/logo/",
    alias: "api_tenant_logo_destroy",
    description: `Upload or delete tenant logo.

POST: Upload a new logo (multipart/form-data with &#x27;logo&#x27; file field)
DELETE: Remove the current logo`,
    requestFormat: "json",
    response: z.object({ logo_url: z.string().nullable() }).passthrough(),
  },
  {
    method: "get",
    path: "/api/tenant/settings/",
    alias: "api_tenant_settings_retrieve",
    description: `Get or update tenant settings.

Only accessible by tenant admins (users in Admin group).`,
    requestFormat: "json",
    response: TenantSettingsResponse,
  },
  {
    method: "patch",
    path: "/api/tenant/settings/",
    alias: "api_tenant_settings_partial_update",
    description: `Get or update tenant settings.

Only accessible by tenant admins (users in Admin group).`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTenantSettingsUpdateRequestRequest,
      },
    ],
    response: TenantSettingsUpdateResponse,
  },
  {
    method: "get",
    path: "/api/TenantGroups/",
    alias: "api_TenantGroups_list",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedTenantGroupList,
  },
  {
    method: "post",
    path: "/api/TenantGroups/",
    alias: "api_TenantGroups_create",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
    ],
    response: TenantGroup,
  },
  {
    method: "get",
    path: "/api/TenantGroups/:id/",
    alias: "api_TenantGroups_retrieve",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroupDetail,
  },
  {
    method: "put",
    path: "/api/TenantGroups/:id/",
    alias: "api_TenantGroups_update",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "patch",
    path: "/api/TenantGroups/:id/",
    alias: "api_TenantGroups_partial_update",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "delete",
    path: "/api/TenantGroups/:id/",
    alias: "api_TenantGroups_destroy",
    description: `ViewSet for managing tenant groups (TenantGroup).

Allows tenant admins to:
- List/create/update/delete groups
- Manage permissions on groups
- Manage group membership (UserRoles)
- Clone groups and create from presets`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/TenantGroups/:id/clone/",
    alias: "api_TenantGroups_clone_create",
    description: `Clone a group with a new name.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "get",
    path: "/api/TenantGroups/:id/members/",
    alias: "api_TenantGroups_members_retrieve",
    description: `Manage group members (UserRoles).

GET: List members
POST: Add member (user_id required, facility_id/company_id optional)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "post",
    path: "/api/TenantGroups/:id/members/",
    alias: "api_TenantGroups_members_create",
    description: `Manage group members (UserRoles).

GET: List members
POST: Add member (user_id required, facility_id/company_id optional)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "delete",
    path: "/api/TenantGroups/:id/members/:user_id/",
    alias: "api_TenantGroups_members_destroy",
    description: `Remove a user from the group.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "user_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.object({ status: z.string() }).passthrough(),
  },
  {
    method: "get",
    path: "/api/TenantGroups/:id/permissions/",
    alias: "api_TenantGroups_permissions_retrieve",
    description: `Manage permissions on a group.

GET: List current permissions
PUT: Replace all permissions
POST: Add permissions
DELETE: Remove permissions`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "post",
    path: "/api/TenantGroups/:id/permissions/",
    alias: "api_TenantGroups_permissions_create",
    description: `Manage permissions on a group.

GET: List current permissions
PUT: Replace all permissions
POST: Add permissions
DELETE: Remove permissions`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "put",
    path: "/api/TenantGroups/:id/permissions/",
    alias: "api_TenantGroups_permissions_update",
    description: `Manage permissions on a group.

GET: List current permissions
PUT: Replace all permissions
POST: Add permissions
DELETE: Remove permissions`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "delete",
    path: "/api/TenantGroups/:id/permissions/",
    alias: "api_TenantGroups_permissions_destroy",
    description: `Manage permissions on a group.

GET: List current permissions
PUT: Replace all permissions
POST: Add permissions
DELETE: Remove permissions`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/TenantGroups/:id/preset-diff/",
    alias: "api_TenantGroups_preset_diff_retrieve",
    description: `Compare group permissions against its original preset.

Returns added/removed permissions vs the preset template.`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TenantGroup,
  },
  {
    method: "post",
    path: "/api/TenantGroups/from-preset/",
    alias: "api_TenantGroups_from_preset_create",
    description: `Create a new group from a preset template.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantGroupRequest,
      },
    ],
    response: TenantGroup,
  },
  {
    method: "get",
    path: "/api/Tenants/",
    alias: "api_Tenants_list",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedTenantList,
  },
  {
    method: "post",
    path: "/api/Tenants/",
    alias: "api_Tenants_create",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantCreateRequest,
      },
    ],
    response: TenantCreate,
  },
  {
    method: "get",
    path: "/api/Tenants/:slug/",
    alias: "api_Tenants_retrieve",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "put",
    path: "/api/Tenants/:slug/",
    alias: "api_Tenants_update",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantRequest,
      },
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "patch",
    path: "/api/Tenants/:slug/",
    alias: "api_Tenants_partial_update",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTenantRequest,
      },
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "delete",
    path: "/api/Tenants/:slug/",
    alias: "api_Tenants_destroy",
    description: `ViewSet for managing tenants (platform admin only).

Only available in SaaS mode and requires superuser/staff.`,
    requestFormat: "json",
    parameters: [
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/Tenants/:slug/activate/",
    alias: "api_Tenants_activate_create",
    description: `Activate a suspended tenant.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantRequest,
      },
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "post",
    path: "/api/Tenants/:slug/suspend/",
    alias: "api_Tenants_suspend_create",
    description: `Suspend a tenant.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TenantRequest,
      },
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "get",
    path: "/api/Tenants/:slug/users/",
    alias: "api_Tenants_users_retrieve",
    description: `List users in a tenant.`,
    requestFormat: "json",
    parameters: [
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: Tenant,
  },
  {
    method: "post",
    path: "/api/tenants/signup/",
    alias: "api_tenants_signup_create",
    description: `Self-service tenant signup endpoint.

Creates a new tenant and admin user. Only available in SaaS mode.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SignupRequest,
      },
    ],
    response: SignupResponse,
  },
  {
    method: "get",
    path: "/api/ThreeDModels/",
    alias: "api_ThreeDModels_list",
    description: `List 3D models with filtering and search capabilities`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "file_type__icontains",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "uploaded_at",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "uploaded_at__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "uploaded_at__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
    ],
    response: PaginatedThreeDModelList,
  },
  {
    method: "post",
    path: "/api/ThreeDModels/",
    alias: "api_ThreeDModels_create",
    description: `ViewSet for managing 3D model files for quality visualization`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ThreeDModelRequest,
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "get",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_retrieve",
    description: `ViewSet for managing 3D model files for quality visualization`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "put",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_update",
    description: `ViewSet for managing 3D model files for quality visualization`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ThreeDModelRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "patch",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_partial_update",
    description: `ViewSet for managing 3D model files for quality visualization`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedThreeDModelRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "delete",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_destroy",
    description: `ViewSet for managing 3D model files for quality visualization`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/ThreeDModels/export-excel/",
    alias: "api_ThreeDModels_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/ThreeDModels/metadata/",
    alias: "api_ThreeDModels_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/TimeEntries/",
    alias: "api_TimeEntries_list",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "approved",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "entry_type",
        type: "Query",
        schema: z
          .enum(["downtime", "indirect", "production", "rework", "setup"])
          .optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedTimeEntryList,
  },
  {
    method: "post",
    path: "/api/TimeEntries/",
    alias: "api_TimeEntries_create",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TimeEntryRequest,
      },
    ],
    response: TimeEntry,
  },
  {
    method: "get",
    path: "/api/TimeEntries/:id/",
    alias: "api_TimeEntries_retrieve",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TimeEntry,
  },
  {
    method: "put",
    path: "/api/TimeEntries/:id/",
    alias: "api_TimeEntries_update",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TimeEntryRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TimeEntry,
  },
  {
    method: "patch",
    path: "/api/TimeEntries/:id/",
    alias: "api_TimeEntries_partial_update",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTimeEntryRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TimeEntry,
  },
  {
    method: "delete",
    path: "/api/TimeEntries/:id/",
    alias: "api_TimeEntries_destroy",
    description: `Labor time tracking with clock-in/out`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/TimeEntries/:id/approve/",
    alias: "api_TimeEntries_approve_create",
    description: `Approve a time entry`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TimeEntry,
  },
  {
    method: "post",
    path: "/api/TimeEntries/:id/clock_out/",
    alias: "api_TimeEntries_clock_out_create",
    description: `End a time entry`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ notes: z.string().min(1) })
          .partial()
          .passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TimeEntry,
  },
  {
    method: "post",
    path: "/api/TimeEntries/clock_in/",
    alias: "api_TimeEntries_clock_in_create",
    description: `Start a new time entry for the current user`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ClockInRequest,
      },
    ],
    response: TimeEntry,
  },
  {
    method: "get",
    path: "/api/TimeEntries/export-excel/",
    alias: "api_TimeEntries_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/TrackerOrders/",
    alias: "api_TrackerOrders_list",
    description: `Customer-facing read-only order tracking endpoint.

Security:
- Read-only: customers cannot create, update, or delete orders
- Filtered by SecureManager.for_user(): customers only see their own orders
- Limited fields via CustomerOrderSerializer: no internal data exposed

Use /api/Orders/ for full CRUD operations (staff only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedCustomerOrderList,
  },
  {
    method: "get",
    path: "/api/TrackerOrders/:id/",
    alias: "api_TrackerOrders_retrieve",
    description: `Customer-facing read-only order tracking endpoint.

Security:
- Read-only: customers cannot create, update, or delete orders
- Filtered by SecureManager.for_user(): customers only see their own orders
- Limited fields via CustomerOrderSerializer: no internal data exposed

Use /api/Orders/ for full CRUD operations (staff only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: CustomerOrder,
  },
  {
    method: "post",
    path: "/api/TrackerOrders/:id/invite/",
    alias: "api_TrackerOrders_invite_create",
    description: `Invite someone to view this order.

Works for both staff and customers who have access to the order.
Creates user if doesn&#x27;t exist, sends invitation email via Celery.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ email: z.string().min(1).email() }).passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: InviteViewerResponse,
    errors: [
      {
        status: 400,
        schema: z.object({ detail: z.string() }).passthrough(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/TrainingRecords/",
    alias: "api_TrainingRecords_list",
    description: `List training records with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "status",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "trainer",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedTrainingRecordList,
  },
  {
    method: "post",
    path: "/api/TrainingRecords/",
    alias: "api_TrainingRecords_create",
    description: `Create a new training record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingRecordRequest,
      },
    ],
    response: TrainingRecord,
  },
  {
    method: "get",
    path: "/api/TrainingRecords/:id/",
    alias: "api_TrainingRecords_retrieve",
    description: `Retrieve a specific training record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRecord,
  },
  {
    method: "put",
    path: "/api/TrainingRecords/:id/",
    alias: "api_TrainingRecords_update",
    description: `Update a training record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRecord,
  },
  {
    method: "patch",
    path: "/api/TrainingRecords/:id/",
    alias: "api_TrainingRecords_partial_update",
    description: `Partially update a training record`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTrainingRecordRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRecord,
  },
  {
    method: "delete",
    path: "/api/TrainingRecords/:id/",
    alias: "api_TrainingRecords_destroy",
    description: `Soft delete a training record`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/TrainingRecords/expired/",
    alias: "api_TrainingRecords_expired_list",
    description: `Get all expired training records`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "trainer",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedTrainingRecordList,
  },
  {
    method: "get",
    path: "/api/TrainingRecords/expiring-soon/",
    alias: "api_TrainingRecords_expiring_soon_list",
    description: `Get training records expiring within N days (default 30)`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().optional().default(30),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "trainer",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedTrainingRecordList,
  },
  {
    method: "get",
    path: "/api/TrainingRecords/export-excel/",
    alias: "api_TrainingRecords_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/TrainingRecords/metadata/",
    alias: "api_TrainingRecords_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/TrainingRecords/my-training/",
    alias: "api_TrainingRecords_my_training_list",
    description: `Get training records for the current authenticated user`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "trainer",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedTrainingRecordList,
  },
  {
    method: "get",
    path: "/api/TrainingRecords/stats/",
    alias: "api_TrainingRecords_stats_retrieve",
    description: `Get training statistics summary`,
    requestFormat: "json",
    response: TrainingStats,
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/",
    alias: "api_TrainingRequirements_list",
    description: `List training requirements with filtering`,
    requestFormat: "json",
    parameters: [
      {
        name: "equipment_type",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedTrainingRequirementList,
  },
  {
    method: "post",
    path: "/api/TrainingRequirements/",
    alias: "api_TrainingRequirements_create",
    description: `Create a new training requirement`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingRequirementRequest,
      },
    ],
    response: TrainingRequirement,
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/:id/",
    alias: "api_TrainingRequirements_retrieve",
    description: `Retrieve a specific training requirement`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRequirement,
  },
  {
    method: "put",
    path: "/api/TrainingRequirements/:id/",
    alias: "api_TrainingRequirements_update",
    description: `Update a training requirement`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingRequirementRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRequirement,
  },
  {
    method: "patch",
    path: "/api/TrainingRequirements/:id/",
    alias: "api_TrainingRequirements_partial_update",
    description: `Partially update a training requirement`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTrainingRequirementRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingRequirement,
  },
  {
    method: "delete",
    path: "/api/TrainingRequirements/:id/",
    alias: "api_TrainingRequirements_destroy",
    description: `Soft delete a training requirement`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/export-excel/",
    alias: "api_TrainingRequirements_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/for-process/",
    alias: "api_TrainingRequirements_for_process_list",
    description: `Get all training requirements for a specific process`,
    requestFormat: "json",
    parameters: [
      {
        name: "equipment_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "process_id",
        type: "Query",
        schema: z.string(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedTrainingRequirementList,
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/for-step/",
    alias: "api_TrainingRequirements_for_step_list",
    description: `Get all training requirements for a specific step`,
    requestFormat: "json",
    parameters: [
      {
        name: "equipment_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "step_id",
        type: "Query",
        schema: z.string(),
      },
      {
        name: "training_type",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
    ],
    response: PaginatedTrainingRequirementList,
  },
  {
    method: "get",
    path: "/api/TrainingRequirements/metadata/",
    alias: "api_TrainingRequirements_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/TrainingTypes/",
    alias: "api_TrainingTypes_list",
    description: `List all training types`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "validity_period_days",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedTrainingTypeList,
  },
  {
    method: "post",
    path: "/api/TrainingTypes/",
    alias: "api_TrainingTypes_create",
    description: `Create a new training type`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingTypeRequest,
      },
    ],
    response: TrainingType,
  },
  {
    method: "get",
    path: "/api/TrainingTypes/:id/",
    alias: "api_TrainingTypes_retrieve",
    description: `Retrieve a specific training type`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingType,
  },
  {
    method: "put",
    path: "/api/TrainingTypes/:id/",
    alias: "api_TrainingTypes_update",
    description: `Update a training type`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TrainingTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingType,
  },
  {
    method: "patch",
    path: "/api/TrainingTypes/:id/",
    alias: "api_TrainingTypes_partial_update",
    description: `Partially update a training type`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedTrainingTypeRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: TrainingType,
  },
  {
    method: "delete",
    path: "/api/TrainingTypes/:id/",
    alias: "api_TrainingTypes_destroy",
    description: `Soft delete a training type`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/TrainingTypes/export-excel/",
    alias: "api_TrainingTypes_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/TrainingTypes/metadata/",
    alias: "api_TrainingTypes_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "get",
    path: "/api/User/",
    alias: "api_User_list",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "archived",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "date_joined__gte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "date_joined__lte",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "email",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "first_name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "is_active",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "is_staff",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "last_name",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "parent_company",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "username",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedUserList,
  },
  {
    method: "post",
    path: "/api/User/",
    alias: "api_User_create",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserRequest,
      },
    ],
    response: User,
  },
  {
    method: "get",
    path: "/api/User/:id/",
    alias: "api_User_retrieve",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: User,
  },
  {
    method: "put",
    path: "/api/User/:id/",
    alias: "api_User_update",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: User,
  },
  {
    method: "patch",
    path: "/api/User/:id/",
    alias: "api_User_partial_update",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedUserRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: User,
  },
  {
    method: "delete",
    path: "/api/User/:id/",
    alias: "api_User_destroy",
    description: `Enhanced User ViewSet with comprehensive filtering, ordering, and search`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/User/bulk-activate/",
    alias: "api_User_bulk_activate_create",
    description: `Bulk activate/deactivate users`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BulkUserActivationInputRequest,
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/User/bulk-assign-company/",
    alias: "api_User_bulk_assign_company_create",
    description: `Bulk assign users to a company`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BulkCompanyAssignmentInputRequest,
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/User/export-excel/",
    alias: "api_User_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/User/metadata/",
    alias: "api_User_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "post",
    path: "/api/User/send-invitation/",
    alias: "api_User_send_invitation_create",
    description: `Send invitation email to a user`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ user_id: z.number().int() }).passthrough(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/user/token/",
    alias: "get_user_api_token",
    description: `Get or create an API token for the current session-authenticated user`,
    requestFormat: "json",
    response: z
      .object({ token: z.string(), created: z.boolean() })
      .partial()
      .passthrough(),
    errors: [
      {
        status: 401,
        schema: z.unknown(),
      },
      {
        status: 500,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/UserInvitations/",
    alias: "api_UserInvitations_list",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "accepted_at",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "invited_by",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "user",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedUserInvitationList,
  },
  {
    method: "post",
    path: "/api/UserInvitations/",
    alias: "api_UserInvitations_create",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserInvitationRequest,
      },
    ],
    response: UserInvitation,
  },
  {
    method: "get",
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_retrieve",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserInvitation,
  },
  {
    method: "put",
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_update",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserInvitationRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserInvitation,
  },
  {
    method: "patch",
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_partial_update",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedUserInvitationRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserInvitation,
  },
  {
    method: "delete",
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_destroy",
    description: `ViewSet for managing user invitations.

Provides endpoints for:
- Listing invitations (staff only)
- Validating invitation tokens (public)
- Accepting invitations (public)
- Resending invitations (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
  },
  {
    method: "post",
    path: "/api/UserInvitations/accept/",
    alias: "api_UserInvitations_accept_create",
    description: `Accept an invitation and set up user account (public endpoint)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AcceptInvitationInputRequest,
      },
    ],
    response: AcceptInvitationResponse,
  },
  {
    method: "post",
    path: "/api/UserInvitations/resend/",
    alias: "api_UserInvitations_resend_create",
    description: `Resend an invitation (staff only)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ invitation_id: z.number().int() }).passthrough(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/UserInvitations/validate-token/",
    alias: "api_UserInvitations_validate_token_create",
    description: `Validate an invitation token (public endpoint)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ token: z.string().min(1) }).passthrough(),
      },
    ],
    response: ValidateTokenResponse,
  },
  {
    method: "get",
    path: "/api/users/:user_id/effective-permissions/",
    alias: "api_users_effective_permissions_retrieve",
    description: `Get effective permissions for a user (union of all their groups).

Admins can check any user; regular users can only check themselves.`,
    requestFormat: "json",
    parameters: [
      {
        name: "user_id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: EffectivePermissionsResponse,
  },
  {
    method: "get",
    path: "/api/users/me/effective-permissions/",
    alias: "api_users_me_effective_permissions_retrieve",
    description: `Get effective permissions for a user (union of all their groups).

Admins can check any user; regular users can only check themselves.`,
    requestFormat: "json",
    response: EffectivePermissionsResponse,
  },
  {
    method: "get",
    path: "/api/WorkCenters-Options/",
    alias: "api_WorkCenters_Options_list",
    description: `Lightweight work center endpoint for dropdowns`,
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(WorkCenterSelect),
  },
  {
    method: "get",
    path: "/api/WorkCenters-Options/:id/",
    alias: "api_WorkCenters_Options_retrieve",
    description: `Lightweight work center endpoint for dropdowns`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkCenterSelect,
  },
  {
    method: "get",
    path: "/api/WorkCenters/",
    alias: "api_WorkCenters_list",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedWorkCenterList,
  },
  {
    method: "post",
    path: "/api/WorkCenters/",
    alias: "api_WorkCenters_create",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: WorkCenterRequest,
      },
    ],
    response: WorkCenter,
  },
  {
    method: "get",
    path: "/api/WorkCenters/:id/",
    alias: "api_WorkCenters_retrieve",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkCenter,
  },
  {
    method: "put",
    path: "/api/WorkCenters/:id/",
    alias: "api_WorkCenters_update",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: WorkCenterRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkCenter,
  },
  {
    method: "patch",
    path: "/api/WorkCenters/:id/",
    alias: "api_WorkCenters_partial_update",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedWorkCenterRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkCenter,
  },
  {
    method: "delete",
    path: "/api/WorkCenters/:id/",
    alias: "api_WorkCenters_destroy",
    description: `Work center management`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/WorkCenters/export-excel/",
    alias: "api_WorkCenters_export_excel_retrieve",
    description: `Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/WorkOrders/",
    alias: "api_WorkOrders_list",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "priority",
        type: "Query",
        schema: z
          .union([z.literal(1), z.literal(2), z.literal(3), z.literal(4)])
          .optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "related_order",
        type: "Query",
        schema: z.string().uuid().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "workorder_status",
        type: "Query",
        schema: z
          .enum([
            "CANCELLED",
            "COMPLETED",
            "IN_PROGRESS",
            "ON_HOLD",
            "PENDING",
            "WAITING_FOR_OPERATOR",
          ])
          .optional(),
      },
    ],
    response: PaginatedWorkOrderListList,
  },
  {
    method: "post",
    path: "/api/WorkOrders/",
    alias: "api_WorkOrders_create",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: WorkOrderRequest,
      },
    ],
    response: WorkOrder,
  },
  {
    method: "get",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_retrieve",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "put",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_update",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: WorkOrderRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "patch",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_partial_update",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedWorkOrderRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "delete",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_destroy",
    description: `Work Orders CRUD with CSV import/export support.

Import/Export endpoints (auto-configured from model):
- GET /import-template/ - Download import template (CSV or Excel)
- POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
- GET /import-status/{task_id}/ - Check status of background import
- GET /export/ - Export filtered data to CSV/Excel`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/WorkOrders/:id/qa_documents/",
    alias: "api_WorkOrders_qa_documents_retrieve",
    description: `Get documents relevant to QA for this work order`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: QADocumentsResponse,
  },
  {
    method: "get",
    path: "/api/WorkOrders/:id/qa_summary/",
    alias: "api_WorkOrders_qa_summary_retrieve",
    description: `Get QA summary for work order including batch status`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "get",
    path: "/api/WorkOrders/:id/step_history/",
    alias: "api_WorkOrders_step_history_retrieve",
    description: `Get step history summary for digital traveler display`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: WorkOrderStepHistoryResponse,
  },
  {
    method: "get",
    path: "/api/WorkOrders/export/",
    alias: "api_WorkOrders_export_retrieve",
    description: `Export filtered data to CSV or Excel format.`,
    requestFormat: "json",
    parameters: [
      {
        name: "fields",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "filename",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/WorkOrders/import-preview/",
    alias: "api_WorkOrders_import_preview_create",
    description: `Preview a file before importing. Returns columns, suggested mappings, and sample data.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
    ],
    response: ImportPreviewResponse,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/WorkOrders/import-status/:task_id/",
    alias: "api_WorkOrders_import_status_retrieve",
    description: `Check status of a background import task.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ImportStatusResponse,
  },
  {
    method: "get",
    path: "/api/WorkOrders/import-template/",
    alias: "api_WorkOrders_import_template_retrieve",
    description: `Download an import template with headers, hints, and FK lookups (Excel only).`,
    requestFormat: "json",
    parameters: [
      {
        name: "format",
        type: "Query",
        schema: z.enum(["csv", "xlsx"]).optional().default("xlsx"),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "post",
    path: "/api/WorkOrders/import/",
    alias: "api_WorkOrders_import_create",
    description: `Import data from CSV or Excel file. Small imports return immediate results (207). Large imports are queued and return task_id (202).`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: api_Orders_import_create_Body,
      },
    ],
    response: ImportQueued,
    errors: [
      {
        status: 400,
        schema: z.unknown(),
      },
    ],
  },
  {
    method: "get",
    path: "/api/WorkOrders/metadata/",
    alias: "api_WorkOrders_metadata_retrieve",
    description: `Return searchable/filterable/orderable field information with filter options.`,
    requestFormat: "json",
    response: ListMetadataResponse,
  },
  {
    method: "post",
    path: "/auth/login/",
    alias: "auth_login_create",
    description: `Check the credentials and return the REST Token
if the credentials are valid and authenticated.
Calls Django Auth login method to register User ID
in Django session framework

Accept the following POST parameters: username, password
Return the REST Framework Token Object&#x27;s key.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: LoginRequest,
      },
    ],
    response: z.object({ key: z.string().max(40) }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/logout/",
    alias: "auth_logout_create",
    description: `Calls Django logout method and delete the Token object
assigned to the current User object.

Accepts/Returns nothing.`,
    requestFormat: "json",
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/password/change/",
    alias: "auth_password_change_create",
    description: `Calls Django Auth SetPasswordForm save method.

Accepts the following POST parameters: new_password1, new_password2
Returns the success/fail message.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PasswordChangeRequest,
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/password/reset/",
    alias: "auth_password_reset_create",
    description: `Calls Django Auth PasswordResetForm save method.

Accepts the following POST parameters: email
Returns the success/fail message.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ email: z.string().min(1).email() }).passthrough(),
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/password/reset/confirm/",
    alias: "auth_password_reset_confirm_create",
    description: `Password reset e-mail link is confirmed, therefore
this resets the user&#x27;s password.

Accepts the following POST parameters: token, uid,
    new_password1, new_password2
Returns the success/fail message.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PasswordResetConfirmRequest,
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/registration/",
    alias: "auth_registration_create",
    description: `Registers a new user.

Accepts the following POST parameters: username, email, password1, password2.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RegisterRequest,
      },
    ],
    response: z.object({ key: z.string().max(40) }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/registration/resend-email/",
    alias: "auth_registration_resend_email_create",
    description: `Resends another email to an unverified email.

Accepts the following POST parameter: email.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ email: z.string().min(1).email() }).passthrough(),
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "post",
    path: "/auth/registration/verify-email/",
    alias: "auth_registration_verify_email_create",
    description: `Verifies the email associated with the provided key.

Accepts the following POST parameter: key.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ key: z.string().min(1) }).passthrough(),
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
  {
    method: "get",
    path: "/auth/user/",
    alias: "auth_user_retrieve",
    description: `Enhanced user details view with staff and group info`,
    requestFormat: "json",
    response: UserDetails,
  },
  {
    method: "put",
    path: "/auth/user/",
    alias: "auth_user_update",
    description: `Enhanced user details view with staff and group info`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserDetailsRequest,
      },
    ],
    response: UserDetails,
  },
  {
    method: "patch",
    path: "/auth/user/",
    alias: "auth_user_partial_update",
    description: `Enhanced user details view with staff and group info`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedUserDetailsRequest,
      },
    ],
    response: UserDetails,
  },
  {
    method: "post",
    path: "/password/reset/confirm/:uidb64/:token/",
    alias: "password_reset_confirm_create",
    description: `Password reset e-mail link is confirmed, therefore
this resets the user&#x27;s password.

Accepts the following POST parameters: token, uid,
    new_password1, new_password2
Returns the success/fail message.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PasswordResetConfirmRequest,
      },
      {
        name: "token",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "uidb64",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.object({ detail: z.string() }).passthrough(),
  },
]);

// Helper function to get CSRF token from cookies
function getCsrfToken(): string | null {
  const name = "csrftoken=";
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookies = decodedCookie.split(";");
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.indexOf(name) === 0) {
      return cookie.substring(name.length);
    }
  }
  return null;
}

// Use VITE_API_TARGET environment variable for production builds
// In development with Vite dev server, don't set base URL to rely on Vite proxy
// In production, this will be replaced at build time with the actual backend URL
const BASE_URL = import.meta.env.VITE_API_TARGET;

export const api = BASE_URL
  ? new Zodios(BASE_URL, endpoints, {
      axiosConfig: {
        withCredentials: true,
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: "repeat" }),
        headers: {
          "X-CSRFToken": getCsrfToken() || "",
        },
      },
    })
  : new Zodios(endpoints, {
      axiosConfig: {
        withCredentials: true,
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: "repeat" }),
        headers: {
          "X-CSRFToken": getCsrfToken() || "",
        },
      },
    });

// Axios interceptor to refresh CSRF token before each request
api.axios.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken && config.headers) {
    config.headers["X-CSRFToken"] = csrfToken;
  }
  return config;
});

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, {
    axiosConfig: {
      withCredentials: true,
      ...options?.axiosConfig,
      paramsSerializer: (params) =>
        qs.stringify(params, { arrayFormat: "repeat" }),
      headers: {
        "X-CSRFToken": getCsrfToken() || "",
        ...options?.axiosConfig?.headers,
      },
    },
    ...options,
  });
}
