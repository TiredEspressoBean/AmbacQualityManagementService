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
    'view_orders', 'view_orderline', 'view_workorder', 'view_parts', 'view_parttypes',
    'view_processes', 'view_steps', 'view_processstep', 'view_stepedge',
    'view_stepexecution', 'view_steptransitionlog', 'view_stepmeasurementrequirement',
    'view_outsideprocessshipment', 'view_customershipment',
    'view_companies', 'view_orderviewer', 'view_externalapiorderidentifier',
    # DWI (digital work instructions)
    'view_substep', 'view_substepcompletion', 'view_substepresource',
    'view_substeptranslation', 'view_substepgatecompletion', 'view_substepresponse',
    # Production exceptions & runtime records
    'view_workorderhold',
    'view_stepoverride', 'view_fpirecord', 'view_batchexecution',
    'view_steprequirement',
    # Shift notes (all floor staff read; authoring is a lead grant)
    'view_shiftnote', 'view_shiftnoteack',
    # BOM & Materials
    'view_bom', 'view_bomline', 'view_assemblyusage', 'view_disassemblybomline',
    'view_material', 'view_storagelocation', 'view_cyclecount',
    'view_materiallot', 'view_materialusage', 'view_materialstaging',
    'view_materialstagingline',
    'view_harvestedcomponent',
    'view_core',
    'view_repaircode', 'view_rebuildscopepreset', 'view_rebuildslotoverride',
    # Equipment & Calibration
    'view_equipments', 'view_equipmenttype',
    'view_calibrationrecord',
    # Scheduling
    'view_workcenter', 'view_shift', 'view_scheduleslot', 'view_downtimeevent',
    'view_timeentry', 'view_userworkcentermembership',
    # CP-SAT scheduler: everyone can read the schedule + its inputs
    'view_scheduleresult', 'view_scheduledtask', 'view_steptiming',
    'view_stepequipmentaffinity', 'view_workcenterchangeover', 'view_fixture',
    'view_optimizationconfig', 'view_continuousmachine',
    'view_laborcalendarblock', 'view_overtimewindow', 'view_plantcalendarexception',
    # Milestones & life tracking
    'view_milestone', 'view_milestonetemplate',
    'view_lifelimitdefinition', 'view_parttypelifelimit', 'view_lifetracking',
    # Quality
    'view_qualityreports', 'view_qualityerrorslist', 'view_qualityreportdefect',
    'view_qaapproval', 'view_quarantinedisposition',
    'view_qualityreportequipment', 'view_qualityreportpersonnel',
    'view_stepexecutionequipment',
    # Supplier quality / part approval / quality gates
    'view_supplierqualification', 'view_partapproval', 'view_stepgatefiring',
    # CAPA & RCA
    'view_capa', 'view_capatasks', 'view_capataskassignee', 'view_capaverification',
    'view_rcarecord', 'view_fishbone', 'view_fivewhys', 'view_rootcause',
    'view_capastatustransition',
    # Measurements & SPC
    'view_measurementresult', 'view_measurementdefinition', 'view_spcbaseline',
    'view_stepexecutionmeasurement',
    # Documents (classified tiers live in CLASSIFIED_DOCUMENT_VIEW)
    'view_documents', 'view_documenttype', 'view_documentlink',
    # 3D Models & Annotations
    'view_threedmodel', 'view_heatmapannotations',
    # Approvals
    'view_approvaltemplate', 'view_approvalrequest', 'view_approvalresponse',
    'view_approverassignment', 'view_groupapproverassignment',
    # Sampling
    'view_samplingrule', 'view_samplingruleset', 'view_samplingdecision',
    'view_samplinganalytics', 'view_samplingauditlog', 'view_samplingtriggerstate',
    'view_samplingseveritystate',
    'view_samplingseveritystate',
    # Process Change Control
    'view_processchangerequest', 'view_processchangeorder', 'view_processchangenotice',
    # Training. `view_training_matrix` lives here (not per-group) as a
    # transparent lean/ILUO board: every internal-staff group spreads
    # STAFF_VIEW_PERMISSIONS, so all staff (incl. operators) see the competency
    # grid; the Customer preset omits this bundle, so externals stay out. Pull
    # this one line out to a narrower set if competency is ever made HR-private.
    'view_trainingrecord', 'view_trainingtype', 'view_trainingrequirement',
    'view_training_matrix',
    'view_jobrole',
    # Reports
    'view_generatedreport',
    # AI Chat & Embeddings
    'view_chatsession', 'view_docchunk',
    # Notifications (config is admin-managed; everyone can see what's configured —
    # including the customer contacts a rule sends to, so the recipient list on a
    # rule staff can open isn't a 403. Managing contacts stays manager-tier.)
    'view_notificationrule', 'view_notificationschedule', 'view_externalcontact',
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
    # (Removed 2026-10-06, no endpoint behind them — a grant with nothing to gate
    # becomes a live hole the day someone adds one: add/change for qaapproval,
    # steprequirement, samplinganalytics and generatedreport, change_measurementresult
    # (results are immutable), and add_approvalresponse (ApprovalResponses is
    # read-only; responses come from submit-response).)
    # Production records
    'add_orders', 'change_orders',
    # Recording what a customer asked for is order administration. Turning that demand
    # into work is a different authority — `plan` on the line is gated on
    # `add_workorder`, because committing capacity and material is not the same act as
    # writing down the request.
    'add_orderline', 'change_orderline',
    # Curating a rebuild plan is planning work, not engineering authoring — the codes
    # are authored once, the override is a call made on one unit in front of you.
    'add_rebuildslotoverride', 'change_rebuildslotoverride',
    'add_workorder', 'change_workorder',
    'add_parts', 'change_parts',
    'add_stepexecution', 'change_stepexecution',
    # Outside processing (subcontract send-out / receive-back — Flow B).
    # delete is opted out (retired via status/void), like other operational records.
    'add_outsideprocessshipment', 'change_outsideprocessshipment',
    # Shipping to customers: ship (add) and correct/void (change). Voided, never deleted.
    'add_customershipment', 'change_customershipment',
    # Counting a location (start, record, submit). Applying it to stock is a lead's call.
    'add_cyclecount', 'change_cyclecount',
    # Anyone who receives or moves stock can add the location it's going to ("add new" in
    # the picker). Renaming, nesting and the held-only / dock controls stay with leads.
    'add_storagelocation',
    # (steptransitionlog is service-written and DB-immutable — view only)
    # Production exceptions
    'add_workorderhold', 'change_workorderhold',
    'add_stepoverride', 'change_stepoverride',
    'add_fpirecord', 'change_fpirecord',
    'add_batchexecution', 'change_batchexecution',
    # DWI runtime — completions + per-node responses + gate completions
    'add_substepcompletion', 'change_substepcompletion',
    'add_substepgatecompletion', 'change_substepgatecompletion',
    'add_substepresponse', 'change_substepresponse',
    # Reman — receive + work cores, and record what teardown found.
    #
    # `grade_component` stays here: the tech with the part in their hand is the one
    # who can see its condition, and recording an observation is not the same act as
    # acting on it. What moved out is accept/reject — see
    # COMPONENT_DISPOSITION_PERMISSIONS.
    'add_core', 'change_core',
    'start_disassembly', 'complete_disassembly', 'scrap_core',
    'grade_component',
    'add_harvestedcomponent', 'change_harvestedcomponent',
    # Materials & BOM usage
    'add_materiallot', 'change_materiallot',
    'add_materialusage', 'change_materialusage',
    'add_materialstaging', 'change_materialstaging',
    'add_materialstagingline', 'change_materialstagingline',
    'add_assemblyusage', 'change_assemblyusage',
    # Equipment & Calibration
    'add_equipments', 'change_equipments',
    'add_equipmenttype', 'change_equipmenttype',
    # (Calibration records are CALIBRATION_RECORD_WRITE — evidence, not equipment config.)
    # Scheduling & time. NOT here: work-centers (routing master data → AUTHORING;
    # changing a WC's kind re-routes whole surfaces) and shifts (solver working
    # windows → SCHEDULING_PLANNER, with the rest of the calendar inputs).
    'add_scheduleslot', 'change_scheduleslot',
    'add_downtimeevent', 'change_downtimeevent',
    'add_timeentry', 'change_timeentry',
    # Milestones & life tracking. delete_milestone: the milestones editor has
    # a remove button (DELETE soft-archives via SecureModel.delete); templates
    # have no delete UI and stay delete-ungranted.
    'add_milestone', 'change_milestone', 'delete_milestone',
    'add_milestonetemplate', 'change_milestonetemplate',
    # (Life-limit definitions and their part-type links are LIFE_LIMIT_WRITE.)
    'add_lifetracking', 'change_lifetracking',
    # Quality records
    'add_qualityreports', 'change_qualityreports',
    'add_qualityerrorslist', 'change_qualityerrorslist',
    'add_qualityreportdefect', 'change_qualityreportdefect',
    'add_quarantinedisposition', 'change_quarantinedisposition',
    # Supplier quality / part approval (records managed by QA; delete is opted
    # out — retired via status, not destroyed. `approve_*` live in SOD below.)
    'add_supplierqualification', 'change_supplierqualification',
    'add_partapproval', 'change_partapproval',
    'add_qualityreportequipment', 'change_qualityreportequipment',
    'add_stepexecutionequipment', 'change_stepexecutionequipment',
    'add_qualityreportpersonnel', 'change_qualityreportpersonnel',
    # CAPA & RCA — anyone can help fill in a draft (change_capa); raising a
    # new CAPA (initiate_capa) is granted separately per role. Approval verbs
    # are SoD-gated.
    'add_capa', 'change_capa',
    'add_capatasks', 'change_capatasks',
    'add_capataskassignee', 'change_capataskassignee',
    'add_capaverification', 'change_capaverification',
    'add_rcarecord', 'change_rcarecord', 'conduct_rca',
    'add_fishbone', 'change_fishbone',
    'add_fivewhys', 'change_fivewhys',
    'add_rootcause', 'change_rootcause',
    # Measurements & SPC — operators record step measurements via the
    # bulk-record endpoint (POST → add_); change/delete stay immutable
    'add_measurementresult',
    'add_stepexecutionmeasurement',
    # (SPC baselines — frozen control limits — are SPC_BASELINE_WRITE.)
    # Documents & 3D — records in/out; deletion + classification are gated
    'add_documents', 'change_documents',
    # Document associations (attach/detach a doc to additional entities).
    # Both verbs are operational: linking is the natural counterpart to
    # unlinking, so the roles that attach can also detach. (`change_documentlink`
    # is intentionally never granted — links are immutable, managed via
    # attach=add / detach=delete only.)
    'add_documentlink', 'delete_documentlink',
    'add_threedmodel', 'change_threedmodel',
    'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations',
    # Approvals — route for approval + respond; workflow admin is gated.
    # Responses are e-signature records: DB-immutable once written (add only;
    # delegation is a crud-exempt action gated on respond_to_approval).
    'add_approvalrequest', 'change_approvalrequest',
    'respond_to_approval',
    # Sampling rules are SAMPLING_RULE_WRITE (quality doers, not every staff role);
    # deletes are manager-tier.
    # Process change — anyone can raise/edit/submit a change request. Note:
    # the `propose` action also requires add_processes (it forks a draft
    # process), and approve/reject additionally gate on change_processes —
    # so deciding a PCR stays with authoring roles even though the PCR row
    # itself is broadly writable.
    'add_processchangerequest', 'change_processchangerequest',
    # (Training records are TRAINING_RECORD_WRITE — qualification evidence, not operational.)
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
    'add_parttypes', 'change_parttypes', 'delete_parttypes', 'change_parttype_sourcing',
    # Raw-material master data (like part-type master data — change-controlled)
    'add_material', 'change_material', 'delete_material',
    # The managed list of storage locations receiving offers.
    'add_storagelocation', 'change_storagelocation', 'delete_storagelocation',
    # Work-centers: routing master data — a WC's `kind` is the surface
    # discriminator (operator queue / QA inbox / receiving / OSP), so editing
    # one re-routes work the way editing a process does. Authoring tier, not
    # broad operational write. (delete_workcenter stays manager-tier.)
    'add_workcenter', 'change_workcenter',
    'add_measurementdefinition', 'change_measurementdefinition', 'delete_measurementdefinition',
    'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement',
    # BOM definitions
    'add_bom', 'change_bom', 'delete_bom',
    'add_bomline', 'change_bomline', 'delete_bomline',
    'add_disassemblybomline', 'change_disassemblybomline', 'delete_disassemblybomline',
    # Rebuild scope: what work a finding implies, and what a named rebuild level
    # includes. Engineering judgment like the BOM it sits beside, not operational.
    'add_repaircode', 'change_repaircode', 'delete_repaircode',
    'add_rebuildscopepreset', 'change_rebuildscopepreset', 'delete_rebuildscopepreset',
    # Controlled documents — deletion + categories (add/change of documents is broad)
    'delete_documents', 'delete_threedmodel',
    'add_documenttype', 'change_documenttype', 'delete_documenttype',
    # Approval workflow authoring
    'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate',
    'create_approval_template', 'manage_approval_workflow',
    # Training program definitions
    'add_trainingtype', 'change_trainingtype', 'delete_trainingtype',
    'add_trainingrequirement', 'change_trainingrequirement', 'delete_trainingrequirement',
    # Job roles (HR / competency profiles)
    'add_jobrole', 'change_jobrole', 'delete_jobrole',
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
    # Deciding a step override (it lets a part past a blocker) — never self-approved.
    'approve_stepoverride',
    # Rejecting a whole lot back to the vendor (VDMR). A tenant may also grant it to
    # its inspectors' group; without it an inspector's whole-lot reject is a request.
    'reject_whole_lot',
    # Supplier quality / part approval grant authority (the `grant` action's
    # marker perm) — QA Manager / Tenant Admin tier, like other approve verbs.
    'approve_supplierqualification', 'approve_partapproval',
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

