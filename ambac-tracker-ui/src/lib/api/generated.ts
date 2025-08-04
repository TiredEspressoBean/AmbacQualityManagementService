import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";
import qs from "qs";

type AuditLog = {
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
type ActionEnum =
  /**
   * * `0` - create
   * `1` - update
   * `2` - delete
   * `3` - access
   *
   * @enum 0, 1, 2, 3
   */
  0 | 1 | 2 | 3;
type BulkAddPartsInputRequest = {
  part_type: number;
  step: number;
  quantity: number;
  part_status?: /**
   * @default "PENDING"
   */
  PartStatusEnum | undefined;
  work_order?: number | undefined;
  erp_id_start?: /**
   * @default 1
   */
  number | undefined;
};
type PartStatusEnum =
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
type Documents = {
  id: number;
  classification?:
    | /**
     * Level of document classification:
    - "public": Public
    - "internal": Internal Use
    - "confidential": Confidential
    - "restricted": Restricted (serious impact)
    - "secret": Secret (critical impact)
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
    (ClassificationEnum | NullEnum | null)
    | undefined;
  AI_readable?: boolean | undefined;
  is_image: boolean;
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
     * ID of the object this document relates to
     *
     * @minimum 0
     * @maximum 9223372036854776000
     */
    (number | null)
    | undefined;
  content_type_info: {};
  version?: /**
   * @minimum 0
   * @maximum 32767
   */
  number | undefined;
  access_info: {};
  auto_properties: {};
  created_at: string;
  updated_at: string;
  archived: boolean;
};
type ClassificationEnum =
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
type NullEnum =
  /**
   * @enum
   */
  unknown;
type DocumentsRequest = {
  classification?:
    | /**
     * Level of document classification:
    - "public": Public
    - "internal": Internal Use
    - "confidential": Confidential
    - "restricted": Restricted (serious impact)
    - "secret": Secret (critical impact)
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
    (ClassificationEnum | NullEnum | null)
    | undefined;
  AI_readable?: boolean | undefined;
  is_image: boolean;
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
     * ID of the object this document relates to
     *
     * @minimum 0
     * @maximum 9223372036854776000
     */
    (number | null)
    | undefined;
  version?: /**
   * @minimum 0
   * @maximum 32767
   */
  number | undefined;
};
type MeasurementDefinition = {
  id: number;
  /**
   * @maxLength 100
   */
  label: string;
  step_name: string;
  allow_override?: boolean | undefined;
  allow_remeasure?: boolean | undefined;
  allow_quarantine?: boolean | undefined;
  unit?: /**
   * @maxLength 50
   */
  string | undefined;
  require_qa_review?: boolean | undefined;
  nominal?: (number | null) | undefined;
  upper_tol?: (number | null) | undefined;
  lower_tol?: (number | null) | undefined;
  required?: boolean | undefined;
  type: TypeEnum;
  step: number;
};
type TypeEnum =
  /**
   * * `NUMERIC` - Numeric
   * `PASS_FAIL` - Pass/Fail
   *
   * @enum NUMERIC, PASS_FAIL
   */
  "NUMERIC" | "PASS_FAIL";
type MeasurementDefinitionRequest = {
  /**
   * @minLength 1
   * @maxLength 100
   */
  label: string;
  allow_override?: boolean | undefined;
  allow_remeasure?: boolean | undefined;
  allow_quarantine?: boolean | undefined;
  unit?: /**
   * @maxLength 50
   */
  string | undefined;
  require_qa_review?: boolean | undefined;
  nominal?: (number | null) | undefined;
  upper_tol?: (number | null) | undefined;
  lower_tol?: (number | null) | undefined;
  required?: boolean | undefined;
  type: TypeEnum;
};
type Orders = {
  id: number;
  /**
   * @maxLength 50
   */
  name: string;
  customer_note?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  customer: number;
  customer_info: UserSelect;
  company: number;
  company_info: Company;
  estimated_completion?: (string | null) | undefined;
  order_status: OrderStatusEnum;
  current_hubspot_gate?: (number | null) | undefined;
  parts_summary: {};
  process_stages: Array<unknown>;
  customer_first_name: string;
  customer_last_name: string;
  company_name: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
};
type UserSelect = {
  id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   */
  username: string;
  first_name?: /**
   * @maxLength 150
   */
  string | undefined;
  last_name?: /**
   * @maxLength 150
   */
  string | undefined;
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
type Company = {
  id: number;
  /**
   * @maxLength 50
   */
  name: string;
  description: string;
  /**
   * @maxLength 50
   */
  hubspot_api_id: string;
  user_count: number;
  created_at: string;
  updated_at: string;
  archived: boolean;
};
type OrderStatusEnum =
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
type OrdersRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  customer_note?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  customer: number;
  company: number;
  estimated_completion?: (string | null) | undefined;
  order_status: OrderStatusEnum;
  current_hubspot_gate?: (number | null) | undefined;
};
type PaginatedAuditLogList = {
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
type PaginatedContentTypeList = {
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
  results: Array<ContentType>;
};
type ContentType = {
  id: number;
  /**
   * @maxLength 100
   */
  app_label: string;
  /**
   * @maxLength 100
   */
  model: string;
};
type PaginatedDocumentsList = {
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
type PaginatedEquipmentTypeList = {
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
type EquipmentType = {
  id: number;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  /**
   * @maxLength 50
   */
  name: string;
};
type PaginatedEquipmentsList = {
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
type Equipments = {
  id: number;
  /**
   * @maxLength 50
   */
  name: string;
  equipment_type?: (number | null) | undefined;
  equipment_type_name: string;
};
type PaginatedMeasurementDefinitionList = {
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
type PaginatedOrdersList = {
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
type PaginatedPartTypesList = {
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
type PartTypes = {
  id: number;
  previous_version: number | null;
  previous_version_name: string | null;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
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
  version?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  ERP_id?:
    | /**
     * @maxLength 50
     */
    (string | null)
    | undefined;
};
type PaginatedPartsList = {
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
type Parts = {
  id: number;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  part_status?: PartStatusEnum | undefined;
  archived: boolean;
  requires_sampling: boolean;
  order?: number | undefined;
  order_info: {};
  part_type: number;
  part_type_info: {};
  step: number;
  step_info: {};
  work_order?: (number | null) | undefined;
  work_order_info: {};
  sampling_info: {};
  quality_info: {};
  sampling_history: {};
  created_at: string;
  updated_at: string;
  has_error: boolean;
  part_type_name: string;
  process_name: string;
  order_name: string | null;
  step_description: string;
  work_order_erp_id: string | null;
  quality_status: {};
  sampling_rule?: (number | null) | undefined;
  sampling_ruleset?: (number | null) | undefined;
  sampling_context?: unknown | undefined;
};
type PaginatedProcessWithStepsList = {
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
type ProcessWithSteps = {
  id: number;
  /**
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  part_type: number;
  steps: Array<Step>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
};
type Step = {
  /**
   * @maxLength 50
   */
  name: string;
  id: number;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  order: number;
  description?: (string | null) | undefined;
  is_last_step?: boolean | undefined;
  process: number;
  part_type: number;
  process_name: string;
  part_type_name: string;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
};
type PaginatedProcessesList = {
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
type Processes = {
  id: number;
  part_type_name: string;
  steps: Array<Step>;
  archived?: boolean | undefined;
  deleted_at?: (string | null) | undefined;
  created_at: string;
  updated_at: string;
  /**
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
  version?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  part_type: number;
  previous_version?: (number | null) | undefined;
};
type PaginatedQualityErrorsListList = {
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
type QualityErrorsList = {
  id: number;
  /**
   * @maxLength 50
   */
  error_name: string;
  error_example: string;
  part_type?: (number | null) | undefined;
  part_type_name: string;
};
type PaginatedQualityReportsList = {
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
type QualityReports = {
  id: number;
  step?: (number | null) | undefined;
  part?: (number | null) | undefined;
  machine?: (number | null) | undefined;
  operator?: Array<number> | undefined;
  sampling_rule?: (number | null) | undefined;
  sampling_method?: /**
   * @maxLength 50
   */
  string | undefined;
  status: StatusEnum;
  description?:
    | /**
     * @maxLength 300
     */
    (string | null)
    | undefined;
  file?: (number | null) | undefined;
  created_at: string;
  errors?: Array<number> | undefined;
  sampling_audit_log?:
    | /**
     * Links to the sampling decision that triggered this inspection
     */
    (number | null)
    | undefined;
};
type StatusEnum =
  /**
   * * `PASS` - Pass
   * `FAIL` - Fail
   * `PENDING` - Pending
   *
   * @enum PASS, FAIL, PENDING
   */
  "PASS" | "FAIL" | "PENDING";
type PaginatedSamplingRuleList = {
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
type SamplingRule = {
  id: number;
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
  ruleset: number;
  ruleset_info: {};
  created_by?: (number | null) | undefined;
  created_at: string;
  modified_by?: (number | null) | undefined;
  modified_at: string;
  archived: boolean;
  ruletype_name: string;
  ruleset_name: string;
};
type RuleTypeEnum =
  /**
   * * `every_nth_part` - Every Nth Part
   * `percentage` - Percentage of Parts
   * `random` - Pure Random
   * `first_n_parts` - First N Parts
   * `last_n_parts` - Last N Parts
   *
   * @enum every_nth_part, percentage, random, first_n_parts, last_n_parts
   */
  "every_nth_part" | "percentage" | "random" | "first_n_parts" | "last_n_parts";
type PaginatedSamplingRuleSetList = {
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
type SamplingRuleSet = {
  id: number;
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
   * @default 1
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
  is_fallback?: /**
   * @default false
   */
  boolean | undefined;
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
  archived: boolean;
  part_type: number;
  part_type_info: {};
  process: number;
  process_info: {};
  step: number;
  step_info: {};
  rules: Array<unknown>;
  created_by?: (number | null) | undefined;
  created_at: string;
  modified_by?: (number | null) | undefined;
  modified_at: string;
  part_type_name: string;
  process_name: string;
};
type PaginatedStepDistributionResponseList = {
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
type StepDistributionResponse = {
  id: number;
  count: number;
  name: string;
};
type PaginatedStepsList = {
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
type Steps = {
  id: number;
  /**
   * @maxLength 50
   */
  name: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  order: number;
  expected_duration?: (string | null) | undefined;
  description?: (string | null) | undefined;
  is_last_step?: boolean | undefined;
  block_on_quarantine?: boolean | undefined;
  requires_qa_signoff?: boolean | undefined;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
  pass_threshold?: number | undefined;
  process: number;
  part_type: number;
  process_info: {};
  part_type_info: {};
  resolved_sampling_rules: unknown;
  sampling_coverage: {};
  process_name: string;
  part_type_name: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
};
type PaginatedUserSelectList = {
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
type PaginatedWorkOrderList = {
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
  results: Array<WorkOrder>;
};
type WorkOrder = {
  id: number;
  /**
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status?: WorkorderStatusEnum | undefined;
  quantity?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  related_order?: (number | null) | undefined;
  related_order_info: {};
  related_order_detail: Orders;
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
  created_at: string;
  updated_at: string;
  archived: boolean;
};
type WorkorderStatusEnum =
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
type PartsRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  part_status?: PartStatusEnum | undefined;
  order?: number | undefined;
  part_type: number;
  step: number;
  work_order?: (number | null) | undefined;
  sampling_rule?: (number | null) | undefined;
  sampling_ruleset?: (number | null) | undefined;
  sampling_context?: unknown | undefined;
};
type PatchedDocumentsRequest = Partial<{
  /**
     * Level of document classification:
    - "public": Public
    - "internal": Internal Use
    - "confidential": Confidential
    - "restricted": Restricted (serious impact)
    - "secret": Secret (critical impact)
    
    * `public` - Public
    * `internal` - Internal Use
    * `confidential` - Confidential
    * `restricted` - Restricted
    * `secret` - Secret
     */
  classification: ClassificationEnum | NullEnum | null;
  AI_readable: boolean;
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
   * ID of the object this document relates to
   *
   * @minimum 0
   * @maximum 9223372036854776000
   */
  object_id: number | null;
  /**
   * @minimum 0
   * @maximum 32767
   */
  version: number;
}>;
type PatchedMeasurementDefinitionRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 100
   */
  label: string;
  allow_override: boolean;
  allow_remeasure: boolean;
  allow_quarantine: boolean;
  /**
   * @maxLength 50
   */
  unit: string;
  require_qa_review: boolean;
  nominal: number | null;
  upper_tol: number | null;
  lower_tol: number | null;
  required: boolean;
  type: TypeEnum;
}>;
type PatchedOrdersRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  /**
   * @maxLength 500
   */
  customer_note: string | null;
  customer: number;
  company: number;
  estimated_completion: string | null;
  order_status: OrderStatusEnum;
  current_hubspot_gate: number | null;
}>;
type PatchedPartsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  part_status: PartStatusEnum;
  order: number;
  part_type: number;
  step: number;
  work_order: number | null;
  sampling_rule: number | null;
  sampling_ruleset: number | null;
  sampling_context: unknown;
}>;
type PatchedProcessWithStepsRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  part_type: number;
  steps: Array<StepRequest>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
}>;
type StepRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  order: number;
  description?: (string | null) | undefined;
  is_last_step?: boolean | undefined;
  process: number;
  part_type: number;
  sampling_required?: boolean | undefined;
  min_sampling_rate?: /**
   * Minimum % of parts that must be sampled at this step
   */
  number | undefined;
};
type PatchedQualityReportsRequest = Partial<{
  step: number | null;
  part: number | null;
  machine: number | null;
  operator: Array<number>;
  sampling_rule: number | null;
  /**
   * @minLength 1
   * @maxLength 50
   */
  sampling_method: string;
  status: StatusEnum;
  /**
   * @maxLength 300
   */
  description: string | null;
  file: number | null;
  errors: Array<number>;
  measurements: Array<MeasurementDefinitionRequest>;
  /**
   * Links to the sampling decision that triggered this inspection
   */
  sampling_audit_log: number | null;
}>;
type PatchedSamplingRuleRequest = Partial<{
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
  ruleset: number;
  created_by: number | null;
  modified_by: number | null;
}>;
type PatchedWorkOrderRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status: WorkorderStatusEnum;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  quantity: number;
  related_order: number | null;
  expected_completion: string | null;
  expected_duration: string | null;
  true_completion: string | null;
  true_duration: string | null;
  /**
   * @maxLength 500
   */
  notes: string | null;
}>;
type ProcessWithStepsRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  name: string;
  is_remanufactured: boolean;
  part_type: number;
  steps: Array<StepRequest>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
};
type QualityReportsRequest = {
  step?: (number | null) | undefined;
  part?: (number | null) | undefined;
  machine?: (number | null) | undefined;
  operator?: Array<number> | undefined;
  sampling_rule?: (number | null) | undefined;
  sampling_method?: /**
   * @minLength 1
   * @maxLength 50
   */
  string | undefined;
  status: StatusEnum;
  description?:
    | /**
     * @maxLength 300
     */
    (string | null)
    | undefined;
  file?: (number | null) | undefined;
  errors?: Array<number> | undefined;
  measurements: Array<MeasurementDefinitionRequest>;
  sampling_audit_log?:
    | /**
     * Links to the sampling decision that triggered this inspection
     */
    (number | null)
    | undefined;
};
type SamplingRuleRequest = {
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
  ruleset: number;
  created_by?: (number | null) | undefined;
  modified_by?: (number | null) | undefined;
};
type SamplingRuleUpdateRequest = {
  rule_type: RuleTypeEnum;
  value?: (number | null) | undefined;
  order: number;
};
type StepSamplingRulesUpdateRequest = {
  rules: Array<SamplingRuleUpdateRequest>;
  fallback_rules?: Array<SamplingRuleUpdateRequest> | undefined;
  fallback_threshold?: number | undefined;
  fallback_duration?: number | undefined;
};
type UserDetail = {
  id: number;
  /**
   * Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
   *
   * @maxLength 150
   * @pattern ^[\w.@+-]+$
   */
  username: string;
  first_name?: /**
   * @maxLength 150
   */
  string | undefined;
  last_name?: /**
   * @maxLength 150
   */
  string | undefined;
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
type WorkOrderRequest = {
  /**
   * @minLength 1
   * @maxLength 50
   */
  ERP_id: string;
  workorder_status?: WorkorderStatusEnum | undefined;
  quantity?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  related_order?: (number | null) | undefined;
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
};

const Company: z.ZodType<Company> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    description: z.string(),
    hubspot_api_id: z.string().max(50),
    user_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const CompanyRequest = z
  .object({
    name: z.string().min(1).max(50),
    description: z.string().min(1),
    hubspot_api_id: z.string().min(1).max(50),
  })
  .passthrough();
const PatchedCompanyRequest = z
  .object({
    name: z.string().min(1).max(50),
    description: z.string().min(1),
    hubspot_api_id: z.string().min(1).max(50),
  })
  .partial()
  .passthrough();
const UserDetail: z.ZodType<UserDetail> = z
  .object({
    id: z.number().int(),
    username: z
      .string()
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
    email: z.string().max(254).email().optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    date_joined: z.string().datetime({ offset: true }),
    parent_company: Company,
  })
  .passthrough();
const UserDetailRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
    email: z.string().max(254).email().optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    parent_company_id: z.number().int().optional(),
  })
  .passthrough();
const PatchedUserDetailRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150),
    last_name: z.string().max(150),
    email: z.string().max(254).email(),
    is_staff: z.boolean(),
    is_active: z.boolean(),
    parent_company_id: z.number().int(),
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
const Documents: z.ZodType<Documents> = z
  .object({
    id: z.number().int(),
    classification: z.union([ClassificationEnum, NullEnum]).nullish(),
    AI_readable: z.boolean().optional(),
    is_image: z.boolean(),
    file_name: z.string().max(50),
    file: z.string().url(),
    file_url: z.string(),
    upload_date: z.string(),
    uploaded_by: z.number().int().nullish(),
    uploaded_by_info: z.object({}).partial().passthrough(),
    content_type: z.number().int().nullish(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullish(),
    content_type_info: z.object({}).partial().passthrough(),
    version: z.number().int().gte(0).lte(32767).optional(),
    access_info: z.object({}).partial().passthrough(),
    auto_properties: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedDocumentsList: z.ZodType<PaginatedDocumentsList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Documents),
  })
  .passthrough();
const DocumentsRequest: z.ZodType<DocumentsRequest> = z
  .object({
    classification: z.union([ClassificationEnum, NullEnum]).nullish(),
    AI_readable: z.boolean().optional(),
    is_image: z.boolean(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullish(),
    content_type: z.number().int().nullish(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullish(),
    version: z.number().int().gte(0).lte(32767).optional(),
  })
  .passthrough();
const PatchedDocumentsRequest: z.ZodType<PatchedDocumentsRequest> = z
  .object({
    classification: z.union([ClassificationEnum, NullEnum]).nullable(),
    AI_readable: z.boolean(),
    is_image: z.boolean(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullable(),
    content_type: z.number().int().nullable(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullable(),
    version: z.number().int().gte(0).lte(32767),
  })
  .partial()
  .passthrough();
const UserSelect: z.ZodType<UserSelect> = z
  .object({
    id: z.number().int(),
    username: z.string(),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
    email: z.string().max(254).email().optional(),
    full_name: z.string(),
    is_active: z.boolean(),
  })
  .passthrough();
const PaginatedUserSelectList: z.ZodType<PaginatedUserSelectList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(UserSelect),
  })
  .passthrough();
const Equipments: z.ZodType<Equipments> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    equipment_type: z.number().int().nullish(),
    equipment_type_name: z.string(),
  })
  .passthrough();
const PaginatedEquipmentsList: z.ZodType<PaginatedEquipmentsList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Equipments),
  })
  .passthrough();
const EquipmentsRequest = z
  .object({
    name: z.string().min(1).max(50),
    equipment_type: z.number().int().nullish(),
  })
  .passthrough();
const EquipmentType: z.ZodType<EquipmentType> = z
  .object({
    id: z.number().int(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    name: z.string().max(50),
  })
  .passthrough();
const PaginatedEquipmentTypeList: z.ZodType<PaginatedEquipmentTypeList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(EquipmentType),
  })
  .passthrough();
const EquipmentTypeRequest = z
  .object({
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    name: z.string().min(1).max(50),
  })
  .passthrough();
const PatchedEquipmentTypeRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    name: z.string().min(1).max(50),
  })
  .partial()
  .passthrough();
const PatchedEquipmentsRequest = z
  .object({
    name: z.string().min(1).max(50),
    equipment_type: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const QualityErrorsList: z.ZodType<QualityErrorsList> = z
  .object({
    id: z.number().int(),
    error_name: z.string().max(50),
    error_example: z.string(),
    part_type: z.number().int().nullish(),
    part_type_name: z.string(),
  })
  .passthrough();
const PaginatedQualityErrorsListList: z.ZodType<PaginatedQualityErrorsListList> =
  z
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
    part_type: z.number().int().nullish(),
  })
  .passthrough();
const PatchedQualityErrorsListRequest = z
  .object({
    error_name: z.string().min(1).max(50),
    error_example: z.string().min(1),
    part_type: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const StatusEnum = z.enum(["PASS", "FAIL", "PENDING"]);
const QualityReports: z.ZodType<QualityReports> = z
  .object({
    id: z.number().int(),
    step: z.number().int().nullish(),
    part: z.number().int().nullish(),
    machine: z.number().int().nullish(),
    operator: z.array(z.number().int()).optional(),
    sampling_rule: z.number().int().nullish(),
    sampling_method: z.string().max(50).optional(),
    status: StatusEnum,
    description: z.string().max(300).nullish(),
    file: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    errors: z.array(z.number().int()).optional(),
    sampling_audit_log: z.number().int().nullish(),
  })
  .passthrough();
const PaginatedQualityReportsList: z.ZodType<PaginatedQualityReportsList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(QualityReports),
  })
  .passthrough();
const TypeEnum = z.enum(["NUMERIC", "PASS_FAIL"]);
const MeasurementDefinitionRequest: z.ZodType<MeasurementDefinitionRequest> = z
  .object({
    label: z.string().min(1).max(100),
    allow_override: z.boolean().optional(),
    allow_remeasure: z.boolean().optional(),
    allow_quarantine: z.boolean().optional(),
    unit: z.string().max(50).optional(),
    require_qa_review: z.boolean().optional(),
    nominal: z.number().nullish(),
    upper_tol: z.number().nullish(),
    lower_tol: z.number().nullish(),
    required: z.boolean().optional(),
    type: TypeEnum,
  })
  .passthrough();
const QualityReportsRequest: z.ZodType<QualityReportsRequest> = z
  .object({
    step: z.number().int().nullish(),
    part: z.number().int().nullish(),
    machine: z.number().int().nullish(),
    operator: z.array(z.number().int()).optional(),
    sampling_rule: z.number().int().nullish(),
    sampling_method: z.string().min(1).max(50).optional(),
    status: StatusEnum,
    description: z.string().max(300).nullish(),
    file: z.number().int().nullish(),
    errors: z.array(z.number().int()).optional(),
    measurements: z.array(MeasurementDefinitionRequest),
    sampling_audit_log: z.number().int().nullish(),
  })
  .passthrough();
const PatchedQualityReportsRequest: z.ZodType<PatchedQualityReportsRequest> = z
  .object({
    step: z.number().int().nullable(),
    part: z.number().int().nullable(),
    machine: z.number().int().nullable(),
    operator: z.array(z.number().int()),
    sampling_rule: z.number().int().nullable(),
    sampling_method: z.string().min(1).max(50),
    status: StatusEnum,
    description: z.string().max(300).nullable(),
    file: z.number().int().nullable(),
    errors: z.array(z.number().int()),
    measurements: z.array(MeasurementDefinitionRequest),
    sampling_audit_log: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const ExternalAPIOrderIdentifier = z
  .object({
    id: z.number().int(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    stage_name: z.string().max(100),
    API_id: z.string().max(50),
  })
  .passthrough();
const ExternalAPIOrderIdentifierRequest = z
  .object({
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    stage_name: z.string().min(1).max(100),
    API_id: z.string().min(1).max(50),
  })
  .passthrough();
const PatchedExternalAPIOrderIdentifierRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    stage_name: z.string().min(1).max(100),
    API_id: z.string().min(1).max(50),
  })
  .partial()
  .passthrough();
const MeasurementDefinition: z.ZodType<MeasurementDefinition> = z
  .object({
    id: z.number().int(),
    label: z.string().max(100),
    step_name: z.string(),
    allow_override: z.boolean().optional(),
    allow_remeasure: z.boolean().optional(),
    allow_quarantine: z.boolean().optional(),
    unit: z.string().max(50).optional(),
    require_qa_review: z.boolean().optional(),
    nominal: z.number().nullish(),
    upper_tol: z.number().nullish(),
    lower_tol: z.number().nullish(),
    required: z.boolean().optional(),
    type: TypeEnum,
    step: z.number().int(),
  })
  .passthrough();
const PaginatedMeasurementDefinitionList: z.ZodType<PaginatedMeasurementDefinitionList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(MeasurementDefinition),
    })
    .passthrough();
const PatchedMeasurementDefinitionRequest: z.ZodType<PatchedMeasurementDefinitionRequest> =
  z
    .object({
      label: z.string().min(1).max(100),
      allow_override: z.boolean(),
      allow_remeasure: z.boolean(),
      allow_quarantine: z.boolean(),
      unit: z.string().max(50),
      require_qa_review: z.boolean(),
      nominal: z.number().nullable(),
      upper_tol: z.number().nullable(),
      lower_tol: z.number().nullable(),
      required: z.boolean(),
      type: TypeEnum,
    })
    .partial()
    .passthrough();
const OrderStatusEnum = z.enum([
  "RFI",
  "PENDING",
  "IN_PROGRESS",
  "COMPLETED",
  "ON_HOLD",
  "CANCELLED",
]);
const Orders: z.ZodType<Orders> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    customer_note: z.string().max(500).nullish(),
    customer: z.number().int(),
    customer_info: UserSelect,
    company: z.number().int(),
    company_info: Company,
    estimated_completion: z.string().nullish(),
    order_status: OrderStatusEnum,
    current_hubspot_gate: z.number().int().nullish(),
    parts_summary: z.object({}).partial().passthrough(),
    process_stages: z.array(z.unknown()),
    customer_first_name: z.string(),
    customer_last_name: z.string(),
    company_name: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedOrdersList: z.ZodType<PaginatedOrdersList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Orders),
  })
  .passthrough();
