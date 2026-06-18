"""
Group presets for tenant initialization.

These presets define the default groups and permissions seeded when a new tenant
is created. Tenant admins can customize permissions after creation.

Permission system:
- Permissions control both ACTIONS (add, change, delete) and DATA VISIBILITY (view_*)
- Users without view_* permission fall back to Order relationship filtering
  (Order.customer and Order.viewers determine access)

Policy (the whole file follows from these two rules):
- **Customer is the only hard access boundary.** External portal users get
  view-only access plus the handful of portal interactions they genuinely need
  (responding to use-as-is approvals, AI chat), row-filtered to their own
  orders. Everything else is internal.
- **Internal roles are permissive by default.** Every internal "doer" role gets
  the full view base plus broad add/change on operational records. The only
  things held back are the named compliance sets below — each one states its
  reason. If a permission isn't compliance-shaped, every doer role has it.

Compliance holdbacks (the ONLY reasons an internal role lacks a permission):
- Segregation of duties: approve/verify/close verbs + approver routing
  (SOD_APPROVAL_PERMISSIONS) — QA Manager / Tenant Admin only.
- Change control: authoring of processes, work instructions, specs, BOMs,
  controlled docs (AUTHORING_PERMISSIONS) — engineering/manager tier.
- Record retention: delete_ on operational records (MANAGER_DELETE_PERMISSIONS)
  — manager tier; line roles void/supersede, never delete.
- Export control / ITAR: classification + audit-log export
  (COMPLIANCE_PERMISSIONS) — Tenant Admin + Document Controller.
- Document classification: secret tier + classification authority — narrow.
- Audit independence: Auditor is view-only, no classified tiers.
- Access administration: users, groups, invitations, order viewers — admin /
  manager tier.
- Audit-record writes: none. Append-only audit tables (sampling audit log,
  step transition log, equipment usage, approval responses) are enforced
  immutable by DB triggers (setup_audit_triggers) — no role gets dead grants.

Usage:
    from Tracker.presets import GROUP_PRESETS

    # In seed_groups_for_tenant():
    for key, preset in GROUP_PRESETS.items():
        group = TenantGroup.objects.create(...)
        if preset['permissions'] == '__all__':
            group.permissions.set(Permission.objects.all())
        else:
            group.permissions.set(Permission.objects.filter(codename__in=preset['permissions']))
"""

# =============================================================================
# STAFF VIEW BASE - every internal role, INCLUDING Auditor, sees everything
# =============================================================================
# Philosophy: everyone internal should be able to see what's happening in the
# system. Classified document tiers are the one exception (see
# CLASSIFIED_DOCUMENT_VIEW below); the secret tier is narrower still.

