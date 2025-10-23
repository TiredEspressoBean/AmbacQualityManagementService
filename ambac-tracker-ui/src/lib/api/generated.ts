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
   * @maximum 2147483647
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
     * ID of the object this document relates to
     *
     * @minimum 0
     * @maximum 9223372036854776000
     */
    (number | null)
    | undefined;
  version?: /**
   * @minimum 0
   * @maximum 2147483647
   */
  number | undefined;
};
type HeatMapAnnotations = {
  id: number;
  model: number;
  model_display: string;
  part: number;
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
  severity?: (SeverityEnum | BlankEnum | NullEnum | null) | undefined;
  notes?: string | undefined;
  created_by: number | null;
  created_by_display: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
  deleted_at: string | null;
};
type SeverityEnum =
  /**
   * * `low` - Low
   * `medium` - Medium
   * `high` - High
   * `critical` - Critical
   *
   * @enum low, medium, high, critical
   */
  "low" | "medium" | "high" | "critical";
type BlankEnum =
  /**
   * @enum
   */
  unknown;
type HeatMapAnnotationsRequest = {
  model: number;
  part: number;
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
  severity?: (SeverityEnum | BlankEnum | NullEnum | null) | undefined;
  notes?: string | undefined;
};
type MeasurementDefinition = {
  id: number;
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
};
type MeasurementResult = {
  report: string;
  definition: number;
  value_numeric?: (number | null) | undefined;
  value_pass_fail?:
    | (ValuePassFailEnum | BlankEnum | NullEnum | null)
    | undefined;
  is_within_spec: boolean;
  created_by: number;
};
type ValuePassFailEnum =
  /**
   * * `PASS` - Pass
   * `FAIL` - Fail
   *
   * @enum PASS, FAIL
   */
  "PASS" | "FAIL";