# Training gate override: authorize an operator to START work they are not yet
# qualified for (the warn + supervisor-override gate on claim / work-start). The
# person on the line can't clear their own competency gap; a lead / manager
# pushes it through with a logged reason (persisted on
# StepExecution.training_authorization). Supervisor tier — same distribution as
# decision resolution / FPI sign-off, deliberately withheld from the line
# Operator. This is the "override / waive authority" the Shift Lead preset
# comment anticipated.
TRAINING_GATE_OVERRIDE_PERMISSIONS = [
    'override_training_gate',
]

# Writing a training record certifies someone as qualified — the evidence the training
# gate, "prove qualification before starting" and ISO 9001 7.2 all read. It used to sit
# in STAFF_OPERATIONAL_WRITE, so an operator could award themselves a certification.
# Held by the same tier as the gate override plus the authoring roles; withheld from
# Operator and QA Inspector (an inspector who can't waive the gate once shouldn't be
# able to certify standing qualification) and from Purchasing. Delete stays in
# MANAGER_DELETE_PERMISSIONS.
TRAINING_RECORD_WRITE = [
    'add_trainingrecord', 'change_trainingrecord',
]

# Quality-control records that sat in STAFF_OPERATIONAL_WRITE, so an operator could
# write them (each proven by probing as an operator, 2026-10-06):
# - a calibration record — a PASS also returns OUT_OF_SERVICE equipment to service;
# - a sampling rule set / rule — e.g. AQL 1.0 -> 6.5, severity NORMAL -> REDUCED;
# - a life-limit definition — e.g. a hard limit -> 999999.
# Withheld from Operator (the people these controls constrain) and Purchasing.
# Narrowed further (user decision 2026-10-06): sampling rules are a quality decision —
# QA Manager, QA Inspector, Tenant Admin; life limits are an engineering specification
# — Engineering plus those quality roles. Calibration and SPC baselines stay with every
# other staff role.
# Supplier qualifications and part approvals don't need this: they create PENDING and
# only the approve_*-gated `grant` gives them force — the pattern these should follow.
CALIBRATION_RECORD_WRITE = [
    'add_calibrationrecord', 'change_calibrationrecord',
]
SAMPLING_RULE_WRITE = [
    'add_samplingrule', 'change_samplingrule',
    'add_samplingruleset', 'change_samplingruleset',
]
# Frozen SPC control limits: quality planning like sampling rules, not measurement
# entry. The viewset also used to skip model permissions entirely (any tenant user).
SPC_BASELINE_WRITE = [
    'add_spcbaseline', 'change_spcbaseline',
]
LIFE_LIMIT_WRITE = [
    'add_lifelimitdefinition', 'change_lifelimitdefinition',
    # The link IS the limit's application: unlinking stops a harvested component
    # inheriting its core's accumulated life (reman _transfer_life_tracking) and drops
    # a lot's per-type shelf life to the default — so it travels with the definition.
    # delete_: the part type page's Life Limits panel removes a link (soft delete;
    # linking the pair again revives it).
    'add_parttypelifelimit', 'change_parttypelifelimit', 'delete_parttypelifelimit',
]