STAFF_VIEW_PERMISSIONS = [
    # Export-your-own-views
    'export_data',
    # Production
    'view_orders', 'view_workorder', 'view_parts', 'view_parttypes',
    'view_processes', 'view_steps', 'view_processstep', 'view_stepedge',
    'view_stepexecution', 'view_steptransitionlog', 'view_stepmeasurementrequirement',
    'view_companies', 'view_orderviewer', 'view_externalapiorderidentifier',
    # DWI (digital work instructions)
    'view_substep', 'view_substepcompletion', 'view_substepresource',
    'view_substeptranslation', 'view_substepgatecompletion', 'view_substepresponse',
    # Production exceptions & runtime records
    'view_workorderhold', 'view_steprollback', 'view_batchrollback',
    'view_stepoverride', 'view_fpirecord', 'view_batchexecution',
    'view_steprequirement',
    # BOM & Materials
    'view_bom', 'view_bomline', 'view_assemblyusage', 'view_disassemblybomline',
    'view_materiallot', 'view_materialusage', 'view_harvestedcomponent',
    'view_core',
    # Equipment & Calibration
    'view_equipments', 'view_equipmenttype', 'view_equipmentusage',
    'view_calibrationrecord',
    # Scheduling
    'view_workcenter', 'view_shift', 'view_scheduleslot', 'view_downtimeevent',
    'view_timeentry',
    # Milestones & life tracking
    'view_milestone', 'view_milestonetemplate',
    'view_lifelimitdefinition', 'view_parttypelifelimit', 'view_lifetracking',
    # Quality
    'view_qualityreports', 'view_qualityerrorslist', 'view_qualityreportdefect',
    'view_qaapproval', 'view_quarantinedisposition',
    'view_qualityreportequipment', 'view_qualityreportpersonnel',
    # CAPA & RCA
    'view_capa', 'view_capatasks', 'view_capataskassignee', 'view_capaverification',
    'view_rcarecord', 'view_fishbone', 'view_fivewhys', 'view_rootcause',
    'view_capastatustransition',
    # Measurements & SPC
    'view_measurementresult', 'view_measurementdefinition', 'view_spcbaseline',
    'view_stepexecutionmeasurement',
    # Documents (classified tiers live in CLASSIFIED_DOCUMENT_VIEW)
    'view_documents', 'view_documenttype',
    # 3D Models & Annotations
    'view_threedmodel', 'view_heatmapannotations',
    # Approvals
    'view_approvaltemplate', 'view_approvalrequest', 'view_approvalresponse',
    'view_approverassignment', 'view_groupapproverassignment',
    # Sampling
    'view_samplingrule', 'view_samplingruleset', 'view_samplingdecision',
    'view_samplinganalytics', 'view_samplingauditlog', 'view_samplingtriggerstate',
    # Process Change Control
    'view_processchangerequest', 'view_processchangeorder', 'view_processchangenotice',
    # Training
    'view_trainingrecord', 'view_trainingtype', 'view_trainingrequirement',
    # Reports
    'view_generatedreport',
    # AI Chat & Embeddings
    'view_chatsession', 'view_docchunk',
    # Notifications (config is admin-managed; everyone can see what's configured)
    'view_notificationrule', 'view_notificationschedule',
    # Audit & traceability (viewing is universal; exporting is compliance-gated)
    # `view_logentry` is the django-auditlog perm the /api/auditlog/ endpoint
    # actually enforces (TenantModelPermissions derives it from the LogEntry
    # model); `view_auditlog` is the Tracker-side marker. Grant both.
    'view_auditlog', 'view_logentry', 'view_recordedit', 'view_permissionchangelog',
    # Admin/Config (view only) — group/role *membership* is readable by all
    # staff (the endpoints already allow it); managing it stays admin-only.
    'view_facility', 'view_archivereason', 'view_user', 'view_userinvitation',
    'view_tenantgroup', 'view_userrole',
]

# Classified technical data (confidential + restricted tiers). All internal
# doer roles — the floor needs restricted technical documents to do the work.
# NOT Auditor (audit independence / export-control: external auditors may not
# be authorized persons) and NOT Customer. The secret tier and classification
# authority are granted per-role below.
CLASSIFIED_DOCUMENT_VIEW = [
    'view_confidential_documents', 'view_restricted_documents',
]

# =============================================================================
# STAFF OPERATIONAL WRITE - broad add/change for every internal doer role
# =============================================================================
# Philosophy: internal roles are trusted; over-granting operational capability
# is preferable to a role hitting a 403 mid-task. Anything add/change on an
# operational record is here. What is NOT here (and why):
#   - delete_ on records        -> MANAGER_DELETE_PERMISSIONS (retention)
#   - authoring of definitions  -> AUTHORING_PERMISSIONS (change control)
#   - approve/verify/close      -> SOD_APPROVAL_PERMISSIONS (segregation of duties)
#   - export control, secret docs, access admin, notification config -> below
# Append-only audit models (recordedit, capastatustransition, ...) have no
# write grants anywhere — enforced by test_permission_coverage.py + DB triggers.