const OrdersRequest: z.ZodType<OrdersRequest> = z
  .object({
    name: z.string().min(1).max(50),
    customer_note: z.string().max(500).nullish(),
    customer: z.number().int(),
    company: z.number().int(),
    estimated_completion: z.string().nullish(),
    order_status: OrderStatusEnum,
    current_hubspot_gate: z.number().int().nullish(),
  })
  .passthrough();
const PatchedOrdersRequest: z.ZodType<PatchedOrdersRequest> = z
  .object({
    name: z.string().min(1).max(50),
    customer_note: z.string().max(500).nullable(),
    customer: z.number().int(),
    company: z.number().int(),
    estimated_completion: z.string().nullable(),
    order_status: OrderStatusEnum,
    current_hubspot_gate: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const StepIncrementInputRequest = z
  .object({ step_id: z.number().int() })
  .passthrough();
const StepIncrementResponse = z
  .object({ advanced: z.number().int(), total: z.number().int() })
  .passthrough();
const PartStatusEnum = z.enum([
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
const BulkAddPartsInputRequest: z.ZodType<BulkAddPartsInputRequest> = z
  .object({
    part_type: z.number().int(),
    step: z.number().int(),
    quantity: z.number().int(),
    part_status: PartStatusEnum.optional().default("PENDING"),
    work_order: z.number().int().optional(),
    erp_id_start: z.number().int().optional().default(1),
  })
  .passthrough();
const BulkSoftDeleteRequest = z
  .object({
    ids: z.array(z.number().int()),
    reason: z.string().min(1).max(200).optional().default("bulk_admin_delete"),
  })
  .passthrough();
const StepDistributionResponse: z.ZodType<StepDistributionResponse> = z
  .object({ id: z.number().int(), count: z.number().int(), name: z.string() })
  .passthrough();
const PaginatedStepDistributionResponseList: z.ZodType<PaginatedStepDistributionResponseList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(StepDistributionResponse),
    })
    .passthrough();
const PartTypes: z.ZodType<PartTypes> = z
  .object({
    id: z.number().int(),
    previous_version: z.number().int().nullable(),
    previous_version_name: z.string().nullable(),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    name: z.string().max(50),
    ID_prefix: z.string().max(50).nullish(),
    version: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    ERP_id: z.string().max(50).nullish(),
  })
  .passthrough();
const PaginatedPartTypesList: z.ZodType<PaginatedPartTypesList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(PartTypes),
  })
  .passthrough();