# First Piece Inspection buy-off: who may pass / fail / waive an FPI. Setup
# verification must be independent of the operator who ran the first piece, so
# this goes to the QA / lead / manager tier (same distribution as decision
# resolution) and is deliberately withheld from the Operator role.
FPI_SIGNOFF_PERMISSIONS = [
    'sign_off_fpi',
]

# Harvested-component disposition: putting a used part back into the supply of parts
# that go into customer product, or destroying it. Same distribution as FPI sign-off
# and decision resolution — QA / lead / manager tier, deliberately withheld from the
# line Operator.
#
# The split is between observing and acting, not between production and quality. The
# teardown tech keeps `grade_component` (STAFF_OPERATIONAL_WRITE) because they are
# holding the part and are the only one who can see its condition. Accepting it into
# inventory is a different act: from that moment the component is available to be
# built into someone's injector on the strength of that judgement, and AS9100 asks for
# the authority to assign a disposition to be *defined* rather than incidental to
# whoever happened to run teardown. Rejecting is the same act in the other direction —
# it destroys value and is equally a disposition.
COMPONENT_DISPOSITION_PERMISSIONS = [
    'accept_component', 'reject_component',
]

# Voiding a substep completion: retracting a record of work someone else
# signed. QA Inspector, QA Manager, and Tenant Admin — deliberately withheld
# from Shift Lead and Production Manager as well as the Operator, because this
# is a quality-record judgement rather than a production override. Tenant Admin
# holds it for the same reason it holds every other marker perm: the tenant's
# administrator must be able to correct a bad record without first granting
# themselves the permission to do so.
#
# It needs its own perm because the CRUD default for a POST action is
# `add_substepcompletion`, which every role holds — including the Operator
# whose completion is being invalidated. And the act has teeth: the advancement
# gate ignores a voided row, so the part blocks until the work is redone, and
# on an unsplit lot that holds the entire lot.
VOID_COMPLETION_PERMISSIONS = [
    'void_substepcompletion',
]