STAFF_OPERATIONAL_WRITE = [
    # Production records
    'add_orders', 'change_orders',
    'add_workorder', 'change_workorder',
    'add_parts', 'change_parts',
    'add_stepexecution', 'change_stepexecution',
    # (steptransitionlog is service-written and DB-immutable — view only)
    # Production exceptions
    'add_workorderhold', 'change_workorderhold',
    'add_steprollback', 'change_steprollback',
    'add_batchrollback', 'change_batchrollback',
    'add_stepoverride', 'change_stepoverride',
    'add_fpirecord', 'change_fpirecord',
    'add_batchexecution', 'change_batchexecution',
    'add_steprequirement', 'change_steprequirement',
    # DWI runtime — completions + per-node responses + gate completions
    'add_substepcompletion', 'change_substepcompletion',
    'add_substepgatecompletion', 'change_substepgatecompletion',
    'add_substepresponse', 'change_substepresponse',
    # Reman — receive + work cores, grade harvested components
    'add_core', 'change_core',
    'start_disassembly', 'complete_disassembly', 'scrap_core',
    'grade_component', 'accept_component', 'reject_component',
    'add_harvestedcomponent', 'change_harvestedcomponent',
    # Materials & BOM usage
    'add_materiallot', 'change_materiallot',
    'add_materialusage', 'change_materialusage',
    'add_assemblyusage', 'change_assemblyusage',
    # Equipment & Calibration (equipmentusage rows are DB-immutable once
    # written — add only, no change)
    'add_equipments', 'change_equipments',
    'add_equipmenttype', 'change_equipmenttype',
    'add_equipmentusage',
    'add_calibrationrecord', 'change_calibrationrecord',
    # Scheduling & time
    'add_workcenter', 'change_workcenter',
    'add_shift', 'change_shift',
    'add_scheduleslot', 'change_scheduleslot',
    'add_downtimeevent', 'change_downtimeevent',
    'add_timeentry', 'change_timeentry',
    # Milestones & life tracking
    'add_milestone', 'change_milestone',
    'add_milestonetemplate', 'change_milestonetemplate',
    'add_lifelimitdefinition', 'change_lifelimitdefinition',
    'add_parttypelifelimit', 'change_parttypelifelimit',
    'add_lifetracking', 'change_lifetracking',
    # Quality records
    'add_qualityreports', 'change_qualityreports',
    'add_qualityerrorslist', 'change_qualityerrorslist',
    'add_qualityreportdefect', 'change_qualityreportdefect',
    'add_qaapproval', 'change_qaapproval',
    'add_quarantinedisposition', 'change_quarantinedisposition',
    'add_qualityreportequipment', 'change_qualityreportequipment',
    'add_qualityreportpersonnel', 'change_qualityreportpersonnel',
    # CAPA & RCA — anyone can raise and work; approval verbs are SoD-gated
    'add_capa', 'change_capa', 'initiate_capa',
    'add_capatasks', 'change_capatasks',
    'add_capataskassignee', 'change_capataskassignee',
    'add_capaverification', 'change_capaverification',
    'add_rcarecord', 'change_rcarecord', 'conduct_rca',
    'add_fishbone', 'change_fishbone',
    'add_fivewhys', 'change_fivewhys',
    'add_rootcause', 'change_rootcause',
    # Measurements & SPC — operators record step measurements via the
    # bulk-record endpoint (POST → add_); change/delete stay immutable
    'add_measurementresult', 'change_measurementresult',
    'add_stepexecutionmeasurement',
    'add_spcbaseline', 'change_spcbaseline',
    # Documents & 3D — records in/out; deletion + classification are gated
    'add_documents', 'change_documents',
    'add_threedmodel', 'change_threedmodel',
    'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations',
    # Reports
    'add_generatedreport', 'change_generatedreport',
    # Approvals — route for approval + respond; workflow admin is gated.
    # Responses are e-signature records: DB-immutable once written (add only;
    # delegation is a crud-exempt action gated on respond_to_approval).
    'add_approvalrequest', 'change_approvalrequest',
    'add_approvalresponse',
    'respond_to_approval',
    # Sampling — rules editable by quality doers today; deletes are manager-tier
    'add_samplingrule', 'change_samplingrule',
    'add_samplingruleset', 'change_samplingruleset',
    'add_samplinganalytics', 'change_samplinganalytics',
    # Process change — anyone can raise/edit/submit a change request. Note:
    # the `propose` action also requires add_processes (it forks a draft
    # process), and approve/reject additionally gate on change_processes —
    # so deciding a PCR stays with authoring roles even though the PCR row
    # itself is broadly writable.
    'add_processchangerequest', 'change_processchangerequest',
    # Training
    'add_trainingrecord', 'change_trainingrecord',
    # Master data & config (not compliance-shaped)
    'add_companies', 'change_companies',
    'add_externalapiorderidentifier', 'change_externalapiorderidentifier',
    'add_facility', 'change_facility',
    'add_archivereason', 'change_archivereason',
    # AI Chat (own sessions)
    'add_chatsession', 'change_chatsession', 'delete_chatsession',
]

# =============================================================================
# COMPLIANCE HOLDBACK SETS
# =============================================================================