const PartTypesRequest = z
  .object({
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullish(),
    version: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    ERP_id: z.string().max(50).nullish(),
  })
  .passthrough();
const PatchedPartTypesRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullable(),
    version: z.number().int().gte(-2147483648).lte(2147483647),
    ERP_id: z.string().max(50).nullable(),
  })
  .partial()
  .passthrough();
const Parts: z.ZodType<Parts> = z
  .object({
    id: z.number().int(),
    ERP_id: z.string().max(50),
    part_status: PartStatusEnum.optional(),
    archived: z.boolean(),
    requires_sampling: z.boolean(),
    order: z.number().int().optional(),
    order_info: z.object({}).partial().passthrough(),
    part_type: z.number().int(),
    part_type_info: z.object({}).partial().passthrough(),
    step: z.number().int(),
    step_info: z.object({}).partial().passthrough(),
    work_order: z.number().int().nullish(),
    work_order_info: z.object({}).partial().passthrough().nullable(),
    sampling_info: z.object({}).partial().passthrough(),
    quality_info: z.object({}).partial().passthrough(),
    sampling_history: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    has_error: z.boolean(),
    part_type_name: z.string(),
    process_name: z.string(),
    order_name: z.string().nullable(),
    step_description: z.string(),
    work_order_erp_id: z.string().nullable(),
    quality_status: z.object({}).partial().passthrough(),
    sampling_rule: z.number().int().nullish(),
    sampling_ruleset: z.number().int().nullish(),
    sampling_context: z.unknown().optional(),
  })
  .passthrough();