# Record retention: deleting operational records is manager-tier only. Line
# roles void / supersede / archive, never delete. (Authoring artifacts delete
# via AUTHORING_PERMISSIONS; soft-delete-only models grant no delete at all —
# see test_permission_coverage.py.)
MANAGER_DELETE_PERMISSIONS = [
    'delete_orders', 'delete_orderline', 'delete_workorder', 'delete_parts',
    'delete_stepexecution',
    'delete_substepcompletion', 'delete_substepgatecompletion', 'delete_substepresponse',
    'delete_core', 'delete_harvestedcomponent', 'delete_rebuildslotoverride',
    'delete_materiallot', 'delete_materialusage', 'delete_materialstaging',
    'delete_materialstagingline',
    'delete_assemblyusage',
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
    # Work-center membership = which stations a user is eligible at (ISA-95
    # PersonnelClass eligibility). Managed by the same tier that handles other
    # access administration.
    'add_userworkcentermembership', 'change_userworkcentermembership',
    'delete_userworkcentermembership',
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
    # The tenant/customer rule + schedule viewsets are gated by TenantModelPermissions
    # and the notification settings UI ships delete buttons, so DELETE (a soft
    # archive via SecureModel.delete) must be reachable by the managing roles.
    'delete_notificationrule', 'delete_notificationschedule',
    # External contacts are the customer-side recipients of customer-scoped
    # rules — the same configuration, managed by the same roles.
    'view_externalcontact', 'add_externalcontact',
    'change_externalcontact', 'delete_externalcontact',
]