# Change control: authoring of processes, work instructions, specs, BOM
# definitions, controlled document types, approval workflows. Engineering +
# manager tier + Document Controller. Line roles execute these definitions;
# they don't author them. Authors also delete their own draft artifacts.
AUTHORING_PERMISSIONS = [
    # Process & step definitions
    'add_processes', 'change_processes', 'delete_processes',
    'add_steps', 'change_steps', 'delete_steps',
    'add_processstep', 'change_processstep', 'delete_processstep',
    'add_stepedge', 'change_stepedge', 'delete_stepedge',
    # DWI substep authoring
    'add_substep', 'change_substep', 'delete_substep',
    'add_substepresource', 'change_substepresource', 'delete_substepresource',
    'add_substeptranslation', 'change_substeptranslation', 'delete_substeptranslation',
    # Specs
    'add_parttypes', 'change_parttypes', 'delete_parttypes',
    'add_measurementdefinition', 'change_measurementdefinition', 'delete_measurementdefinition',
    'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement',
    # BOM definitions
    'add_bom', 'change_bom', 'delete_bom',
    'add_bomline', 'change_bomline', 'delete_bomline',
    'add_disassemblybomline', 'change_disassemblybomline', 'delete_disassemblybomline',
    # Controlled documents — deletion + categories (add/change of documents is broad)
    'delete_documents', 'delete_threedmodel',
    'add_documenttype', 'change_documenttype', 'delete_documenttype',
    # Approval workflow authoring
    'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate',
    'create_approval_template', 'manage_approval_workflow',
    # Training program definitions
    'add_trainingtype', 'change_trainingtype', 'delete_trainingtype',
    'add_trainingrequirement', 'change_trainingrequirement', 'delete_trainingrequirement',
    # AI embedding pipeline (document-derived)
    'add_docchunk', 'change_docchunk', 'delete_docchunk',
    # Process change control — PCO/PCN lifecycle; PCR proposing is broad
    'delete_processchangerequest',
    'add_processchangeorder', 'change_processchangeorder', 'delete_processchangeorder',
    'add_processchangenotice', 'change_processchangenotice', 'delete_processchangenotice',
]

# Segregation of duties: e-signature approve/verify/close verbs + approver
# routing. QA Manager + Tenant Admin only — the person doing the work must not
# be the person who can approve it.
# NOTE: `approve_own_qualityreports` ("Can approve own quality reports") is
# deliberately granted to NO role — it is a license to self-approve, which is
# exactly what this set exists to prevent. See test_permission_coverage.py.
SOD_APPROVAL_PERMISSIONS = [
    'approve_qualityreports',
    'approve_capa', 'close_capa', 'verify_capa',
    'review_rca',
    'approve_disposition', 'close_disposition',
    # Approver routing — who is eligible to approve what
    'add_approverassignment', 'change_approverassignment', 'delete_approverassignment',
    'add_groupapproverassignment', 'change_groupapproverassignment', 'delete_groupapproverassignment',
]

# Disposition resolution: closing an NCR's disposition (resolving the decision).
# Granted GENEROUSLY across the manager / lead / inspector tiers — many roles
# legitimately resolve dispositions on the floor, so this is not held to the
# narrow SoD approve tier. (`approve_disposition` stays SoD-restricted above; the
# line Operator is still excluded — they surface the QR, they don't disposition it.)
# qa_manager / tenant_admin already get close_disposition via SOD_APPROVAL_PERMISSIONS.
DISPOSITION_RESOLUTION_PERMISSIONS = [
    'close_disposition',
]

# Decision-point resolution (4a): choosing the routing branch at a MANUAL
# decision-point step. Manager / lead tier — operators run the step but a
# supervisor makes the routing call. (QA_RESULT decision points route
# automatically from the QualityReport and need no permission.)
DECISION_RESOLUTION_PERMISSIONS = [
    'resolve_step_decision',
]

# First Piece Inspection buy-off: who may pass / fail / waive an FPI. Setup
# verification must be independent of the operator who ran the first piece, so
# this goes to the QA / lead / manager tier (same distribution as decision
# resolution) and is deliberately withheld from the Operator role.
FPI_SIGNOFF_PERMISSIONS = [
    'sign_off_fpi',
]

# Record retention: deleting operational records is manager-tier only. Line
# roles void / supersede / archive, never delete. (Authoring artifacts delete
# via AUTHORING_PERMISSIONS; soft-delete-only models grant no delete at all —
# see test_permission_coverage.py.)
MANAGER_DELETE_PERMISSIONS = [
    'delete_orders', 'delete_workorder', 'delete_parts',
    'delete_stepexecution',
    'delete_substepcompletion', 'delete_substepgatecompletion', 'delete_substepresponse',
    'delete_core', 'delete_harvestedcomponent',
    'delete_materiallot', 'delete_materialusage', 'delete_assemblyusage',
    'delete_equipments', 'delete_equipmenttype',
    'delete_calibrationrecord',
    'delete_workcenter', 'delete_shift', 'delete_scheduleslot',
    'delete_downtimeevent', 'delete_timeentry',
    'delete_qualityreports', 'delete_qualityerrorslist', 'delete_qualityreportdefect',
    'delete_qaapproval', 'delete_quarantinedisposition',
    'delete_capa', 'delete_capatasks', 'delete_capataskassignee', 'delete_capaverification',
    'delete_rcarecord', 'delete_fishbone', 'delete_fivewhys', 'delete_rootcause',
    'delete_measurementresult', 'delete_spcbaseline',
    'delete_generatedreport',
    'delete_approvalrequest',
    'delete_samplingrule', 'delete_samplingruleset', 'delete_samplinganalytics',
    'delete_trainingrecord',
    'delete_companies', 'delete_externalapiorderidentifier',
    'delete_facility', 'delete_archivereason',
]