const PaginatedPartsList: z.ZodType<PaginatedPartsList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Parts),
  })
  .passthrough();
const PartsRequest: z.ZodType<PartsRequest> = z
  .object({
    ERP_id: z.string().min(1).max(50),
    part_status: PartStatusEnum.optional(),
    order: z.number().int().optional(),
    part_type: z.number().int(),
    step: z.number().int(),
    work_order: z.number().int().nullish(),
    sampling_rule: z.number().int().nullish(),
    sampling_ruleset: z.number().int().nullish(),
    sampling_context: z.unknown().optional(),
  })
  .passthrough();
const PatchedPartsRequest: z.ZodType<PatchedPartsRequest> = z
  .object({
    ERP_id: z.string().min(1).max(50),
    part_status: PartStatusEnum,
    order: z.number().int(),
    part_type: z.number().int(),
    step: z.number().int(),
    work_order: z.number().int().nullable(),
    sampling_rule: z.number().int().nullable(),
    sampling_ruleset: z.number().int().nullable(),
    sampling_context: z.unknown(),
  })
  .partial()
  .passthrough();
const Step: z.ZodType<Step> = z
  .object({
    name: z.string().max(50),
    id: z.number().int(),
    order: z.number().int().gte(-2147483648).lte(2147483647),
    description: z.string().nullish(),
    is_last_step: z.boolean().optional(),
    process: z.number().int(),
    part_type: z.number().int(),
    process_name: z.string(),
    part_type_name: z.string(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
  })
  .passthrough();
const Processes: z.ZodType<Processes> = z
  .object({
    id: z.number().int(),
    part_type_name: z.string(),
    steps: z.array(Step),
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    name: z.string().max(50),
    is_remanufactured: z.boolean(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    version: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    part_type: z.number().int(),
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const PaginatedProcessesList: z.ZodType<PaginatedProcessesList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Processes),
  })
  .passthrough();
const ProcessesRequest = z
  .object({
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    version: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    part_type: z.number().int(),
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const PatchedProcessesRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    version: z.number().int().gte(-2147483648).lte(2147483647),
    part_type: z.number().int(),
    previous_version: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const ProcessWithSteps: z.ZodType<ProcessWithSteps> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    is_remanufactured: z.boolean(),
    part_type: z.number().int(),
    steps: z.array(Step),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
  })
  .passthrough();
const PaginatedProcessWithStepsList: z.ZodType<PaginatedProcessWithStepsList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(ProcessWithSteps),
    })
    .passthrough();