type MeasurementResultRequest = {
  definition: number;
  value_numeric?: (number | null) | undefined;
  value_pass_fail?:
    | (ValuePassFailEnum | BlankEnum | NullEnum | null)
    | undefined;
};
type NotificationPreference = {
  id: number;
  notification_type: NotificationTypeEnum;
  notification_type_display: string;
  channel_type?: ChannelTypeEnum | undefined;
  channel_type_display: string;
  status: NotificationPreferenceStatusEnum;
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
type NotificationTypeEnum =
  /**
   * * `WEEKLY_REPORT` - Weekly Order Report
   * `CAPA_REMINDER` - CAPA Reminder
   *
   * @enum WEEKLY_REPORT, CAPA_REMINDER
   */
  "WEEKLY_REPORT" | "CAPA_REMINDER";
type ChannelTypeEnum =
  /**
   * * `email` - Email
   * `in_app` - In-App Notification
   * `sms` - SMS
   *
   * @enum email, in_app, sms
   */
  "email" | "in_app" | "sms";
type NotificationPreferenceStatusEnum =
  /**
   * * `pending` - Pending
   * `sent` - Sent
   * `failed` - Failed
   * `cancelled` - Cancelled
   *
   * @enum pending, sent, failed, cancelled
   */
  "pending" | "sent" | "failed" | "cancelled";
type NotificationSchedule = {
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
type IntervalTypeEnum =
  /**
   * * `fixed` - fixed
   * `deadline_based` - deadline_based
   *
   * @enum fixed, deadline_based
   */
  "fixed" | "deadline_based";
type NotificationPreferenceRequest = {
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
type NotificationScheduleRequest = {
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
type Orders = {
  id: number;
  /**
   * @maxLength 200
   */
  name: string;
  customer_note?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  customer?: (number | null) | undefined;
  customer_info: UserSelect;
  company?: (number | null) | undefined;
  company_info: Company;
  estimated_completion?: (string | null) | undefined;
  order_status: OrderStatusEnum;
  current_hubspot_gate?: (number | null) | undefined;
  parts_summary: {};
  process_stages: Array<unknown>;
  gate_info: {};
  customer_first_name: string | null;
  customer_last_name: string | null;
  company_name: string | null;
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
   * @maxLength 200
   */
  name: string;
  customer_note?:
    | /**
     * @maxLength 500
     */
    (string | null)
    | undefined;
  customer?: (number | null) | undefined;
  company?: (number | null) | undefined;
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
type PaginatedCompanyList = {
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
  previous_version?: (number | null) | undefined;
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
type PaginatedGroupList = {
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
type Group = {
  id: number;
  /**
   * @maxLength 150
   */
  name: string;
};
type PaginatedHeatMapAnnotationsList = {
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
type PaginatedNotificationPreferenceList = {
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
  previous_version?: (number | null) | undefined;
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
  is_from_batch_process: boolean;
  sampling_rule?: (number | null) | undefined;
  sampling_ruleset?: (number | null) | undefined;
  sampling_context?: unknown | undefined;
  process: number;
  total_rework_count: number;
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
  is_remanufactured?: boolean | undefined;
  part_type: number;
  steps: Array<Step>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
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
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
  previous_version?: (number | null) | undefined;
  part_type: number;
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
  status: QualityReportsStatusEnum;
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
type QualityReportsStatusEnum =
  /**
   * * `PASS` - Pass
   * `FAIL` - Fail
   * `PENDING` - Pending
   *
   * @enum PASS, FAIL, PENDING
   */
  "PASS" | "FAIL" | "PENDING";
type PaginatedQuarantineDispositionList = {
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
type QuarantineDisposition = {
  id: number;
  disposition_number: string;
  current_state?: CurrentStateEnum | undefined;
  disposition_type?: (DispositionTypeEnum | BlankEnum) | undefined;
  assigned_to?: (number | null) | undefined;
  description?: string | undefined;
  resolution_notes?: string | undefined;
  resolution_completed?: boolean | undefined;
  resolution_completed_by?: (number | null) | undefined;
  resolution_completed_by_name: string;
  resolution_completed_at?: (string | null) | undefined;
  part?: (number | null) | undefined;
  step?: (number | null) | undefined;
  step_info: {};
  rework_attempt_at_step?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  rework_limit_exceeded: boolean;
  quality_reports: Array<number>;
  assignee_name: string;
  choices_data: {};
};
type CurrentStateEnum =
  /**
   * * `OPEN` - Open
   * `IN_PROGRESS` - In Progress
   * `CLOSED` - Closed
   *
   * @enum OPEN, IN_PROGRESS, CLOSED
   */
  "OPEN" | "IN_PROGRESS" | "CLOSED";
type DispositionTypeEnum =
  /**
   * * `REWORK` - Rework
   * `SCRAP` - Scrap
   * `USE_AS_IS` - Use As Is
   * `RETURN_TO_SUPPLIER` - Return to Supplier
   *
   * @enum REWORK, SCRAP, USE_AS_IS, RETURN_TO_SUPPLIER
   */
  "REWORK" | "SCRAP" | "USE_AS_IS" | "RETURN_TO_SUPPLIER";
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
  updated_at: string;
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
  updated_at: string;
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
type PaginatedThreeDModelList = {
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
type ThreeDModel = {
  id: number;
  /**
   * @maxLength 255
   */
  name: string;
  file: string;
  part_type?: (number | null) | undefined;
  part_type_display: string;
  step?:
    | /**
     * Optional: Link to specific step if this shows intermediate state
     */
    (number | null)
    | undefined;
  step_display: string;
  uploaded_at: string;
  /**
   * e.g., glb, gltf, obj
   */
  file_type: string;
  annotation_count: number;
  created_at: string;
  updated_at: string;
  archived: boolean;
  deleted_at: string | null;
};
type PaginatedUserInvitationList = {
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
type UserInvitation = {
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
type PaginatedUserList = {
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
type User = {
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
  groups: Array<Group>;
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
  is_batch_work_order: boolean;
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
   * ID of the object this document relates to
   *
   * @minimum 0
   * @maximum 9223372036854776000
   */
  object_id: number | null;
  /**
   * @minimum 0
   * @maximum 2147483647
   */
  version: number;
}>;
type PatchedHeatMapAnnotationsRequest = Partial<{
  model: number;
  part: number;
  position_x: number;
  position_y: number;
  position_z: number;
  measurement_value: number | null;
  /**
   * @maxLength 255
   */
  defect_type: string | null;
  severity: SeverityEnum | BlankEnum | NullEnum | null;
  notes: string;
}>;
type PatchedMeasurementDefinitionRequest = Partial<{
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
}>;
type PatchedNotificationPreferenceRequest = Partial<{
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
type PatchedOrdersRequest = Partial<{
  /**
   * @minLength 1
   * @maxLength 200
   */
  name: string;
  /**
   * @maxLength 500
   */
  customer_note: string | null;
  customer: number | null;
  company: number | null;
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
  /**
   * If True, UI treats work order parts as a batch unit
   */
  is_batch_process: boolean;
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
  status: QualityReportsStatusEnum;
  /**
   * @maxLength 300
   */
  description: string | null;
  file: number | null;
  errors: Array<number>;
  measurements: Array<MeasurementResultRequest>;
  /**
   * Links to the sampling decision that triggered this inspection
   */
  sampling_audit_log: number | null;
}>;
type PatchedQuarantineDispositionRequest = Partial<{
  current_state: CurrentStateEnum;
  disposition_type: DispositionTypeEnum | BlankEnum;
  assigned_to: number | null;
  description: string;
  resolution_notes: string;
  resolution_completed: boolean;
  resolution_completed_by: number | null;
  resolution_completed_at: string | null;
  part: number | null;
  step: number | null;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  rework_attempt_at_step: number;
  quality_reports: Array<number>;
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
  is_remanufactured?: boolean | undefined;
  part_type: number;
  steps: Array<StepRequest>;
  /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  num_steps: number;
  is_batch_process?: /**
   * If True, UI treats work order parts as a batch unit
   */
  boolean | undefined;
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
  status: QualityReportsStatusEnum;
  description?:
    | /**
     * @maxLength 300
     */
    (string | null)
    | undefined;
  file?: (number | null) | undefined;
  errors?: Array<number> | undefined;
  measurements: Array<MeasurementResultRequest>;
  sampling_audit_log?:
    | /**
     * Links to the sampling decision that triggered this inspection
     */
    (number | null)
    | undefined;
};
type QuarantineDispositionRequest = {
  current_state?: CurrentStateEnum | undefined;
  disposition_type?: (DispositionTypeEnum | BlankEnum) | undefined;
  assigned_to?: (number | null) | undefined;
  description?: string | undefined;
  resolution_notes?: string | undefined;
  resolution_completed?: boolean | undefined;
  resolution_completed_by?: (number | null) | undefined;
  resolution_completed_at?: (string | null) | undefined;
  part?: (number | null) | undefined;
  step?: (number | null) | undefined;
  rework_attempt_at_step?: /**
   * @minimum -2147483648
   * @maximum 2147483647
   */
  number | undefined;
  quality_reports: Array<number>;
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
const PaginatedCompanyList: z.ZodType<PaginatedCompanyList> = z
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
    first_name: z.string().max(150).nullable(),
    last_name: z.string().max(150).nullable(),
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
    ai_readable: z.boolean().optional(),
    is_image: z.boolean().optional(),
    file_name: z.string().max(50),
    file: z.string().url(),
    file_url: z.string(),
    upload_date: z.string(),
    uploaded_by: z.number().int().nullish(),
    uploaded_by_info: z.object({}).partial().passthrough(),
    content_type: z.number().int().nullish(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullish(),
    content_type_info: z.object({}).partial().passthrough(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
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
    ai_readable: z.boolean().optional(),
    is_image: z.boolean().optional(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullish(),
    content_type: z.number().int().nullish(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullish(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
  })
  .passthrough();
const PatchedDocumentsRequest: z.ZodType<PatchedDocumentsRequest> = z
  .object({
    classification: z.union([ClassificationEnum, NullEnum]).nullable(),
    ai_readable: z.boolean(),
    is_image: z.boolean(),
    file_name: z.string().min(1).max(50),
    file: z.instanceof(File),
    uploaded_by: z.number().int().nullable(),
    content_type: z.number().int().nullable(),
    object_id: z.number().int().gte(0).lte(9223372036854776000).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
  })
  .partial()
  .passthrough();
const UserSelect: z.ZodType<UserSelect> = z
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    previous_version: z.number().int().nullish(),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const PatchedEquipmentTypeRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    previous_version: z.number().int().nullable(),
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
const QualityReportsStatusEnum = z.enum(["PASS", "FAIL", "PENDING"]);
const QualityReports: z.ZodType<QualityReports> = z
  .object({
    id: z.number().int(),
    step: z.number().int().nullish(),
    part: z.number().int().nullish(),
    machine: z.number().int().nullish(),
    operator: z.array(z.number().int()).optional(),
    sampling_rule: z.number().int().nullish(),
    sampling_method: z.string().max(50).optional(),
    status: QualityReportsStatusEnum,
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
const ValuePassFailEnum = z.enum(["PASS", "FAIL"]);
const BlankEnum = z.unknown();
const MeasurementResultRequest: z.ZodType<MeasurementResultRequest> = z
  .object({
    definition: z.number().int(),
    value_numeric: z.number().nullish(),
    value_pass_fail: z
      .union([ValuePassFailEnum, BlankEnum, NullEnum])
      .nullish(),
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
    status: QualityReportsStatusEnum,
    description: z.string().max(300).nullish(),
    file: z.number().int().nullish(),
    errors: z.array(z.number().int()).optional(),
    measurements: z.array(MeasurementResultRequest),
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
    status: QualityReportsStatusEnum,
    description: z.string().max(300).nullable(),
    file: z.number().int().nullable(),
    errors: z.array(z.number().int()),
    measurements: z.array(MeasurementResultRequest),
    sampling_audit_log: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const Group: z.ZodType<Group> = z
  .object({ id: z.number().int(), name: z.string().max(150) })
  .passthrough();
const PaginatedGroupList: z.ZodType<PaginatedGroupList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(Group),
  })
  .passthrough();
const SeverityEnum = z.enum(["low", "medium", "high", "critical"]);
const HeatMapAnnotations: z.ZodType<HeatMapAnnotations> = z
  .object({
    id: z.number().int(),
    model: z.number().int(),
    model_display: z.string(),
    part: z.number().int(),
    part_display: z.string(),
    position_x: z.number(),
    position_y: z.number(),
    position_z: z.number(),
    measurement_value: z.number().nullish(),
    defect_type: z.string().max(255).nullish(),
    severity: z.union([SeverityEnum, BlankEnum, NullEnum]).nullish(),
    notes: z.string().optional(),
    created_by: z.number().int().nullable(),
    created_by_display: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
  })
  .passthrough();
const PaginatedHeatMapAnnotationsList: z.ZodType<PaginatedHeatMapAnnotationsList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(HeatMapAnnotations),
    })
    .passthrough();
const HeatMapAnnotationsRequest: z.ZodType<HeatMapAnnotationsRequest> = z
  .object({
    model: z.number().int(),
    part: z.number().int(),
    position_x: z.number(),
    position_y: z.number(),
    position_z: z.number(),
    measurement_value: z.number().nullish(),
    defect_type: z.string().max(255).nullish(),
    severity: z.union([SeverityEnum, BlankEnum, NullEnum]).nullish(),
    notes: z.string().optional(),
  })
  .passthrough();
const PatchedHeatMapAnnotationsRequest: z.ZodType<PatchedHeatMapAnnotationsRequest> =
  z
    .object({
      model: z.number().int(),
      part: z.number().int(),
      position_x: z.number(),
      position_y: z.number(),
      position_z: z.number(),
      measurement_value: z.number().nullable(),
      defect_type: z.string().max(255).nullable(),
      severity: z.union([SeverityEnum, BlankEnum, NullEnum]).nullable(),
      notes: z.string(),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    stage_name: z.string().max(100),
    API_id: z.string().max(50),
    pipeline_id: z.string().max(50).nullish(),
    display_order: z.number().int().gte(-2147483648).lte(2147483647).optional(),
    last_synced_at: z.string().datetime({ offset: true }).nullish(),
    include_in_progress: z.boolean().optional(),
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const ExternalAPIOrderIdentifierRequest = z
  .object({
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
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const PatchedExternalAPIOrderIdentifierRequest = z
  .object({
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
    previous_version: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const TypeEnum = z.enum(["NUMERIC", "PASS_FAIL"]);
const MeasurementDefinition: z.ZodType<MeasurementDefinition> = z
  .object({
    id: z.number().int(),
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
const MeasurementDefinitionRequest: z.ZodType<MeasurementDefinitionRequest> = z
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
  })
  .passthrough();
const PatchedMeasurementDefinitionRequest: z.ZodType<PatchedMeasurementDefinitionRequest> =
  z
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
    })
    .partial()
    .passthrough();
const NotificationTypeEnum = z.enum(["WEEKLY_REPORT", "CAPA_REMINDER"]);
const ChannelTypeEnum = z.enum(["email", "in_app", "sms"]);
const NotificationPreferenceStatusEnum = z.enum([
  "pending",
  "sent",
  "failed",
  "cancelled",
]);
const IntervalTypeEnum = z.enum(["fixed", "deadline_based"]);
const NotificationSchedule: z.ZodType<NotificationSchedule> = z
  .object({
    interval_type: IntervalTypeEnum,
    day_of_week: z.number().int().gte(0).lte(6).nullish(),
    time: z.string().nullish(),
    interval_weeks: z.number().int().gte(1).nullish(),
    escalation_tiers: z.array(z.array(z.number()).min(2).max(2)).nullish(),
  })
  .passthrough();
const NotificationPreference: z.ZodType<NotificationPreference> = z
  .object({
    id: z.number().int(),
    notification_type: NotificationTypeEnum,
    notification_type_display: z.string(),
    channel_type: ChannelTypeEnum.optional(),
    channel_type_display: z.string(),
    status: NotificationPreferenceStatusEnum,
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
const PaginatedNotificationPreferenceList: z.ZodType<PaginatedNotificationPreferenceList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(NotificationPreference),
    })
    .passthrough();
const NotificationScheduleRequest: z.ZodType<NotificationScheduleRequest> = z
  .object({
    interval_type: IntervalTypeEnum,
    day_of_week: z.number().int().gte(0).lte(6).nullish(),
    time: z.string().nullish(),
    interval_weeks: z.number().int().gte(1).nullish(),
    escalation_tiers: z.array(z.array(z.number()).min(2).max(2)).nullish(),
  })
  .passthrough();
const NotificationPreferenceRequest: z.ZodType<NotificationPreferenceRequest> =
  z
    .object({
      notification_type: NotificationTypeEnum,
      channel_type: ChannelTypeEnum.optional(),
      schedule: NotificationScheduleRequest.optional(),
      max_attempts: z.number().int().gte(-2147483648).lte(2147483647).nullish(),
    })
    .passthrough();
const PatchedNotificationPreferenceRequest: z.ZodType<PatchedNotificationPreferenceRequest> =
  z
    .object({
      notification_type: NotificationTypeEnum,
      channel_type: ChannelTypeEnum,
      schedule: NotificationScheduleRequest,
      max_attempts: z
        .number()
        .int()
        .gte(-2147483648)
        .lte(2147483647)
        .nullable(),
    })
    .partial()
    .passthrough();
const TestSendResponse = z
  .object({ status: z.string(), message: z.string() })
  .passthrough();
const AvailableNotificationTypes = z
  .object({ notification_types: z.array(z.object({}).partial().passthrough()) })
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
    name: z.string().max(200),
    customer_note: z.string().max(500).nullish(),
    customer: z.number().int().nullish(),
    customer_info: UserSelect.nullable(),
    company: z.number().int().nullish(),
    company_info: Company.nullable(),
    estimated_completion: z.string().nullish(),
    order_status: OrderStatusEnum,
    current_hubspot_gate: z.number().int().nullish(),
    parts_summary: z.object({}).partial().passthrough(),
    process_stages: z.array(z.unknown()),
    gate_info: z.object({}).partial().passthrough().nullable(),
    customer_first_name: z.string().nullable(),
    customer_last_name: z.string().nullable(),
    company_name: z.string().nullable(),
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
    name: z.string().min(1).max(200),
    customer_note: z.string().max(500).nullish(),
    customer: z.number().int().nullish(),
    company: z.number().int().nullish(),
    estimated_completion: z.string().nullish(),
    order_status: OrderStatusEnum,
    current_hubspot_gate: z.number().int().nullish(),
  })
  .passthrough();
const PatchedOrdersRequest: z.ZodType<PatchedOrdersRequest> = z
  .object({
    name: z.string().min(1).max(200),
    customer_note: z.string().max(500).nullable(),
    customer: z.number().int().nullable(),
    company: z.number().int().nullable(),
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
    archived: z.boolean().optional(),
    deleted_at: z.string().datetime({ offset: true }).nullish(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    ID_prefix: z.string().max(50).nullish(),
    ERP_id: z.string().max(50).nullish(),
    previous_version: z.number().int().nullish(),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullish(),
    ERP_id: z.string().max(50).nullish(),
    previous_version: z.number().int().nullish(),
  })
  .passthrough();
const PatchedPartTypesRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    ID_prefix: z.string().max(50).nullable(),
    ERP_id: z.string().max(50).nullable(),
    previous_version: z.number().int().nullable(),
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
    is_from_batch_process: z.boolean(),
    sampling_rule: z.number().int().nullish(),
    sampling_ruleset: z.number().int().nullish(),
    sampling_context: z.unknown().optional(),
    process: z.number().int(),
    total_rework_count: z.number().int(),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().max(50),
    is_remanufactured: z.boolean().optional(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    is_batch_process: z.boolean().optional(),
    previous_version: z.number().int().nullish(),
    part_type: z.number().int(),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
    is_current_version: z.boolean().optional(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean().optional(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    is_batch_process: z.boolean().optional(),
    previous_version: z.number().int().nullish(),
    part_type: z.number().int(),
  })
  .passthrough();
const PatchedProcessesRequest = z
  .object({
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
    version: z.number().int().gte(0).lte(2147483647),
    is_current_version: z.boolean(),
    name: z.string().min(1).max(50),
    is_remanufactured: z.boolean(),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    is_batch_process: z.boolean(),
    previous_version: z.number().int().nullable(),
    part_type: z.number().int(),
  })
  .partial()
  .passthrough();
const ProcessWithSteps: z.ZodType<ProcessWithSteps> = z
  .object({
    id: z.number().int(),
    name: z.string().max(50),
    is_remanufactured: z.boolean().optional(),
    part_type: z.number().int(),
    steps: z.array(Step),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    is_batch_process: z.boolean().optional(),
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
    is_remanufactured: z.boolean().optional(),
    part_type: z.number().int(),
    steps: z.array(StepRequest),
    num_steps: z.number().int().gte(-2147483648).lte(2147483647),
    is_batch_process: z.boolean().optional(),
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
      is_batch_process: z.boolean(),
    })
    .partial()
    .passthrough();
const CurrentStateEnum = z.enum(["OPEN", "IN_PROGRESS", "CLOSED"]);
const DispositionTypeEnum = z.enum([
  "REWORK",
  "SCRAP",
  "USE_AS_IS",
  "RETURN_TO_SUPPLIER",
]);
const QuarantineDisposition: z.ZodType<QuarantineDisposition> = z
  .object({
    id: z.number().int(),
    disposition_number: z.string(),
    current_state: CurrentStateEnum.optional(),
    disposition_type: z.union([DispositionTypeEnum, BlankEnum]).optional(),
    assigned_to: z.number().int().nullish(),
    description: z.string().optional(),
    resolution_notes: z.string().optional(),
    resolution_completed: z.boolean().optional(),
    resolution_completed_by: z.number().int().nullish(),
    resolution_completed_by_name: z.string(),
    resolution_completed_at: z.string().datetime({ offset: true }).nullish(),
    part: z.number().int().nullish(),
    step: z.number().int().nullish(),
    step_info: z.object({}).partial().passthrough().nullable(),
    rework_attempt_at_step: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    rework_limit_exceeded: z.boolean(),
    quality_reports: z.array(z.number().int()),
    assignee_name: z.string(),
    choices_data: z.object({}).partial().passthrough(),
  })
  .passthrough();
const PaginatedQuarantineDispositionList: z.ZodType<PaginatedQuarantineDispositionList> =
  z
    .object({
      count: z.number().int(),
      next: z.string().url().nullish(),
      previous: z.string().url().nullish(),
      results: z.array(QuarantineDisposition),
    })
    .passthrough();
const QuarantineDispositionRequest: z.ZodType<QuarantineDispositionRequest> = z
  .object({
    current_state: CurrentStateEnum.optional(),
    disposition_type: z.union([DispositionTypeEnum, BlankEnum]).optional(),
    assigned_to: z.number().int().nullish(),
    description: z.string().optional(),
    resolution_notes: z.string().optional(),
    resolution_completed: z.boolean().optional(),
    resolution_completed_by: z.number().int().nullish(),
    resolution_completed_at: z.string().datetime({ offset: true }).nullish(),
    part: z.number().int().nullish(),
    step: z.number().int().nullish(),
    rework_attempt_at_step: z
      .number()
      .int()
      .gte(-2147483648)
      .lte(2147483647)
      .optional(),
    quality_reports: z.array(z.number().int()),
  })
  .passthrough();
const PatchedQuarantineDispositionRequest: z.ZodType<PatchedQuarantineDispositionRequest> =
  z
    .object({
      current_state: CurrentStateEnum,
      disposition_type: z.union([DispositionTypeEnum, BlankEnum]),
      assigned_to: z.number().int().nullable(),
      description: z.string(),
      resolution_notes: z.string(),
      resolution_completed: z.boolean(),
      resolution_completed_by: z.number().int().nullable(),
      resolution_completed_at: z.string().datetime({ offset: true }).nullable(),
      part: z.number().int().nullable(),
      step: z.number().int().nullable(),
      rework_attempt_at_step: z.number().int().gte(-2147483648).lte(2147483647),
      quality_reports: z.array(z.number().int()),
    })
    .partial()
    .passthrough();
const SamplingRuleSet: z.ZodType<SamplingRuleSet> = z
  .object({
    id: z.number().int(),
    name: z.string().max(100),
    origin: z.string().max(100).optional(),
    active: z.boolean().optional(),
    version: z.number().int().gte(0).lte(2147483647).optional(),
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
    updated_at: z.string().datetime({ offset: true }),
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
    version: z.number().int().gte(0).lte(2147483647).optional(),
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
    version: z.number().int().gte(0).lte(2147483647),
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
  "exact_count",
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
    updated_at: z.string().datetime({ offset: true }),
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
const ThreeDModel: z.ZodType<ThreeDModel> = z
  .object({
    id: z.number().int(),
    name: z.string().max(255),
    file: z.string().url(),
    part_type: z.number().int().nullish(),
    part_type_display: z.string(),
    step: z.number().int().nullish(),
    step_display: z.string(),
    uploaded_at: z.string().datetime({ offset: true }),
    file_type: z.string(),
    annotation_count: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
    archived: z.boolean(),
    deleted_at: z.string().datetime({ offset: true }).nullable(),
  })
  .passthrough();
const PaginatedThreeDModelList: z.ZodType<PaginatedThreeDModelList> = z
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
    part_type: z.number().int().nullish(),
    step: z.number().int().nullish(),
  })
  .passthrough();
const PatchedThreeDModelRequest = z
  .object({
    name: z.string().min(1).max(255),
    file: z.instanceof(File),
    part_type: z.number().int().nullable(),
    step: z.number().int().nullable(),
  })
  .partial()
  .passthrough();
const User: z.ZodType<User> = z
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
    groups: z.array(Group),
  })
  .passthrough();
const PaginatedUserList: z.ZodType<PaginatedUserList> = z
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
    parent_company_id: z.number().int().nullish(),
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
    parent_company_id: z.number().int().nullable(),
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
    company_id: z.number().int().nullable(),
  })
  .passthrough();
const SendInvitationInputRequest = z
  .object({ user_id: z.number().int() })
  .passthrough();
const UserInvitation: z.ZodType<UserInvitation> = z
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
const PaginatedUserInvitationList: z.ZodType<PaginatedUserInvitationList> = z
  .object({
    count: z.number().int(),
    next: z.string().url().nullish(),
    previous: z.string().url().nullish(),
    results: z.array(UserInvitation),
  })
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
    related_order_info: z.object({}).partial().passthrough().nullable(),
    related_order_detail: Orders.nullable(),
    expected_completion: z.string().nullish(),
    expected_duration: z.string().nullish(),
    true_completion: z.string().nullish(),
    true_duration: z.string().nullish(),
    notes: z.string().max(500).nullish(),
    parts_summary: z.object({}).partial().passthrough(),
    is_batch_work_order: z.boolean(),
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
const EmbedQueryRequestRequest = z
  .object({ query: z.string().min(1) })
  .passthrough();
const EmbedQueryResponse = z
  .object({ embedding: z.array(z.number()) })
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
const ExecuteQueryResponse = z
  .object({
    model: z.string(),
    filters: z.object({}).partial().passthrough(),
    count: z.number().int(),
    limit: z.number().int(),
    results: z.array(z.object({}).partial().passthrough()),
  })
  .passthrough();
const ContextWindowRequestRequest = z
  .object({
    chunk_id: z.number().int(),
    window_size: z.number().int().optional(),
  })
  .passthrough();
const ContextWindowResponse = z
  .object({
    center_chunk_id: z.number().int(),
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
    doc_ids: z.array(z.number().int()),
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
    doc_ids: z.array(z.number().int()).optional(),
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
const GroupRequest = z
  .object({ name: z.string().min(1).max(150) })
  .passthrough();
const MeasurementResult: z.ZodType<MeasurementResult> = z
  .object({
    report: z.string(),
    definition: z.number().int(),
    value_numeric: z.number().nullish(),
    value_pass_fail: z
      .union([ValuePassFailEnum, BlankEnum, NullEnum])
      .nullish(),
    is_within_spec: z.boolean(),
    created_by: z.number().int(),
  })
  .passthrough();

export const schemas = {
  Company,
  PaginatedCompanyList,
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
  QualityReportsStatusEnum,
  QualityReports,
  PaginatedQualityReportsList,
  ValuePassFailEnum,
  BlankEnum,
  MeasurementResultRequest,
  QualityReportsRequest,
  PatchedQualityReportsRequest,
  Group,
  PaginatedGroupList,
  SeverityEnum,
  HeatMapAnnotations,
  PaginatedHeatMapAnnotationsList,
  HeatMapAnnotationsRequest,
  PatchedHeatMapAnnotationsRequest,
  ExternalAPIOrderIdentifier,
  ExternalAPIOrderIdentifierRequest,
  PatchedExternalAPIOrderIdentifierRequest,
  TypeEnum,
  MeasurementDefinition,
  PaginatedMeasurementDefinitionList,
  MeasurementDefinitionRequest,
  PatchedMeasurementDefinitionRequest,
  NotificationTypeEnum,
  ChannelTypeEnum,
  NotificationPreferenceStatusEnum,
  IntervalTypeEnum,
  NotificationSchedule,
  NotificationPreference,
  PaginatedNotificationPreferenceList,
  NotificationScheduleRequest,
  NotificationPreferenceRequest,
  PatchedNotificationPreferenceRequest,
  TestSendResponse,
  AvailableNotificationTypes,
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
  CurrentStateEnum,
  DispositionTypeEnum,
  QuarantineDisposition,
  PaginatedQuarantineDispositionList,
  QuarantineDispositionRequest,
  PatchedQuarantineDispositionRequest,
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
  ThreeDModel,
  PaginatedThreeDModelList,
  ThreeDModelRequest,
  PatchedThreeDModelRequest,
  User,
  PaginatedUserList,
  UserRequest,
  PatchedUserRequest,
  BulkUserActivationInputRequest,
  BulkCompanyAssignmentInputRequest,
  SendInvitationInputRequest,
  UserInvitation,
  PaginatedUserInvitationList,
  AcceptInvitationInputRequest,
  AcceptInvitationResponse,
  ResendInvitationInputRequest,
  ValidateTokenInputRequest,
  ValidateTokenResponse,
  WorkorderStatusEnum,
  WorkOrder,
  PaginatedWorkOrderList,
  WorkOrderRequest,
  PatchedWorkOrderRequest,
  EmbedQueryRequestRequest,
  EmbedQueryResponse,
  ExecuteQueryRequestRequest,
  ExecuteQueryResponse,
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
  GroupRequest,
  MeasurementResult,
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
    method: "post",
    path: "/api/ai/query/execute_read_only/",
    alias: "api_ai_query_execute_read_only_create",
    description: `Execute SAFE READ-ONLY ORM queries with strict validation`,
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
    response: z.void(),
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Documents/",
    alias: "api_Documents_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: Documents,
  },
  {
    method: "patch",
    path: "/api/Documents/:id/",
    alias: "api_Documents_partial_update",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: Documents,
  },
  {
    method: "delete",
    path: "/api/Documents/:id/",
    alias: "api_Documents_destroy",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Documents/:id/download/",
    alias: "api_Documents_download_retrieve",
    description: `Download the actual file`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Equipment/",
    alias: "api_Equipment_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Error-types/",
    alias: "api_Error_types_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/ErrorReports/",
    alias: "api_ErrorReports_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Groups/",
    alias: "api_Groups_list",
    description: `ViewSet for Django Groups - read only for selection purposes`,
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
    method: "get",
    path: "/api/Groups/:id/",
    alias: "api_Groups_retrieve",
    description: `ViewSet for Django Groups - read only for selection purposes`,
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
        schema: z.number().int().optional(),
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
        schema: z.number().int().optional(),
      },
      {
        name: "part__work_order",
        type: "Query",
        schema: z.number().int().optional(),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
    path: "/api/HubspotGates/",
    alias: "api_HubspotGates_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/MeasurementDefinitions/",
    alias: "api_MeasurementDefinitions_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/NotificationPreferences/",
    alias: "api_NotificationPreferences_list",
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
    requestFormat: "json",
    parameters: [
      {
        name: "channel_type",
        type: "Query",
        schema: z.enum(["email", "in_app", "sms"]).optional(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional(),
      },
      {
        name: "notification_type",
        type: "Query",
        schema: z.enum(["CAPA_REMINDER", "WEEKLY_REPORT"]).optional(),
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
        schema: z.enum(["cancelled", "failed", "pending", "sent"]).optional(),
      },
    ],
    response: PaginatedNotificationPreferenceList,
  },
  {
    method: "post",
    path: "/api/NotificationPreferences/",
    alias: "api_NotificationPreferences_create",
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
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
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
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
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
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
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
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
    description: `ViewSet for managing user notification preferences.

Provides CRUD operations for notification preferences including:
- Weekly order reports (recurring, fixed schedule)
- CAPA reminders (escalating, deadline-based)

Automatically handles timezone conversion between user&#x27;s local time and UTC.

Permissions:
- Users can only see and manage their own notification preferences
- Only authenticated users can access this endpoint`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Orders/export-excel/",
    alias: "api_Orders_export_excel_retrieve",
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
    path: "/api/Parts/",
    alias: "api_Parts_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Parts/export-excel/",
    alias: "api_Parts_export_excel_retrieve",
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
        name: "status__in",
        type: "Query",
        schema: z.array(z.string()).optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/PartTypes/",
    alias: "api_PartTypes_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/PartTypes/export-excel/",
    alias: "api_PartTypes_export_excel_retrieve",
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
        schema: z.number().int().optional(),
      },
    ],
    response: z.instanceof(File),
  },
  {
    method: "get",
    path: "/api/Processes_with_steps/",
    alias: "api_Processes_with_steps_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/QuarantineDispositions/",
    alias: "api_QuarantineDispositions_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
          .enum(["RETURN_TO_SUPPLIER", "REWORK", "SCRAP", "USE_AS_IS"])
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
        schema: z.number().int().optional(),
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "put",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_update",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "patch",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_partial_update",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: QuarantineDisposition,
  },
  {
    method: "delete",
    path: "/api/QuarantineDispositions/:id/",
    alias: "api_QuarantineDispositions_destroy",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Sampling-rule-sets/",
    alias: "api_Sampling_rule_sets_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/Sampling-rules/",
    alias: "api_Sampling_rules_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int().optional(),
      },
      {
        name: "process",
        type: "Query",
        schema: z.number().int().optional(),
      },
    ],
    response: z.instanceof(File),
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
        schema: z.number().int().optional(),
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
    requestFormat: "json",
    parameters: [
      {
        name: "id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "put",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_update",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "patch",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_partial_update",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
        schema: z.number().int(),
      },
    ],
    response: ThreeDModel,
  },
  {
    method: "delete",
    path: "/api/ThreeDModels/:id/",
    alias: "api_ThreeDModels_destroy",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/TrackerOrders/",
    alias: "api_TrackerOrders_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/TrackerOrders/export-excel/",
    alias: "api_TrackerOrders_export_excel_retrieve",
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
        schema: z.number().int().optional(),
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
    description: `List user&#x27;s notification preferences`,
    requestFormat: "json",
    parameters: [
      {
        name: "accepted_at",
        type: "Query",
        schema: z.string().datetime({ offset: true }).optional(),
      },
      {
        name: "channel_type",
        type: "Query",
        schema: z.string().optional(),
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
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_retrieve",
    description: `Retrieve a specific notification preference`,
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
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_partial_update",
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
    path: "/api/UserInvitations/:id/",
    alias: "api_UserInvitations_destroy",
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
    path: "/api/WorkOrders/",
    alias: "api_WorkOrders_list",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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
    path: "/api/WorkOrders/:id/qa_documents/",
    alias: "api_WorkOrders_qa_documents_retrieve",
    description: `Get documents relevant to QA for this work order`,
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
    method: "get",
    path: "/api/WorkOrders/:id/qa_summary/",
    alias: "api_WorkOrders_qa_summary_retrieve",
    description: `Get QA summary for work order including batch status`,
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
    method: "get",
    path: "/api/WorkOrders/export-excel/",
    alias: "api_WorkOrders_export_excel_retrieve",
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
    path: "/api/WorkOrders/upload_csv/",
    alias: "api_WorkOrders_upload_csv_create",
    description: `Mixin to add Excel export functionality to ViewSets.

Current features:
- Exports all non-relation fields by default
- Respects filtering, search, and ordering from list view
- Supports query param ?fields&#x3D;id,name,status to select specific fields
- Supports query param ?filename&#x3D;custom.xlsx for custom filename

Future enhancements (TODO):
- Add ExportConfiguration model for user-saved preferences
- Add available_fields() action to return list of exportable fields
- Add save_export_config() action to save user preferences
- Frontend: React modal with field checkboxes and &quot;Save as Default&quot; button

Usage:
    class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
        excel_fields &#x3D; [&#x27;id&#x27;, &#x27;name&#x27;, &#x27;status&#x27;]  # Optional: override default fields
        excel_filename &#x3D; &#x27;my_export.xlsx&#x27;  # Optional: override default filename

    GET /api/my-model/export_excel/
    GET /api/my-model/export_excel/?fields&#x3D;id,name
    GET /api/my-model/export_excel/?filename&#x3D;custom_export.xlsx`,
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

// Use VITE_API_TARGET environment variable for production builds
// In development with Vite dev server, don't set base URL to rely on Vite proxy
// In production, this will be replaced at build time with the actual backend URL
const BASE_URL = import.meta.env.VITE_API_TARGET;

export const api = BASE_URL
  ? new Zodios(BASE_URL, endpoints, {
      axiosConfig: {
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: "repeat" }),
      },
    })
  : new Zodios(endpoints, {
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