# Authoring shift notes (floor handoff) = the supervisor tier (Shift Lead +
# Production Manager + Tenant Admin), NOT line operators. No delete_ — notes
# soft-delete via void (retract), so retract is gated by change_shiftnote.
SHIFT_NOTE_AUTHOR_PERMISSIONS = [
    'add_shiftnote', 'change_shiftnote',
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

# CP-SAT scheduler "planner" authority: run the solver + operator dispatch + pin,
# and author the scheduler's inputs (timings, machine affinities, changeovers,
# fixtures, config, continuous machines). Granted to planning roles (Tenant Admin,
# Production Manager). Solve creates a ScheduleResult (add_scheduleresult); dispatch
# and pin mutate tasks (change_scheduledtask). ScheduleResult is otherwise
# solver/service-written (change/delete ungranted) and ScheduledTask add/delete are
# solver-managed — see the opt-outs in test_permission_coverage.py.
SCHEDULING_PLANNER_PERMISSIONS = [
    'add_scheduleresult',        # run the solver
    'change_scheduledtask',      # operator dispatch + pin/unpin
    # delete_ on the three setup tables: their CRUD endpoints (StepTimings,
    # StepEquipmentAffinities, WorkCenterChangeovers) expose DELETE, and removing a
    # machine's eligibility or a changeover cell is a real planner edit (DELETE
    # soft-archives via SecureModel.delete).
    'add_steptiming', 'change_steptiming', 'delete_steptiming',
    'add_stepequipmentaffinity', 'change_stepequipmentaffinity', 'delete_stepequipmentaffinity',
    'add_workcenterchangeover', 'change_workcenterchangeover', 'delete_workcenterchangeover',
    # delete_fixture: the scheduling settings UI has a fixture remove button
    # (DELETE soft-archives via SecureModel.delete).
    'add_fixture', 'change_fixture', 'delete_fixture',
    'add_optimizationconfig', 'change_optimizationconfig',
    'add_continuousmachine', 'change_continuousmachine',
    # Labor/plant calendar inputs the solver reads (shifts, overtime,
    # holidays/shutdowns). Shifts define the solver's working windows, so they
    # sit with the other calendar inputs rather than broad operational write.
    'add_shift', 'change_shift',
    # Calendar entries are lightweight planning inputs: a mis-entered PTO day
    # or closure is removable from the calendar UI (DELETE soft-archives via
    # SecureModel.delete; auditlog keeps the trail). Without delete_ the UI's
    # remove buttons 403 for everyone.
    'add_laborcalendarblock', 'change_laborcalendarblock', 'delete_laborcalendarblock',
    'add_overtimewindow', 'change_overtimewindow', 'delete_overtimewindow',
    'add_plantcalendarexception', 'change_plantcalendarexception', 'delete_plantcalendarexception',
]

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
            'apply_cyclecount',
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *CALIBRATION_RECORD_WRITE,
            *SAMPLING_RULE_WRITE,
            *LIFE_LIMIT_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
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
            *COMPONENT_DISPOSITION_PERMISSIONS,
            # Void an erroneous substep completion (quality-record judgement)
            *VOID_COMPLETION_PERMISSIONS,
            # Override the training gate to start unqualified work (logged)
            *TRAINING_GATE_OVERRIDE_PERMISSIONS,
            # Author shift notes (floor handoff)
            *SHIFT_NOTE_AUTHOR_PERMISSIONS,
            # Formally raise a CAPA
            'initiate_capa',
            # Run + tune the CP-SAT scheduler (solve/dispatch/pin + config authoring)
            *SCHEDULING_PLANNER_PERMISSIONS,
        ],
    },

    # -------------------------------------------------------------------------
    # QA MANAGER - Quality management, approvals, CAPA control
    # -------------------------------------------------------------------------
    'qa_manager': {
        'name': 'QA Manager',
        'description': 'Quality management, approvals, CAPA control',
        'permissions': [
            'apply_cyclecount',
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *CALIBRATION_RECORD_WRITE,
            *SAMPLING_RULE_WRITE,
            *LIFE_LIMIT_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
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
            *COMPONENT_DISPOSITION_PERMISSIONS,
            # Void an erroneous substep completion
            *VOID_COMPLETION_PERMISSIONS,
            # Override the training gate to start unqualified work (logged)
            *TRAINING_GATE_OVERRIDE_PERMISSIONS,
            # Formally raise a CAPA
            'initiate_capa',
            # Management schedule-touch: pin/move/reassign scheduled tasks (e.g.
            # holding work for a quality issue). Solving/authoring stay with the
            # planner roles.
            'change_scheduledtask',
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
            *CALIBRATION_RECORD_WRITE,
            *SAMPLING_RULE_WRITE,
            *LIFE_LIMIT_WRITE,
            *SPC_BASELINE_WRITE,
            # Resolve (close) NCR dispositions
            *DISPOSITION_RESOLUTION_PERMISSIONS,
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
            *COMPONENT_DISPOSITION_PERMISSIONS,
            # Void an erroneous substep completion
            *VOID_COMPLETION_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Formally raise a CAPA
            'initiate_capa',
        ],
    },

    # -------------------------------------------------------------------------
    # PRODUCTION MANAGER - Production oversight
    # -------------------------------------------------------------------------
    'production_manager': {
        'name': 'Production Manager',
        'description': 'Manage production operations, work orders, scheduling',
        'permissions': [
            'apply_cyclecount',
            *SHIFT_NOTE_AUTHOR_PERMISSIONS,
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *CALIBRATION_RECORD_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
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
            *COMPONENT_DISPOSITION_PERMISSIONS,
            # Override the training gate to start unqualified work (logged)
            *TRAINING_GATE_OVERRIDE_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Formally raise a CAPA
            'initiate_capa',
            # Run + tune the CP-SAT scheduler (the production planning function)
            *SCHEDULING_PLANNER_PERMISSIONS,
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
            'apply_cyclecount',
            *SHIFT_NOTE_AUTHOR_PERMISSIONS,
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            *CALIBRATION_RECORD_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
            # Resolve (close) NCR dispositions
            *DISPOSITION_RESOLUTION_PERMISSIONS,
            # Resolve MANUAL decision-point routing (4a)
            *DECISION_RESOLUTION_PERMISSIONS,
            # Sign off (buy off) First Piece Inspections
            *FPI_SIGNOFF_PERMISSIONS,
            *COMPONENT_DISPOSITION_PERMISSIONS,
            # Override the training gate to start unqualified work (logged)
            *TRAINING_GATE_OVERRIDE_PERMISSIONS,
            # Formally raise a CAPA
            'initiate_capa',
            # Schedule floor authority: pin/move/reassign/dispatch scheduled
            # tasks on their shift (the Gantt's direct-manipulation verbs).
            # NOT the full planner bundle — solving, committing, and authoring
            # solver inputs stay with Production Manager / Tenant Admin.
            'change_scheduledtask',
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
            *CALIBRATION_RECORD_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
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
            *CALIBRATION_RECORD_WRITE,
            *LIFE_LIMIT_WRITE,
            *SPC_BASELINE_WRITE,
            *TRAINING_RECORD_WRITE,
            *AUTHORING_PERMISSIONS,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
        ],
    },

    # -------------------------------------------------------------------------
    # PURCHASING - Supplier / procurement seat
    # -------------------------------------------------------------------------
    # Owns supplier relationships: raises supplier qualifications, receives
    # material lots, adds supplier companies. Same shape as Operator/Engineering
    # structurally — base view + broad operational write + full tenant
    # visibility — with NO authoring (they don't write processes/BOMs/specs),
    # NO SoD approve verbs (`approve_supplierqualification` stays with QA),
    # NO delete (retention is manager tier), NO shop-floor supervisor grants
    # (FPI / training-override / shift-note authoring). If a permission isn't
    # compliance-shaped, they have it via the base bundles.
    'purchasing': {
        'name': 'Purchasing',
        'description': 'Supplier management and receiving: supplier qualification, part approvals, expected receipts and incoming lots (purchase orders stay in the ERP)',
        'permissions': [
            *STAFF_VIEW_PERMISSIONS,
            *CLASSIFIED_DOCUMENT_VIEW,
            *STAFF_OPERATIONAL_WRITE,
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # A SCAR is a CAPA against a supplier: MaterialLot.raise_scar is gated on it.
            'initiate_capa',
            # Buyers own purchased materials: lead time, preferred supplier, safety stock
            # (what the requirements report nets against).
            'add_material', 'change_material',
            # …and a bought part's sourcing (supplier, lead time, safety stock) — not
            # the part's definition, which stays with engineering.
            'change_parttype_sourcing',
            # Receiving keeps the list of places stock is put away.
            'add_storagelocation', 'change_storagelocation',
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