const StepRequest: z.ZodType<StepRequest> = z
  .object({
    name: z.string().min(1).max(50),
    order: z.number().int().gte(-2147483648).lte(2147483647),
    description: z.string().nullish(),
    is_last_step: z.boolean().optional(),
    process: z.number().int(),
    part_type: z.number().int(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
  })
  .passthrough();
const ProcessWithStepsRequest: z.ZodType<ProcessWithStepsRequest> = z
  .object({
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    part_type: z.number().int(),
    steps: z.array(StepRequest),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
  })
  .passthrough();
const PatchedProcessWithStepsRequest: z.ZodType<PatchedProcessWithStepsRequest> =
  z
    .object({
      name: z.string().min(1).max(50),
      is_remanufactured: z.boolean(),
      part_type: z.number().int(),
      steps: z.array(StepRequest),
      num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    })
    .partial()
    .passthrough();
const SamplingRuleSet: z.ZodType<SamplingRuleSet> = z
  .object({
    id: z.number().int(),
    name: z.string().max(100),
    origin: z.string().max(100).optional(),
    active: z.boolean().optional(),
    version: z.number().int().gte(0).lte(2147483647).optional().default(1),
    is_fallback: z.boolean().optional().default(false),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullish(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullish(),
    archived: z.boolean(),
    part_type: z.number().int(),
    part_type_info: z.object({}).partial().passthrough(),
    process: z.number().int(),
    process_info: z.object({}).partial().passthrough(),
    step: z.number().int(),
    step_info: z.object({}).partial().passthrough(),
    rules: z.array(z.unknown()),
    created_by: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    modified_by: z.number().int().nullish(),
    modified_at: z.string().datetime({ offset: true }),
    part_type_name: z.string(),
    process_name: z.string(),
  })
  .passthrough();
const PaginatedSamplingRuleSetList: z.ZodType<PaginatedSamplingRuleSetList> = z
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
    version: z.number().int().gte(0).lte(2147483647).optional().default(1),
    is_fallback: z.boolean().optional().default(false),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullish(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullish(),
    part_type: z.number().int(),
    process: z.number().int(),
    step: z.number().int(),
    created_by: z.number().int().nullish(),
    modified_by: z.number().int().nullish(),
  })
  .passthrough();
const PatchedSamplingRuleSetRequest = z
  .object({
    name: z.string().min(1).max(100),
    origin: z.string().max(100),
    active: z.boolean(),
    version: z.number().int().gte(0).lte(2147483647).default(1),
    is_fallback: z.boolean().default(false),
    fallback_threshold: z.number().int().gte(0).lte(2147483647).nullable(),
    fallback_duration: z.number().int().gte(0).lte(2147483647).nullable(),
    part_type: z.number().int(),
    process: z.number().int(),
    step: z.number().int(),
    created_by: z.number().int().nullable(),
    modified_by: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const RuleTypeEnum = z.enum([
  "every_nth_part",
  "percentage",
  "random",
  "first_n_parts",
  "last_n_parts",
]);
const SamplingRule: z.ZodType<SamplingRule> = z
  .object({
    id: z.number().int(),
    rule_type: RuleTypeEnum,
    rule_type_display: z.string(),
    value: z.number().int().gte(0).lte(2147483647).nullish(),
    order: z.number().int().gte(0).lte(2147483647).optional(),
    algorithm_description: z.string().optional(),
    last_validated: z.string().datetime({ offset: true }).nullish(),
    ruleset: z.number().int(),
    ruleset_info: z.object({}).partial().passthrough(),
    created_by: z.number().int().nullish(),
    created_at: z.string().datetime({ offset: true }),
    modified_by: z.number().int().nullish(),
    modified_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
    ruletype_name: z.string(),
    ruleset_name: z.string(),
  })
  .passthrough();
const PaginatedSamplingRuleList: z.ZodType<PaginatedSamplingRuleList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(SamplingRule),
  })
  .passthrough();
const SamplingRuleRequest: z.ZodType<SamplingRuleRequest> = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().gte(0).lte(2147483647).nullish(),
    order: z.number().int().gte(0).lte(2147483647).optional(),
    algorithm_description: z.string().min(1).optional(),
    last_validated: z.string().datetime({ offset: true }).nullish(),
    ruleset: z.number().int(),
    created_by: z.number().int().nullish(),
    modified_by: z.number().int().nullish(),
  })
  .passthrough();