# Access administration: who can see which orders, who joins the team.
# Manager tier (QA + Production) + Tenant Admin.
TEAM_ACCESS_ADMIN_PERMISSIONS = [
    'add_userinvitation', 'change_userinvitation', 'delete_userinvitation',
    'add_orderviewer', 'change_orderviewer', 'delete_orderviewer',
]

# ITAR / export-control declaration + audit-log export. Compliance roles only
# (Tenant Admin + Document Controller). A line operator must NOT be able to
# (re)classify export-controlled technical data or pull the audit log.
COMPLIANCE_PERMISSIONS = [
    'verify_export_control', 'change_export_classification', 'export_auditlog',
]

# Notification rule/schedule management = tenant configuration. Tenant Admin +
# the manager roles (Production / QA) for their domains. NOT line roles.
NOTIFICATION_ADMIN_PERMISSIONS = [
    'edit_notification_rules', 'edit_notification_schedules',
    'add_notificationrule', 'change_notificationrule',
    'add_notificationschedule', 'change_notificationschedule',
]

# =============================================================================
# GROUP PRESETS
# =============================================================================
# Each preset defines:
#   - name: Display name for the group
#   - description: Human-readable description
#   - permissions: List of codenames or '__all__' for full access
#
# Data filtering: Users with view_* permissions see all data of that type.
# Users without view_* permissions fall back to Order relationship filtering.
#
# Internal roles = base sets + compliance holdbacks they qualify for + a small
# per-role delta. If you're adding a permission, prefer adding it to the right
# shared set over a role's delta.

