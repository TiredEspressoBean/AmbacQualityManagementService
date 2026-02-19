"""
Group presets for tenant initialization.

These presets define the default groups and permissions seeded when a new tenant
is created. Tenant admins can customize permissions after creation.

Permission system:
- Permissions control both ACTIONS (add, change, delete) and DATA VISIBILITY (view_*)
- Users without view_* permission fall back to Order relationship filtering
  (Order.customer and Order.viewers determine access)

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
# STANDARD VIEW PERMISSIONS - All staff can see everything
# =============================================================================
# Philosophy: Everyone should be able to see what's happening in the system.
# Write permissions are role-specific, but view permissions are universal for staff.

STAFF_VIEW_PERMISSIONS = [
    # Production
    'view_orders', 'view_workorder', 'view_parts', 'view_parttypes',
    'view_processes', 'view_steps', 'view_processstep', 'view_stepedge',
    'view_stepexecution', 'view_steptransitionlog', 'view_stepmeasurementrequirement',
    'view_companies', 'view_orderviewer', 'view_externalapiorderidentifier',
    # BOM & Materials
    'view_bom', 'view_bomline', 'view_assemblyusage', 'view_disassemblybomline',
    'view_materiallot', 'view_materialusage', 'view_harvestedcomponent',
    # Equipment & Calibration
    'view_equipments', 'view_equipmenttype', 'view_equipmentusage',
    'view_calibrationrecord',
    # Scheduling
    'view_workcenter', 'view_shift', 'view_scheduleslot', 'view_downtimeevent',
    'view_timeentry',
    # Quality
    'view_qualityreports', 'view_qualityerrorslist', 'view_qualityreportdefect',
    'view_qaapproval', 'view_quarantinedisposition',
    # CAPA & RCA
    'view_capa', 'view_capatasks', 'view_capataskassignee', 'view_capaverification',
    'view_rcarecord', 'view_fishbone', 'view_fivewhys', 'view_rootcause',
    # Measurements & SPC
    'view_measurementresult', 'view_measurementdefinition', 'view_spcbaseline',
    # Documents (not secret)
    'view_documents', 'view_documenttype', 'view_confidential_documents',
    # 3D Models & Annotations
    'view_threedmodel', 'view_heatmapannotations',
    # Approvals
    'view_approvaltemplate', 'view_approvalrequest', 'view_approvalresponse',
    'view_approverassignment', 'view_groupapproverassignment',
    # Sampling
    'view_samplingrule', 'view_samplingruleset', 'view_samplinganalytics', 'view_samplingauditlog',
    # Training
    'view_trainingrecord', 'view_trainingtype', 'view_trainingrequirement',
    # Reports
    'view_generatedreport',
    # AI Chat & Embeddings
    'view_chatsession', 'view_docchunk',
    # Admin/Config (view only)
    'view_facility', 'view_archivereason', 'view_user', 'view_userinvitation',
    'view_permissionchangelog',
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
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # User management within tenant
            'add_user', 'change_user', 'delete_user', 'view_user',
            'add_userinvitation', 'change_userinvitation', 'delete_userinvitation', 'view_userinvitation',
            'add_userrole', 'change_userrole', 'delete_userrole', 'view_userrole',
            # Group management within tenant
            'add_tenantgroup', 'change_tenantgroup', 'delete_tenantgroup', 'view_tenantgroup',
            'add_tenantgroupmembership', 'change_tenantgroupmembership', 'delete_tenantgroupmembership', 'view_tenantgroupmembership',
            # Facility management
            'add_facility', 'change_facility', 'delete_facility', 'view_facility',
            # Archive reasons
            'add_archivereason', 'change_archivereason', 'delete_archivereason', 'view_archivereason',
            # View permission audit logs
            'view_permissionchangelog',
            # Full production access
            'add_orders', 'change_orders', 'delete_orders', 'view_orders',
            'add_workorder', 'change_workorder', 'delete_workorder', 'view_workorder',
            'add_parts', 'change_parts', 'delete_parts', 'view_parts',
            'add_parttypes', 'change_parttypes', 'delete_parttypes', 'view_parttypes',
            'add_processes', 'change_processes', 'delete_processes', 'view_processes',
            'add_steps', 'change_steps', 'delete_steps', 'view_steps',
            'add_processstep', 'change_processstep', 'delete_processstep', 'view_processstep',
            'add_stepedge', 'change_stepedge', 'delete_stepedge', 'view_stepedge',
            'add_stepexecution', 'change_stepexecution', 'delete_stepexecution', 'view_stepexecution',
            'add_steptransitionlog', 'change_steptransitionlog', 'delete_steptransitionlog', 'view_steptransitionlog',
            'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement', 'view_stepmeasurementrequirement',
            'add_companies', 'change_companies', 'delete_companies', 'view_companies',
            'add_orderviewer', 'change_orderviewer', 'delete_orderviewer', 'view_orderviewer',
            'add_externalapiorderidentifier', 'change_externalapiorderidentifier', 'delete_externalapiorderidentifier', 'view_externalapiorderidentifier',
            # Full BOM & Materials
            'add_bom', 'change_bom', 'delete_bom', 'view_bom',
            'add_bomline', 'change_bomline', 'delete_bomline', 'view_bomline',
            'add_assemblyusage', 'change_assemblyusage', 'delete_assemblyusage', 'view_assemblyusage',
            'add_disassemblybomline', 'change_disassemblybomline', 'delete_disassemblybomline', 'view_disassemblybomline',
            'add_materiallot', 'change_materiallot', 'delete_materiallot', 'view_materiallot',
            'add_materialusage', 'change_materialusage', 'delete_materialusage', 'view_materialusage',
            'add_harvestedcomponent', 'change_harvestedcomponent', 'delete_harvestedcomponent', 'view_harvestedcomponent',
            # Full Equipment & Calibration
            'add_equipments', 'change_equipments', 'delete_equipments', 'view_equipments',
            'add_equipmenttype', 'change_equipmenttype', 'delete_equipmenttype', 'view_equipmenttype',
            'add_equipmentusage', 'change_equipmentusage', 'delete_equipmentusage', 'view_equipmentusage',
            'add_calibrationrecord', 'change_calibrationrecord', 'delete_calibrationrecord', 'view_calibrationrecord',
            # Full Scheduling
            'add_workcenter', 'change_workcenter', 'delete_workcenter', 'view_workcenter',
            'add_shift', 'change_shift', 'delete_shift', 'view_shift',
            'add_scheduleslot', 'change_scheduleslot', 'delete_scheduleslot', 'view_scheduleslot',
            'add_downtimeevent', 'change_downtimeevent', 'delete_downtimeevent', 'view_downtimeevent',
            'add_timeentry', 'change_timeentry', 'delete_timeentry', 'view_timeentry',
            # Full Quality
            'add_qualityreports', 'change_qualityreports', 'delete_qualityreports', 'view_qualityreports',
            'approve_qualityreports', 'approve_own_qualityreports',
            'add_qualityerrorslist', 'change_qualityerrorslist', 'delete_qualityerrorslist', 'view_qualityerrorslist',
            'add_qualityreportdefect', 'change_qualityreportdefect', 'delete_qualityreportdefect', 'view_qualityreportdefect',
            'add_qaapproval', 'change_qaapproval', 'delete_qaapproval', 'view_qaapproval',
            'add_quarantinedisposition', 'change_quarantinedisposition', 'delete_quarantinedisposition', 'view_quarantinedisposition',
            'approve_disposition', 'close_disposition',
            # Full CAPA & RCA
            'add_capa', 'change_capa', 'delete_capa', 'view_capa',
            'initiate_capa', 'approve_capa', 'close_capa', 'verify_capa',
            'add_capatasks', 'change_capatasks', 'delete_capatasks', 'view_capatasks',
            'add_capataskassignee', 'change_capataskassignee', 'delete_capataskassignee', 'view_capataskassignee',
            'add_capaverification', 'change_capaverification', 'delete_capaverification', 'view_capaverification',
            'add_rcarecord', 'change_rcarecord', 'delete_rcarecord', 'view_rcarecord',
            'conduct_rca', 'review_rca',
            'add_fishbone', 'change_fishbone', 'delete_fishbone', 'view_fishbone',
            'add_fivewhys', 'change_fivewhys', 'delete_fivewhys', 'view_fivewhys',
            'add_rootcause', 'change_rootcause', 'delete_rootcause', 'view_rootcause',
            # Full Measurements & SPC
            'add_measurementresult', 'change_measurementresult', 'delete_measurementresult', 'view_measurementresult',
            'add_measurementdefinition', 'change_measurementdefinition', 'delete_measurementdefinition', 'view_measurementdefinition',
            'add_spcbaseline', 'change_spcbaseline', 'delete_spcbaseline', 'view_spcbaseline',
            # Full Documents (including secret)
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            'view_confidential_documents', 'view_restricted_documents', 'view_secret_documents',
            'classify_documents',
            'add_documenttype', 'change_documenttype', 'delete_documenttype', 'view_documenttype',
            # Full 3D Models & Annotations
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel', 'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
            # Full Approvals
            'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate', 'view_approvaltemplate',
            'add_approvalrequest', 'change_approvalrequest', 'delete_approvalrequest', 'view_approvalrequest',
            'add_approvalresponse', 'change_approvalresponse', 'delete_approvalresponse', 'view_approvalresponse',
            'create_approval_template', 'manage_approval_workflow', 'respond_to_approval',
            'add_approverassignment', 'change_approverassignment', 'delete_approverassignment', 'view_approverassignment',
            'add_groupapproverassignment', 'change_groupapproverassignment', 'delete_groupapproverassignment', 'view_groupapproverassignment',
            # Full Sampling
            'add_samplingrule', 'change_samplingrule', 'delete_samplingrule', 'view_samplingrule',
            'add_samplingruleset', 'change_samplingruleset', 'delete_samplingruleset', 'view_samplingruleset',
            'add_samplinganalytics', 'change_samplinganalytics', 'delete_samplinganalytics', 'view_samplinganalytics',
            'add_samplingauditlog', 'change_samplingauditlog', 'delete_samplingauditlog', 'view_samplingauditlog',
            # Full Training
            'add_trainingrecord', 'change_trainingrecord', 'delete_trainingrecord', 'view_trainingrecord',
            'add_trainingtype', 'change_trainingtype', 'delete_trainingtype', 'view_trainingtype',
            'add_trainingrequirement', 'change_trainingrequirement', 'delete_trainingrequirement', 'view_trainingrequirement',
            # Full Reports
            'add_generatedreport', 'change_generatedreport', 'delete_generatedreport', 'view_generatedreport',
            # Full AI Chat & Embeddings
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            'add_docchunk', 'change_docchunk', 'delete_docchunk', 'view_docchunk',
        ],
    },

    # -------------------------------------------------------------------------
    # QA MANAGER - Quality management, approvals, CAPA control
    # -------------------------------------------------------------------------
    'qa_manager': {
        'name': 'QA Manager',
        'description': 'Quality management, approvals, CAPA control',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Quality Reports - full CRUD + approval
            'add_qualityreports', 'change_qualityreports', 'delete_qualityreports', 'view_qualityreports',
            'approve_qualityreports', 'approve_own_qualityreports',
            'add_qualityerrorslist', 'change_qualityerrorslist', 'delete_qualityerrorslist', 'view_qualityerrorslist',
            'add_qualityreportdefect', 'change_qualityreportdefect', 'delete_qualityreportdefect', 'view_qualityreportdefect',
            # QA Approval records
            'add_qaapproval', 'change_qaapproval', 'delete_qaapproval', 'view_qaapproval',
            # CAPA - full CRUD + workflow
            'add_capa', 'change_capa', 'delete_capa', 'view_capa',
            'initiate_capa', 'approve_capa', 'close_capa', 'verify_capa',
            'add_capaverification', 'change_capaverification', 'delete_capaverification', 'view_capaverification',
            'add_capatasks', 'change_capatasks', 'delete_capatasks', 'view_capatasks',
            'add_capataskassignee', 'change_capataskassignee', 'delete_capataskassignee', 'view_capataskassignee',
            # RCA - full control
            'add_rcarecord', 'change_rcarecord', 'delete_rcarecord', 'view_rcarecord',
            'conduct_rca', 'review_rca',
            'add_fishbone', 'change_fishbone', 'delete_fishbone', 'view_fishbone',
            'add_fivewhys', 'change_fivewhys', 'delete_fivewhys', 'view_fivewhys',
            'add_rootcause', 'change_rootcause', 'delete_rootcause', 'view_rootcause',
            # Dispositions - full CRUD
            'add_quarantinedisposition', 'change_quarantinedisposition', 'delete_quarantinedisposition', 'view_quarantinedisposition',
            'approve_disposition', 'close_disposition',
            # Measurements & SPC
            'add_measurementresult', 'change_measurementresult', 'delete_measurementresult', 'view_measurementresult',
            'add_measurementdefinition', 'change_measurementdefinition', 'delete_measurementdefinition', 'view_measurementdefinition',
            'add_spcbaseline', 'change_spcbaseline', 'delete_spcbaseline', 'view_spcbaseline',
            # Step measurement requirements
            'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement', 'view_stepmeasurementrequirement',
            # Documents - full including classified
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            'view_confidential_documents', 'view_restricted_documents',
            'classify_documents',
            'add_documenttype', 'change_documenttype', 'delete_documenttype', 'view_documenttype',
            # 3D Models & Annotations
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel', 'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
            # Approvals - full workflow control
            'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate', 'view_approvaltemplate',
            'add_approvalrequest', 'change_approvalrequest', 'delete_approvalrequest', 'view_approvalrequest',
            'add_approvalresponse', 'change_approvalresponse', 'delete_approvalresponse', 'view_approvalresponse',
            'create_approval_template', 'manage_approval_workflow', 'respond_to_approval',
            # Approver assignments
            'add_approverassignment', 'change_approverassignment', 'delete_approverassignment', 'view_approverassignment',
            'add_groupapproverassignment', 'change_groupapproverassignment', 'delete_groupapproverassignment', 'view_groupapproverassignment',
            # Generated Reports
            'add_generatedreport', 'change_generatedreport', 'delete_generatedreport', 'view_generatedreport',
            # Training Management
            'add_trainingrecord', 'change_trainingrecord', 'delete_trainingrecord', 'view_trainingrecord',
            'add_trainingtype', 'change_trainingtype', 'delete_trainingtype', 'view_trainingtype',
            'add_trainingrequirement', 'change_trainingrequirement', 'delete_trainingrequirement', 'view_trainingrequirement',
            # Calibration
            'add_calibrationrecord', 'change_calibrationrecord', 'delete_calibrationrecord', 'view_calibrationrecord',
            # Equipment
            'add_equipments', 'change_equipments', 'delete_equipments', 'view_equipments',
            'add_equipmenttype', 'change_equipmenttype', 'delete_equipmenttype', 'view_equipmenttype',
            'add_equipmentusage', 'change_equipmentusage', 'delete_equipmentusage', 'view_equipmentusage',
            # Production - full view + some edit
            'add_orders', 'change_orders', 'delete_orders', 'view_orders',
            'add_parts', 'change_parts', 'delete_parts', 'view_parts',
            'add_workorder', 'change_workorder', 'delete_workorder', 'view_workorder',
            'view_processes', 'view_steps', 'view_parttypes',
            'view_companies',
            'view_steptransitionlog',
            # Process flow modeling
            'view_processstep', 'view_stepedge',
            # Sampling - full control including analytics
            'add_samplingrule', 'change_samplingrule', 'delete_samplingrule', 'view_samplingrule',
            'add_samplingruleset', 'change_samplingruleset', 'delete_samplingruleset', 'view_samplingruleset',
            'add_samplinganalytics', 'change_samplinganalytics', 'delete_samplinganalytics', 'view_samplinganalytics',
            'add_samplingauditlog', 'change_samplingauditlog', 'delete_samplingauditlog', 'view_samplingauditlog',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'add_docchunk', 'change_docchunk', 'delete_docchunk', 'view_docchunk',
            # Facilities - full control
            'add_facility', 'change_facility', 'delete_facility', 'view_facility',
            # Users (view team members)
            'view_user',
            # User invitations - can invite team members
            'add_userinvitation', 'change_userinvitation', 'delete_userinvitation', 'view_userinvitation',
            # Archive reasons - full control
            'add_archivereason', 'change_archivereason', 'delete_archivereason', 'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # QA INSPECTOR - Perform inspections, create quality reports
    # -------------------------------------------------------------------------
    'qa_inspector': {
        'name': 'QA Inspector',
        'description': 'Perform inspections, create quality reports, initiate CAPAs',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Quality Reports - full working access
            'add_qualityreports', 'change_qualityreports', 'delete_qualityreports', 'view_qualityreports',
            'add_qualityerrorslist', 'change_qualityerrorslist', 'view_qualityerrorslist',
            'add_qualityreportdefect', 'change_qualityreportdefect', 'view_qualityreportdefect',
            # QA Approval records
            'add_qaapproval', 'change_qaapproval', 'view_qaapproval',
            # CAPA - can initiate and work on
            'add_capa', 'change_capa', 'view_capa',
            'initiate_capa',
            'add_capaverification', 'change_capaverification', 'view_capaverification',
            'add_capatasks', 'change_capatasks', 'view_capatasks',
            'add_capataskassignee', 'change_capataskassignee', 'view_capataskassignee',
            # RCA - can conduct
            'add_rcarecord', 'change_rcarecord', 'view_rcarecord',
            'conduct_rca',
            'add_fishbone', 'change_fishbone', 'view_fishbone',
            'add_fivewhys', 'change_fivewhys', 'view_fivewhys',
            'add_rootcause', 'change_rootcause', 'view_rootcause',
            # Dispositions
            'add_quarantinedisposition', 'change_quarantinedisposition', 'view_quarantinedisposition',
            # Measurements & SPC
            'add_measurementresult', 'change_measurementresult', 'view_measurementresult',
            'view_measurementdefinition',
            'add_spcbaseline', 'change_spcbaseline', 'view_spcbaseline',
            # Step measurement requirements
            'view_stepmeasurementrequirement',
            # Calibration
            'add_calibrationrecord', 'change_calibrationrecord', 'view_calibrationrecord',
            # 3D Models & Annotations
            'add_threedmodel', 'change_threedmodel', 'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
            # Generated Reports
            'add_generatedreport', 'change_generatedreport', 'view_generatedreport',
            # Production - view + change parts
            'view_orders', 'change_parts', 'view_parts', 'view_workorder',
            'view_processes', 'view_steps', 'view_parttypes',
            'view_companies', 'view_equipments', 'view_equipmenttype',
            'add_equipmentusage', 'change_equipmentusage', 'view_equipmentusage',
            'view_steptransitionlog',
            # Process flow modeling
            'view_processstep', 'view_stepedge',
            # Documents
            'add_documents', 'change_documents', 'view_documents',
            'view_confidential_documents',
            # Approvals - can respond
            'view_approvalrequest', 'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            'view_approverassignment',
            # Sampling
            'add_samplingrule', 'change_samplingrule', 'view_samplingrule',
            'add_samplingruleset', 'change_samplingruleset', 'view_samplingruleset',
            'view_samplinganalytics',
            # Training
            'add_trainingrecord', 'change_trainingrecord', 'view_trainingrecord',
            'view_trainingrequirement', 'view_trainingtype',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
            # Facilities
            'add_facility', 'change_facility', 'view_facility',
            # Archive reasons
            'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # PRODUCTION MANAGER - Production oversight
    # -------------------------------------------------------------------------
    'production_manager': {
        'name': 'Production Manager',
        'description': 'Manage production operations, work orders, scheduling',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Orders - full CRUD
            'add_orders', 'change_orders', 'delete_orders', 'view_orders',
            # Work Orders - full CRUD
            'add_workorder', 'change_workorder', 'delete_workorder', 'view_workorder',
            # Parts - full CRUD
            'add_parts', 'change_parts', 'delete_parts', 'view_parts',
            # Processes and Steps - full CRUD
            'add_processes', 'change_processes', 'delete_processes', 'view_processes',
            'add_steps', 'change_steps', 'delete_steps', 'view_steps',
            # Process flow modeling - full CRUD
            'add_processstep', 'change_processstep', 'delete_processstep', 'view_processstep',
            'add_stepedge', 'change_stepedge', 'delete_stepedge', 'view_stepedge',
            # Part Types - full CRUD
            'add_parttypes', 'change_parttypes', 'delete_parttypes', 'view_parttypes',
            # Step Execution
            'add_stepexecution', 'change_stepexecution', 'delete_stepexecution', 'view_stepexecution',
            'add_steptransitionlog', 'change_steptransitionlog', 'delete_steptransitionlog', 'view_steptransitionlog',
            # Step measurement requirements
            'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement', 'view_stepmeasurementrequirement',
            # Equipment - full CRUD
            'add_equipments', 'change_equipments', 'delete_equipments', 'view_equipments',
            'add_equipmenttype', 'change_equipmenttype', 'delete_equipmenttype', 'view_equipmenttype',
            'add_equipmentusage', 'change_equipmentusage', 'delete_equipmentusage', 'view_equipmentusage',
            # BOM
            'add_bom', 'change_bom', 'delete_bom', 'view_bom',
            'add_bomline', 'change_bomline', 'delete_bomline', 'view_bomline',
            'add_assemblyusage', 'change_assemblyusage', 'delete_assemblyusage', 'view_assemblyusage',
            # Disassembly BOM
            'add_disassemblybomline', 'change_disassemblybomline', 'delete_disassemblybomline', 'view_disassemblybomline',
            # Harvested components (remanufacturing)
            'add_harvestedcomponent', 'change_harvestedcomponent', 'delete_harvestedcomponent', 'view_harvestedcomponent',
            # Materials
            'add_materiallot', 'change_materiallot', 'delete_materiallot', 'view_materiallot',
            'add_materialusage', 'change_materialusage', 'delete_materialusage', 'view_materialusage',
            # Scheduling
            'add_workcenter', 'change_workcenter', 'delete_workcenter', 'view_workcenter',
            'add_shift', 'change_shift', 'delete_shift', 'view_shift',
            'add_scheduleslot', 'change_scheduleslot', 'delete_scheduleslot', 'view_scheduleslot',
            'add_downtimeevent', 'change_downtimeevent', 'delete_downtimeevent', 'view_downtimeevent',
            # Time tracking
            'add_timeentry', 'change_timeentry', 'delete_timeentry', 'view_timeentry',
            # Companies - full CRUD
            'add_companies', 'change_companies', 'delete_companies', 'view_companies',
            # Order viewers (access control)
            'add_orderviewer', 'change_orderviewer', 'delete_orderviewer', 'view_orderviewer',
            # External API identifiers
            'add_externalapiorderidentifier', 'change_externalapiorderidentifier', 'delete_externalapiorderidentifier', 'view_externalapiorderidentifier',
            # Quality - full view + can report issues
            'add_qualityreports', 'change_qualityreports', 'view_qualityreports',
            'view_qualityerrorslist', 'view_qualityreportdefect',
            'view_capa', 'view_capatasks', 'view_quarantinedisposition',
            'view_capaverification', 'view_rcarecord',
            # Measurements
            'add_measurementresult', 'change_measurementresult', 'view_measurementresult',
            'add_measurementdefinition', 'change_measurementdefinition', 'view_measurementdefinition',
            # 3D Models & Annotations
            'add_threedmodel', 'change_threedmodel', 'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'view_heatmapannotations',
            # Documents
            'add_documents', 'change_documents', 'view_documents',
            'view_confidential_documents',
            # Generated Reports
            'add_generatedreport', 'change_generatedreport', 'view_generatedreport',
            # Approvals - can respond
            'view_approvalrequest', 'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            # Training - manage team training
            'add_trainingrecord', 'change_trainingrecord', 'view_trainingrecord',
            'view_trainingrequirement', 'view_trainingtype',
            # Calibration
            'add_calibrationrecord', 'change_calibrationrecord', 'view_calibrationrecord',
            # Sampling - full control including analytics
            'add_samplingrule', 'change_samplingrule', 'delete_samplingrule', 'view_samplingrule',
            'add_samplingruleset', 'change_samplingruleset', 'delete_samplingruleset', 'view_samplingruleset',
            'add_samplinganalytics', 'change_samplinganalytics', 'delete_samplinganalytics', 'view_samplinganalytics',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
            # Facilities - full control
            'add_facility', 'change_facility', 'delete_facility', 'view_facility',
            # Users (view team members)
            'view_user',
            # User invitations - can invite team members
            'add_userinvitation', 'change_userinvitation', 'delete_userinvitation', 'view_userinvitation',
            # Archive reasons
            'add_archivereason', 'change_archivereason', 'delete_archivereason', 'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # OPERATOR - Production floor work
    # -------------------------------------------------------------------------
    'operator': {
        'name': 'Operator',
        'description': 'Production floor work, inspections, data entry',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Parts - full working access
            'add_parts', 'change_parts', 'view_parts',
            # Work Orders
            'add_workorder', 'change_workorder', 'view_workorder',
            # Orders
            'view_orders',
            # Processes/Steps - view instructions
            'view_processes', 'view_steps',
            'view_parttypes',
            # Process flow modeling
            'view_processstep', 'view_stepedge',
            # Step execution & transitions
            'add_stepexecution', 'change_stepexecution', 'view_stepexecution',
            'add_steptransitionlog', 'change_steptransitionlog', 'view_steptransitionlog',
            # Step measurement requirements
            'view_stepmeasurementrequirement',
            # Equipment
            'view_equipments', 'view_equipmenttype',
            'add_equipmentusage', 'change_equipmentusage', 'view_equipmentusage',
            # Materials
            'add_materialusage', 'change_materialusage', 'view_materialusage',
            'view_materiallot',
            # BOM
            'view_bom', 'view_bomline',
            'add_assemblyusage', 'change_assemblyusage', 'view_assemblyusage',
            # Disassembly BOM
            'view_disassemblybomline',
            # Harvested components (remanufacturing)
            'add_harvestedcomponent', 'change_harvestedcomponent', 'view_harvestedcomponent',
            # Time tracking
            'add_timeentry', 'change_timeentry', 'view_timeentry',
            # Measurements
            'add_measurementresult', 'change_measurementresult', 'view_measurementresult',
            'view_measurementdefinition',
            # Quality Reports - operators report issues
            'add_qualityreports', 'change_qualityreports', 'view_qualityreports',
            'add_qualityreportdefect', 'change_qualityreportdefect', 'view_qualityreportdefect',
            'view_qualityerrorslist',
            # Dispositions
            'add_quarantinedisposition', 'change_quarantinedisposition', 'view_quarantinedisposition',
            # CAPA - view and work on tasks
            'view_capa', 'view_capatasks', 'change_capatasks',
            # 3D Models & Annotations
            'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'view_heatmapannotations',
            # Documents
            'add_documents', 'view_documents',
            # Generated Reports
            'add_generatedreport', 'view_generatedreport',
            # Companies
            'view_companies',
            # Training
            'add_trainingrecord', 'view_trainingrecord', 'view_trainingrequirement',
            # Calibration
            'view_calibrationrecord',
            # Approvals
            'view_approvalrequest', 'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            # Scheduling
            'view_shift', 'view_scheduleslot', 'view_workcenter',
            'add_downtimeevent', 'change_downtimeevent', 'view_downtimeevent',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
            # Facilities
            'add_facility', 'change_facility', 'view_facility',
            # Archive reasons
            'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # DOCUMENT CONTROLLER - Manage controlled documents
    # -------------------------------------------------------------------------
    'document_controller': {
        'name': 'Document Controller',
        'description': 'Manage controlled documents, revisions, and approvals',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Documents - full CRUD including classified + classification control
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            'view_confidential_documents', 'view_restricted_documents', 'view_secret_documents',
            'classify_documents',
            # Document Types - manage document categories
            'add_documenttype', 'change_documenttype', 'delete_documenttype', 'view_documenttype',
            # 3D Models - full control
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel', 'view_threedmodel',
            # Heatmap Annotations
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
            # Generated Reports
            'add_generatedreport', 'change_generatedreport', 'delete_generatedreport', 'view_generatedreport',
            # Approval templates - full workflow control
            'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate', 'view_approvaltemplate',
            'add_approvalrequest', 'change_approvalrequest', 'delete_approvalrequest', 'view_approvalrequest',
            'add_approvalresponse', 'change_approvalresponse', 'view_approvalresponse',
            'create_approval_template', 'manage_approval_workflow', 'respond_to_approval',
            # Training documentation
            'add_trainingtype', 'change_trainingtype', 'delete_trainingtype', 'view_trainingtype',
            'add_trainingrequirement', 'change_trainingrequirement', 'view_trainingrequirement',
            'add_trainingrecord', 'change_trainingrecord', 'view_trainingrecord',
            # Quality - view for document context
            'view_qualityreports', 'view_capa', 'view_quarantinedisposition',
            'view_rcarecord', 'view_capatasks',
            # Production context - broad view
            'view_orders', 'view_parts', 'view_workorder',
            'add_processes', 'change_processes', 'view_processes',
            'add_steps', 'change_steps', 'view_steps',
            'view_parttypes',
            'view_companies', 'view_equipments', 'view_equipmenttype',
            'view_measurementdefinition', 'view_measurementresult',
            'view_calibrationrecord',
            # Process flow modeling
            'view_processstep', 'view_stepedge',
            # BOM for documentation
            'view_bom', 'view_bomline',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding) - full control for document managers
            'add_docchunk', 'change_docchunk', 'delete_docchunk', 'view_docchunk',
            # Facilities
            'add_facility', 'change_facility', 'view_facility',
            # Archive reasons - full control for document management
            'add_archivereason', 'change_archivereason', 'delete_archivereason', 'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # ENGINEERING - Design and engineering changes
    # -------------------------------------------------------------------------
    'engineering': {
        'name': 'Engineering',
        'description': 'Engineering changes, drawing control, design work',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Documents - full control
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            'view_confidential_documents', 'view_restricted_documents',
            'add_documenttype', 'change_documenttype', 'view_documenttype',
            # 3D Models - full control
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel', 'view_threedmodel',
            # Heatmap Annotations
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
            # Part Types - full control
            'add_parttypes', 'change_parttypes', 'delete_parttypes', 'view_parttypes',
            # Processes - full control
            'add_processes', 'change_processes', 'delete_processes', 'view_processes',
            'add_steps', 'change_steps', 'delete_steps', 'view_steps',
            # Process flow modeling - full control
            'add_processstep', 'change_processstep', 'delete_processstep', 'view_processstep',
            'add_stepedge', 'change_stepedge', 'delete_stepedge', 'view_stepedge',
            # Measurement Definitions
            'add_measurementdefinition', 'change_measurementdefinition', 'delete_measurementdefinition', 'view_measurementdefinition',
            'view_measurementresult',
            # Step measurement requirements - full control
            'add_stepmeasurementrequirement', 'change_stepmeasurementrequirement', 'delete_stepmeasurementrequirement', 'view_stepmeasurementrequirement',
            # BOM - full control
            'add_bom', 'change_bom', 'delete_bom', 'view_bom',
            'add_bomline', 'change_bomline', 'delete_bomline', 'view_bomline',
            # Disassembly BOM - full control
            'add_disassemblybomline', 'change_disassemblybomline', 'delete_disassemblybomline', 'view_disassemblybomline',
            # Equipment specs
            'add_equipmenttype', 'change_equipmenttype', 'view_equipmenttype',
            'view_equipments',
            # CAPA - can initiate and participate
            'add_capa', 'change_capa', 'view_capa',
            'initiate_capa',
            'view_capatasks', 'change_capatasks',
            'view_capaverification',
            # RCA - full participation
            'add_rcarecord', 'change_rcarecord', 'view_rcarecord',
            'conduct_rca',
            'add_fishbone', 'change_fishbone', 'view_fishbone',
            'add_fivewhys', 'change_fivewhys', 'view_fivewhys',
            'add_rootcause', 'change_rootcause', 'view_rootcause',
            # Production
            'add_orders', 'change_orders', 'view_orders',
            'add_parts', 'change_parts', 'view_parts',
            'add_workorder', 'change_workorder', 'view_workorder',
            'view_companies',
            # Quality
            'add_qualityreports', 'change_qualityreports', 'view_qualityreports',
            'view_quarantinedisposition',
            # Approvals
            'add_approvaltemplate', 'change_approvaltemplate', 'view_approvaltemplate',
            'add_approvalrequest', 'change_approvalrequest', 'view_approvalrequest',
            'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            # Generated Reports
            'add_generatedreport', 'change_generatedreport', 'view_generatedreport',
            # Training
            'view_trainingrecord', 'view_trainingrequirement', 'view_trainingtype',
            # Calibration
            'view_calibrationrecord',
            # AI Chat
            'add_chatsession', 'change_chatsession', 'delete_chatsession', 'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
            # Facilities
            'add_facility', 'change_facility', 'view_facility',
            # Archive reasons
            'view_archivereason',
        ],
    },

    # -------------------------------------------------------------------------
    # AUDITOR - Read-only with anonymized sensitive data
    # -------------------------------------------------------------------------
    'auditor': {
        'name': 'Auditor',
        'description': 'Read-only access for audits, anonymized sensitive data',
        'permissions': [
            # Full tenant visibility (sees all data, not just relationship-filtered)
            'full_tenant_access',
            # Production - view all
            'view_orders', 'view_parts', 'view_workorder',
            'view_processes', 'view_steps', 'view_parttypes',
            'view_companies', 'view_equipments', 'view_equipmenttype',
            # Process flow modeling
            'view_processstep', 'view_stepedge',
            # Step measurement requirements
            'view_stepmeasurementrequirement',
            # Quality - view all
            'view_qualityreports', 'view_capa', 'view_rcarecord', 'view_capatasks',
            'view_quarantinedisposition', 'view_capaverification',
            'view_qaapproval',
            # Measurements
            'view_measurementresult', 'view_measurementdefinition',
            # BOM
            'view_bom', 'view_bomline', 'view_disassemblybomline',
            # Harvested components
            'view_harvestedcomponent',
            # Documents
            'view_documents', 'view_documenttype',
            # Approvals
            'view_approvalrequest', 'view_approvalresponse', 'view_approvaltemplate',
            # Order viewers
            'view_orderviewer',
            # Sampling
            'view_samplingrule', 'view_samplingruleset',
            # Traceability
            'view_steptransitionlog',
            # Training & Calibration - compliance evidence
            'view_trainingrecord', 'view_trainingtype', 'view_trainingrequirement',
            'view_calibrationrecord',
            # Generated Reports
            'view_generatedreport',
            # AI Chat (view only for audit trail)
            'view_chatsession',
            # Doc chunks (AI embedding)
            'view_docchunk',
            # Facilities
            'view_facility',
            # Sampling audit logs (compliance)
            'view_samplingauditlog', 'view_samplinganalytics',
            # Permission change logs (compliance)
            'view_permissionchangelog',
            # Archive reasons (compliance)
            'view_archivereason',
            # User invitations (audit trail)
            'view_userinvitation',
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
            # Order viewers (see who has access)
            'view_orderviewer',
            # Documents linked to their orders
            'view_documents',
            # Quality info for their orders
            'view_qualityreports',
            # Approvals - can respond to customer approval requests (use-as-is, etc.)
            'view_approvalrequest', 'add_approvalresponse', 'view_approvalresponse',
            'respond_to_approval',
            # AI Chat - customers can use AI assistance
            'add_chatsession', 'change_chatsession', 'view_chatsession',
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