const PatchedSamplingRuleRequest: z.ZodType<PatchedSamplingRuleRequest> = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().gte(0).lte(2147483647).nullable(),
    order: z.number().int().gte(0).lte(2147483647),
    algorithm_description: z.string().min(1),
    last_validated: z.string().datetime({ offset: true }).nullable(),
    ruleset: z.number().int(),
    created_by: z.number().int().nullable(),
    modified_by: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const Steps: z.ZodType<Steps> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    order: z.number().int().gte(-2147483648).lte(2147483647),
    expected_duration: z.string().nullish(),
    description: z.string().nullish(),
    is_last_step: z.boolean().optional(),
    block_on_quarantine: z.boolean().optional(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    pass_threshold: z.number().optional(),
    process: z.number().int(),
    part_type: z.number().int(),
    process_info: z.object({}).partial().passthrough(),
    part_type_info: z.object({}).partial().passthrough(),
    resolved_sampling_rules: z.unknown(),
    sampling_coverage: z.object({}).partial().passthrough(),
    process_name: z.string(),
    part_type_name: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedStepsList: z.ZodType<PaginatedStepsList> = z
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
    order: z.number().int().gte(-2147483648).lte(2147483647),
    expected_duration: z.string().nullish(),
    description: z.string().nullish(),
    is_last_step: z.boolean().optional(),
    block_on_quarantine: z.boolean().optional(),
    requires_qa_signoff: z.boolean().optional(),
    sampling_required: z.boolean().optional(),
    min_sampling_rate: z.number().optional(),
    pass_threshold: z.number().optional(),
    process: z.number().int(),
    part_type: z.number().int(),
  })
  .passthrough();
const PatchedStepsRequest = z
  .object({
    name: z.string().min(1).max(50),
    order: z.number().int().gte(-2147483648).lte(2147483647),
    expected_duration: z.string().nullable(),
    description: z.string().nullable(),
    is_last_step: z.boolean(),
    block_on_quarantine: z.boolean(),
    requires_qa_signoff: z.boolean(),
    sampling_required: z.boolean(),
    min_sampling_rate: z.number(),
    pass_threshold: z.number(),
    process: z.number().int(),
    part_type: z.number().int(),
  })
  .partial()
  .passthrough();
const SamplingRuleUpdateRequest: z.ZodType<SamplingRuleUpdateRequest> = z
  .object({
    rule_type: RuleTypeEnum,
    value: z.number().int().nullish(),
    order: z.number().int(),
  })
  .passthrough();
const StepSamplingRulesUpdateRequest: z.ZodType<StepSamplingRulesUpdateRequest> =
  z
    .object({
      rules: z.array(SamplingRuleUpdateRequest),
      fallback_rules: z.array(SamplingRuleUpdateRequest).optional(),
      fallback_threshold: z.number().int().optional(),
      fallback_duration: z.number().int().optional(),
    })
    .passthrough();
const WorkorderStatusEnum = z.enum([
  "PENDING",
  "IN_PROGRESS",
  "COMPLETED",
  "ON_HOLD",
  "CANCELLED",
  "WAITING_FOR_OPERATOR",
]);
const WorkOrder: z.ZodType<WorkOrder> = z
  .object({
    id: z.number().int(),
    ERP_id: z.string().max(50),
    workorder_status: WorkorderStatusEnum.optional(),
    quantity: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    related_order: z.number().int().nullish(),
    related_order_info: z.object({}).partial().passthrough(),
    related_order_detail: Orders,
    expected_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_completion: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
    parts_summary: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
  })
  .passthrough();
const PaginatedWorkOrderList: z.ZodType<PaginatedWorkOrderList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(WorkOrder),
  })
  .passthrough();
const WorkOrderRequest: z.ZodType<WorkOrderRequest> = z
  .object({
    ERP_id: z.string().min(1).max(50),
    workorder_status: WorkorderStatusEnum.optional(),
    quantity: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    related_order: z.number().int().nullish(),
    expected_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_completion: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
  })
  .passthrough();
const PatchedWorkOrderRequest: z.ZodType<PatchedWorkOrderRequest> = z
  .object({
    ERP_id: z.string().min(1).max(50),
    workorder_status: WorkorderStatusEnum,
    quantity: z.number().int().gte(-2147483648).lte(2147483647),
    related_order: z.number().int().nullable(),
    expected_completion: z.string().nullable(),
    expected_duration: z.string().nullable(),
    true_completion: z.string().nullable(),
    true_duration: z.string().nullable(),
    notes: z.string().max(500).nullable(),
  })
  .partial()
  .passthrough();
const ActionEnum = z.union([
  z.literal(0),
  z.literal(1),
  z.literal(2),
  z.literal(3),
]);
const AuditLog: z.ZodType<AuditLog> = z
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
const PaginatedAuditLogList: z.ZodType<PaginatedAuditLogList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(AuditLog),
  })
  .passthrough();
const ContentType: z.ZodType<ContentType> = z
  .object({
    id: z.number().int(),
    app_label: z.string().max(100),
    model: z.string().max(100),
  })
  .passthrough();
const PaginatedContentTypeList: z.ZodType<PaginatedContentTypeList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(ContentType),
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
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
  })
  .passthrough();
const UserDetailsRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
  })
  .passthrough();
const PatchedUserDetailsRequest = z
  .object({
    username: z
      .string()
      .min(1)
      .max(150)
      .regex(/^[\w.@+-]+$/),
    first_name: z.string().max(150),
    last_name: z.string().max(150),
  })
  .partial()
  .passthrough();

export const schemas = {
  Company,
  CompanyRequest,
  PatchedCompanyRequest,
  UserDetail,
  UserDetailRequest,
  PatchedUserDetailRequest,
  ClassificationEnum,
  NullEnum,
  Documents,
  PaginatedDocumentsList,
  DocumentsRequest,
  PatchedDocumentsRequest,
  UserSelect,
  PaginatedUserSelectList,
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
  StatusEnum,
  QualityReports,
  PaginatedQualityReportsList,
  TypeEnum,
  MeasurementDefinitionRequest,
  QualityReportsRequest,
  PatchedQualityReportsRequest,
  ExternalAPIOrderIdentifier,
  ExternalAPIOrderIdentifierRequest,
  PatchedExternalAPIOrderIdentifierRequest,
  MeasurementDefinition,
  PaginatedMeasurementDefinitionList,
  PatchedMeasurementDefinitionRequest,
  OrderStatusEnum,
  Orders,
  PaginatedOrdersList,
  OrdersRequest,
  PatchedOrdersRequest,
  StepIncrementInputRequest,
  StepIncrementResponse,
  PartStatusEnum,
  BulkAddPartsInputRequest,
  BulkSoftDeleteRequest,
  StepDistributionResponse,
  PaginatedStepDistributionResponseList,
  PartTypes,
  PaginatedPartTypesList,
  PartTypesRequest,
  PatchedPartTypesRequest,
  Parts,
  PaginatedPartsList,
  PartsRequest,
  PatchedPartsRequest,
  Step,
  Processes,
  PaginatedProcessesList,
  ProcessesRequest,
  PatchedProcessesRequest,
  ProcessWithSteps,
  PaginatedProcessWithStepsList,
  StepRequest,
  ProcessWithStepsRequest,
  PatchedProcessWithStepsRequest,
  SamplingRuleSet,
  PaginatedSamplingRuleSetList,
  SamplingRuleSetRequest,
  PatchedSamplingRuleSetRequest,
  RuleTypeEnum,
  SamplingRule,
  PaginatedSamplingRuleList,
  SamplingRuleRequest,
  PatchedSamplingRuleRequest,
  Steps,
  PaginatedStepsList,
  StepsRequest,
  PatchedStepsRequest,
  SamplingRuleUpdateRequest,
  StepSamplingRulesUpdateRequest,
  WorkorderStatusEnum,
  WorkOrder,
  PaginatedWorkOrderList,
  WorkOrderRequest,
  PatchedWorkOrderRequest,
  ActionEnum,
  AuditLog,
  PaginatedAuditLogList,
  ContentType,
  PaginatedContentTypeList,
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
};