GROUP_PRESETS = {
    # -------------------------------------------------------------------------
    # SYSTEM ADMIN - Platform admin (your business - SaaS provider)
    # -------------------------------------------------------------------------
    'system_admin': {
        'name': 'System Admin',
        'description': 'Platform administrator - manages all tenants and system settings',
        'permissions': '__all__',  # Gets every permission including tenant management
    },

    # -------------------------------------------------------------------------
    # TENANT ADMIN - Customer business admin (manages their own tenant)
    # -------------------------------------------------------------------------
    'tenant_admin': {
        'name': 'Tenant Admin',
        'description': 'Tenant administrator - full access within their organization',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *AUTHORING_PERMISSIONS,
            *SOD_APPROVAL_PERMISSIONS,
            *MANAGER_DELETE_PERMISSIONS,
            *TEAM_ACCESS_ADMIN_PERMISSIONS,
            *NOTIFICATION_ADMIN_PERMISSIONS,
            *COMPLIANCE_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Secret document tier + classification authority
            'view_secret_documents', 'classify_documents',
            # User management within tenant (view perms come from the staff
            # view base; membership is the UserRole model)
            'add_user', 'change_user', 'delete_user',
            'add_userrole', 'change_userrole', 'delete_userrole',
            # Group management within tenant
            'add_tenantgroup', 'change_tenantgroup', 'delete_tenantgroup',
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
        ],
    },

    # -------------------------------------------------------------------------
    # QA MANAGER - Quality management, approvals, CAPA control
    # -------------------------------------------------------------------------
    'qa_manager': {
        'name': 'QA Manager',
        'description': 'Quality management, approvals, CAPA control',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *AUTHORING_PERMISSIONS,
            *SOD_APPROVAL_PERMISSIONS,
            *MANAGER_DELETE_PERMISSIONS,
            *TEAM_ACCESS_ADMIN_PERMISSIONS,
            *NOTIFICATION_ADMIN_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Classification authority (no secret tier)
            'classify_documents',
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
        ],
    },

    # -------------------------------------------------------------------------
    # QA INSPECTOR - Perform inspections, create quality reports
    # -------------------------------------------------------------------------
    'qa_inspector': {
        'name': 'QA Inspector',
        'description': 'Perform inspections, create quality reports, initiate CAPAs',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            # Resolve (close) NCR dispositions
            *DISPOSITION_RESOLUTION_PERMISSIONS,
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # PRODUCTION MANAGER - Production oversight
    # -------------------------------------------------------------------------
    'production_manager': {
        'name': 'Production Manager',
        'description': 'Manage production operations, work orders, scheduling',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *AUTHORING_PERMISSIONS,
            *MANAGER_DELETE_PERMISSIONS,
            *TEAM_ACCESS_ADMIN_PERMISSIONS,
            *NOTIFICATION_ADMIN_PERMISSIONS,
            # Resolve (close) NCR dispositions
            *DISPOSITION_RESOLUTION_PERMISSIONS,
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # OPERATOR - Production floor work
    # -------------------------------------------------------------------------
    'operator': {
        'name': 'Operator',
        'description': 'Production floor work, inspections, data entry',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # SHIFT LEAD - Floor-shaped supervisor between Operator and Production Manager
    # -------------------------------------------------------------------------
    # Same grants as Operator today — the base sets already include the team /
    # quality-oversight visibility that used to be Shift Lead additions.
    # Override / waive / reassign authority will be added when those features
    # exist as distinct permissions.
    'shift_lead': {
        'name': 'Shift Lead',
        'description': 'Floor supervisor: runs work like an operator plus team visibility and quality oversight',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            # Resolve (close) NCR dispositions
            *DISPOSITION_RESOLUTION_PERMISSIONS,
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # DOCUMENT CONTROLLER - Manage controlled documents
    # -------------------------------------------------------------------------
    'document_controller': {
        'name': 'Document Controller',
        'description': 'Manage controlled documents, revisions, and approvals',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *AUTHORING_PERMISSIONS,
            *MANAGER_DELETE_PERMISSIONS,
            *COMPLIANCE_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Secret document tier + classification authority
            'view_secret_documents', 'classify_documents',
        ],
    },

    # -------------------------------------------------------------------------
    # ENGINEERING - Design and engineering changes
    # -------------------------------------------------------------------------
    'engineering': {
        'name': 'Engineering',
        'description': 'Engineering changes, drawing control, design work',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *AUTHORING_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # AUDITOR - Read-only, audit independence
    # -------------------------------------------------------------------------
    # View base only: auditors must not mutate what they audit, and don't get
    # the classified document tiers (external auditors may not be authorized
    # persons for export-controlled technical data).
    'auditor': {
        'name': 'Auditor',
        'description': 'Read-only access for audits, anonymized sensitive data',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # CUSTOMER - External customer portal access
    # -------------------------------------------------------------------------
    'customer': {
        'name': 'Customer',
        'description': 'External customer portal - view their orders only',
        'permissions': [
            # NOTE: No 'full_tenant_access' - customers only see data related to their orders
            # (filtered via Order.customer/viewers relationships in for_user())
            'view_orders',
            'view_workorder',
            'view_parts',
            # Order viewers - see who has access + invite viewers to their own
            # orders (the /TrackerOrders/{id}/invite/ action gates on
            # add_orderviewer; row scoping via for_user() keeps it to orders
            # they can already reach)
            'view_orderviewer', 'add_orderviewer',
            # Documents linked to their orders (+ the type catalog the portal
            # needs to label/filter them — /api/DocumentTypes/ gates on it)
            'view_documents', 'view_documenttype',
            # Quality info for their orders
            'view_qualityreports',
            # Approvals - can respond to customer approval requests (use-as-is, etc.)
            'view_approvalrequest', 'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            # AI Chat - customers can use AI assistance (own sessions only)
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
        ],
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_preset(key):
    """Get a preset by its key."""
    return GROUP_PRESETS.get(key)


def get_preset_names():
    """Get list of all preset keys."""
    return list(GROUP_PRESETS.keys())


def get_all_preset_permissions():
    """Get set of all permission codenames used across all presets."""
    all_perms = set()
    for preset in GROUP_PRESETS.values():
        if preset['permissions'] != '__all__':
            all_perms.update(preset['permissions'])
    return all_perms



def validate_presets():
    """
    Validate that all permissions in presets exist in the database.

    Returns list of missing permission codenames.
    Call this during startup or tests to catch typos.
    """
    from django.contrib.auth.models import Permission

    preset_perms = get_all_preset_permissions()
    db_perms = set(Permission.objects.values_list('codename', flat=True))

    missing = preset_perms - db_perms
    return sorted(missing)