const endpoints = makeApi([
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
    path: "/api/Companies/",
    alias: "api_Companies_list",
    requestFormat: "json",
    parameters: [
      {
        name: "ordering",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: z.array(Company),
  },
  {
    method: "post",
    path: "/api/Companies/",
    alias: "api_Companies_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Company,
  },
  {
    method: "put",
    path: "/api/Companies/:id/",
    alias: "api_Companies_update",
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
        schema: z.number().int(),
      },
    ],
    response: Company,
  },
  {
    method: "patch",
    path: "/api/Companies/:id/",
    alias: "api_Companies_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: Company,
  },
  {
    method: "delete",
    path: "/api/Companies/:id/",
    alias: "api_Companies_destroy",
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
    path: "/api/content-types/",
    alias: "api_content_types_list",
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
    response: PaginatedContentTypeList,
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
    path: "/api/Customers/",
    alias: "api_Customers_list",
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
    path: "/api/Documents/",
    alias: "api_Documents_list",
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
    response: PaginatedDocumentsList,
  },
  {
    method: "post",
    path: "/api/Documents/",
    alias: "api_Documents_create",
    requestFormat: "json",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Documents,
  },
  {
    method: "put",
    path: "/api/Documents/:id/",
    alias: "api_Documents_update",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Documents,
  },
  {
    method: "patch",
    path: "/api/Documents/:id/",
    alias: "api_Documents_partial_update",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: PatchedDocumentsRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Documents,
  },
  {
    method: "delete",
    path: "/api/Documents/:id/",
    alias: "api_Documents_destroy",
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
    path: "/api/Employees-Options/",
    alias: "api_Employees_Options_list",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Equipments,
  },
  {
    method: "get",
    path: "/api/Equipment-types/",
    alias: "api_Equipment_types_list",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "put",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_update",
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
        schema: z.number().int(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "patch",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: EquipmentType,
  },
  {
    method: "delete",
    path: "/api/Equipment-types/:id/",
    alias: "api_Equipment_types_destroy",
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
    path: "/api/Equipment/",
    alias: "api_Equipment_list",
    requestFormat: "json",
    parameters: [
      {
        name: "equipment_type",
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
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedEquipmentsList,
  },
  {
    method: "post",
    path: "/api/Equipment/",
    alias: "api_Equipment_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Equipments,
  },
  {
    method: "put",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_update",
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
        schema: z.number().int(),
      },
    ],
    response: Equipments,
  },
  {
    method: "patch",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: Equipments,
  },
  {
    method: "delete",
    path: "/api/Equipment/:id/",
    alias: "api_Equipment_destroy",
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
    path: "/api/Error-types/",
    alias: "api_Error_types_list",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "put",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_update",
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
        schema: z.number().int(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "patch",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: QualityErrorsList,
  },
  {
    method: "delete",
    path: "/api/Error-types/:id/",
    alias: "api_Error_types_destroy",
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
    path: "/api/ErrorReports/",
    alias: "api_ErrorReports_list",
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
    response: PaginatedQualityReportsList,
  },
  {
    method: "post",
    path: "/api/ErrorReports/",
    alias: "api_ErrorReports_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "put",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_update",
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
        schema: z.number().int(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "patch",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: QualityReports,
  },
  {
    method: "delete",
    path: "/api/ErrorReports/:id/",
    alias: "api_ErrorReports_destroy",
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
    path: "/api/HubspotGates/",
    alias: "api_HubspotGates_list",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "put",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_update",
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
        schema: z.number().int(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "patch",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: ExternalAPIOrderIdentifier,
  },
  {
    method: "delete",
    path: "/api/HubspotGates/:id/",
    alias: "api_HubspotGates_destroy",
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
    path: "/api/MeasurementDefinitions/",
    alias: "api_MeasurementDefinitions_list",
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
        schema: z.number().int().optional(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "put",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_update",
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
        schema: z.number().int(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "patch",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: MeasurementDefinition,
  },
  {
    method: "delete",
    path: "/api/MeasurementDefinitions/:id/",
    alias: "api_MeasurementDefinitions_destroy",
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
    path: "/api/Orders/",
    alias: "api_Orders_list",
    requestFormat: "json",
    parameters: [
      {
        name: "archived",
        type: "Query",
        schema: z.boolean().optional(),
      },
      {
        name: "company",
        type: "Query",
        schema: z.number().int().optional(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "put",
    path: "/api/Orders/:id/",
    alias: "api_Orders_update",
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
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "patch",
    path: "/api/Orders/:id/",
    alias: "api_Orders_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "delete",
    path: "/api/Orders/:id/",
    alias: "api_Orders_destroy",
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
    path: "/api/Orders/:id/increment-step/",
    alias: "api_Orders_increment_step_create",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ step_id: z.number().int() }).passthrough(),
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: StepIncrementResponse,
  },
  {
    method: "post",
    path: "/api/Orders/:id/parts/bulk-add/",
    alias: "api_Orders_parts_bulk_add_create",
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
        schema: z.number().int(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/Orders/:id/parts/bulk-remove/",
    alias: "api_Orders_parts_bulk_remove_create",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BulkSoftDeleteRequest,
      },
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/Orders/:id/step-distribution/",
    alias: "api_Orders_step_distribution_list",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
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
        schema: z.number().int(),
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
    path: "/api/Parts/",
    alias: "api_Parts_list",
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
        schema: z.number().int().optional(),
      },
      {
        name: "work_order",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PaginatedPartsList,
  },
  {
    method: "post",
    path: "/api/Parts/",
    alias: "api_Parts_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
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
    path: "/api/PartTypes/",
    alias: "api_PartTypes_list",
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
        schema: z.number().int().optional(),
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
        schema: z.number().int().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "get",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_retrieve",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "put",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_update",
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "patch",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_partial_update",
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: PartTypes,
  },
  {
    method: "delete",
    path: "/api/PartTypes/:id/",
    alias: "api_PartTypes_destroy",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/",
    alias: "api_Processes_with_steps_list",
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
    response: PaginatedProcessWithStepsList,
  },
  {
    method: "post",
    path: "/api/Processes_with_steps/",
    alias: "api_Processes_with_steps_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "put",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_update",
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
        schema: z.number().int(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "patch",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: ProcessWithSteps,
  },
  {
    method: "delete",
    path: "/api/Processes_with_steps/:id/",
    alias: "api_Processes_with_steps_destroy",
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
    path: "/api/Processes/",
    alias: "api_Processes_list",
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
    ],
    response: PaginatedProcessesList,
  },
  {
    method: "post",
    path: "/api/Processes/",
    alias: "api_Processes_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Processes,
  },
  {
    method: "put",
    path: "/api/Processes/:id/",
    alias: "api_Processes_update",
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
        schema: z.number().int(),
      },
    ],
    response: Processes,
  },
  {
    method: "patch",
    path: "/api/Processes/:id/",
    alias: "api_Processes_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: Processes,
  },
  {
    method: "delete",
    path: "/api/Processes/:id/",
    alias: "api_Processes_destroy",
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
    path: "/api/Sampling-rule-sets/",
    alias: "api_Sampling_rule_sets_list",
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
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
      {
        name: "step",
        type: "Query",
        schema: z.number().int().optional(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "put",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_update",
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
        schema: z.number().int(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "patch",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: SamplingRuleSet,
  },
  {
    method: "delete",
    path: "/api/Sampling-rule-sets/:id/",
    alias: "api_Sampling_rule_sets_destroy",
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
    path: "/api/Sampling-rules/",
    alias: "api_Sampling_rules_list",
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
        schema: z.number().int().optional(),
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "put",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_update",
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
        schema: z.number().int(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "patch",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: SamplingRule,
  },
  {
    method: "delete",
    path: "/api/Sampling-rules/:id/",
    alias: "api_Sampling_rules_destroy",
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
    path: "/api/Steps/",
    alias: "api_Steps_list",
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
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process__part_type",
        type: "Query",
        schema: z.number().int().optional(),
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
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "get",
    path: "/api/Steps/:id/",
    alias: "api_Steps_retrieve",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "put",
    path: "/api/Steps/:id/",
    alias: "api_Steps_update",
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "patch",
    path: "/api/Steps/:id/",
    alias: "api_Steps_partial_update",
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "delete",
    path: "/api/Steps/:id/",
    alias: "api_Steps_destroy",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
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
        schema: z.number().int(),
      },
      {
        name: "part_type",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: Steps,
  },
  {
    method: "get",
    path: "/api/TrackerOrders/",
    alias: "api_TrackerOrders_list",
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
    response: PaginatedOrdersList,
  },
  {
    method: "post",
    path: "/api/TrackerOrders/",
    alias: "api_TrackerOrders_create",
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
    path: "/api/TrackerOrders/:id/",
    alias: "api_TrackerOrders_retrieve",
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "put",
    path: "/api/TrackerOrders/:id/",
    alias: "api_TrackerOrders_update",
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
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "patch",
    path: "/api/TrackerOrders/:id/",
    alias: "api_TrackerOrders_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: Orders,
  },
  {
    method: "delete",
    path: "/api/TrackerOrders/:id/",
    alias: "api_TrackerOrders_destroy",
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
    path: "/api/WorkOrders/",
    alias: "api_WorkOrders_list",
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
        name: "related_order",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "search",
        type: "Query",
        schema: z.string().optional(),
      },
    ],
    response: PaginatedWorkOrderList,
  },
  {
    method: "post",
    path: "/api/WorkOrders/",
    alias: "api_WorkOrders_create",
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
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "put",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_update",
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
        schema: z.number().int(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "patch",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_partial_update",
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
        schema: z.number().int(),
      },
    ],
    response: WorkOrder,
  },
  {
    method: "delete",
    path: "/api/WorkOrders/:id/",
    alias: "api_WorkOrders_destroy",
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
    path: "/api/WorkOrders/upload_csv/",
    alias: "api_WorkOrders_upload_csv_create",
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
    ],
    response: z.object({}).partial().passthrough(),
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
    description: `Reads and updates UserModel fields
Accepts GET, PUT, PATCH methods.

Default accepted fields: username, first_name, last_name
Default display fields: pk, username, email, first_name, last_name
Read-only fields: pk, email

Returns UserModel fields.`,
    requestFormat: "json",
    response: UserDetails,
  },
  {
    method: "put",
    path: "/auth/user/",
    alias: "auth_user_update",
    description: `Reads and updates UserModel fields
Accepts GET, PUT, PATCH methods.

Default accepted fields: username, first_name, last_name
Default display fields: pk, username, email, first_name, last_name
Read-only fields: pk, email

Returns UserModel fields.`,
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
    description: `Reads and updates UserModel fields
Accepts GET, PUT, PATCH methods.

Default accepted fields: username, first_name, last_name
Default display fields: pk, username, email, first_name, last_name
Read-only fields: pk, email

Returns UserModel fields.`,
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
]);

export const api = new Zodios(endpoints, {
  axiosConfig: {
    paramsSerializer: (params) =>
      qs.stringify(params, { arrayFormat: "repeat" }),
  },
});

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, {
    axiosConfig: {
      ...options?.axiosConfig,
      paramsSerializer: (params) =>
        qs.stringify(params, { arrayFormat: "repeat" }),
    },
    ...options,
  });
}
