"""What happens to every link to a versioned record when a new version is made.

A new version of a record is the SAME thing, updated — Mill 3 is still Mill 3 after its
record changes. A new version is a new row with a new id, though, so every row that
pointed at the old id needs a decision. Left to each model to remember, links silently
stayed on history: a machine edit left its calibrations behind (the current machine read
as uncalibrated and the scheduler dropped it), its planned downtime invisible, its step
eligibility on the old row.

So each link declares one policy here, and `apply_version_links` (called by
`SecureModel.create_new_version`) carries it out. `test_version_links` fails when a link
to a versioned model has no policy — the next person to add one has to decide.

Policies
- FOLLOWS  — re-pointed to the new version. Master data (machines, suppliers, part
             types, work centers, shifts, equipment types): EVERY link, history too — it
             is the same thing, and its record's content doesn't change what happened
             to it. Specifications: their configuration.
- STAYS    — left on the old version: records made or measured AGAINST a specification's
             content (a measurement result against a tolerance, a part sampled under a
             ruleset). Readers that want the whole history compare across the chain.
- COPIES   — cloned onto the new version, the original kept. A step version belongs to a
             draft process revision while the old step stays in force, so the step's
             scheduling configuration (eligibility, changeovers, fixtures) is copied,
             not moved.
- MODEL    — the model's own create_new_version override carries it (children of a
             composite, or links a service re-points with extra rules).
- MANAGED  — change control owns it (process and step revision, work orders built to a
             process version, part remapping).
"""
from __future__ import annotations

FOLLOWS = 'follows'
STAYS = 'stays'
COPIES = 'copies'
MODEL = 'model'
MANAGED = 'managed'

POLICIES = {FOLLOWS, STAYS, COPIES, MODEL, MANAGED}

# "<Model>.<field>" of the model that HOLDS the link -> policy. The target is whatever
# versioned model that field points at. (App label is always Tracker.)
LINKS = {
    # --- ApprovalTemplate (spec: who approves) ----------------------------------------
    'DocumentType.approval_template': FOLLOWS,
    'SamplingRuleSet.gate_approval_template': FOLLOWS,

    # --- BOM (composite; its override copies the lines) --------------------------------
    'BOMLine.bom': MODEL,

    # --- Companies (master data: everything follows) -----------------------------------
    'CAPA.supplier': FOLLOWS,
    'Core.customer': FOLLOWS,
    'ExternalContact.customer': FOLLOWS,
    'HubSpotCompanyLink.company': FOLLOWS,
    'Material.preferred_supplier': FOLLOWS,
    'MaterialLot.supplier': FOLLOWS,
    # Customer property's owner: a customer's new version is the same customer.
    'MaterialLot.owner': FOLLOWS,
    'NotificationRule.scope_customer': FOLLOWS,
    'NotificationSchedule.scope_customer': FOLLOWS,
    'Orders.company': FOLLOWS,
    'OutsideProcessShipment.supplier': FOLLOWS,
    'CustomerShipment.customer': FOLLOWS,
    'PartApproval.supplier': FOLLOWS,
    'PartTypes.preferred_supplier': FOLLOWS,
    'SamplingRuleSet.supplier': FOLLOWS,
    'SamplingSeverityState.supplier': FOLLOWS,
    'Steps.outside_supplier': FOLLOWS,
    'SupplierQualification.supplier': FOLLOWS,
    'User.parent_company': FOLLOWS,
    'UserRole.company': FOLLOWS,

    # --- DocumentType / Documents (document control owns revision) ---------------------
    'Documents.document_type': FOLLOWS,
    'DocChunk.doc': STAYS,             # embeddings of that revision's text
    'DocumentLink.document': MANAGED,  # a released revision is chosen by document control
    'GeneratedReport.document': STAYS,
    'QualityReports.file': STAYS,
    'SubstepResponse.value_document': STAYS,

    # --- EquipmentType (master data) ---------------------------------------------------
    'Equipments.equipment_type': FOLLOWS,
    'SubstepResource.equipment_type': FOLLOWS,
    'TrainingRequirement.equipment_type': FOLLOWS,

    # --- Equipments (master data: everything follows) ----------------------------------
    'CalibrationRecord.equipment': FOLLOWS,
    'ContinuousMachine.equipment': MODEL,          # services.mes.equipment
    'DowntimeEvent.equipment': FOLLOWS,
    'FPIRecord.equipment': FOLLOWS,
    'MeasurementDefinition.backup_equipment': FOLLOWS,
    'MeasurementDefinition.default_equipment': FOLLOWS,
    'QualityReportEquipment.equipment': FOLLOWS,
    'QualityReports.equipments': FOLLOWS,
    'ScheduledTask.machine': FOLLOWS,
    'StepEquipmentAffinity.equipment': MODEL,      # services.mes.equipment
    'StepExecutionEquipment.equipment': FOLLOWS,
    'StepExecutionMeasurement.equipment': FOLLOWS,
    'TimeEntry.equipment': FOLLOWS,
    'WorkCenter.equipment': MODEL,                 # services.mes.equipment (current WCs)
    'WorkCenterChangeover.equipment': MODEL,       # services.mes.equipment

    # --- LifeLimitDefinition (spec; override copies part-type links) -------------------
    'LifeTracking.definition': STAYS,
    'PartTypeLifeLimit.definition': MODEL,

    # --- MeasurementDefinition (spec) --------------------------------------------------
    'MeasurementResult.definition': STAYS,
    'QualityReports.variables_characteristic': STAYS,
    'SPCBaseline.measurement_definition': STAYS,   # a new tolerance needs a new baseline
    'SamplingRuleSet.variables_characteristic': FOLLOWS,
    'StepEdge.condition_measurement': MANAGED,
    'StepExecutionMeasurement.measurement_definition': STAYS,
    'StepMeasurementRequirement.measurement': MANAGED,
    'Steps.required_measurements': MANAGED,

    # --- MilestoneTemplate (composite) -------------------------------------------------
    'Milestone.template': MODEL,

    # --- PartTypes (master data: the item master — everything follows) ----------------
    'BOM.part_type': FOLLOWS,
    'BOMLine.component_type': FOLLOWS,
    'Core.core_type': FOLLOWS,
    'DisassemblyBOMLine.component_type': FOLLOWS,
    'DisassemblyBOMLine.core_type': FOLLOWS,
    'FPIRecord.part_type': FOLLOWS,
    'HarvestedComponent.component_type': FOLLOWS,
    'MaterialLot.material_type': FOLLOWS,
    'MaterialStagingLine.material_type': FOLLOWS,
    'OrderLine.part_type': FOLLOWS,
    'PartApproval.part_type': FOLLOWS,
    'PartTypeLifeLimit.part_type': FOLLOWS,
    'Parts.part_type': FOLLOWS,
    'Processes.part_type': FOLLOWS,
    'QualityErrorsList.part_type': FOLLOWS,
    'RebuildScopePreset.core_type': FOLLOWS,
    'RepairCode.component_type': FOLLOWS,
    'SamplingRuleSet.part_type': FOLLOWS,
    'Steps.part_type': FOLLOWS,
    'SupplierQualification.part_type': FOLLOWS,
    'ThreeDModel.part_type': FOLLOWS,

    # --- Processes (change control) ----------------------------------------------------
    'PartTypes.default_disassembly_process': MANAGED,
    'ProcessChangeOrder.draft_process_version': MANAGED,
    'ProcessChangeRequest.draft_process_version': MANAGED,
    'ProcessChangeRequest.target_process': MANAGED,
    'ProcessStep.process': MODEL,
    'SamplingRuleSet.process': MANAGED,
    'StepEdge.process': MODEL,
    'TrainingRequirement.process': MANAGED,
    'WorkOrder.process': MANAGED,

    # --- QualityErrorsList (spec: the defect catalog) ----------------------------------
    'QualityReportDefect.error_type': STAYS,
    'QualityReports.errors': STAYS,

    # --- RepairCode (spec) ---------------------------------------------------------------
    'RebuildScopePreset.codes': FOLLOWS,

    # --- SPCBaseline (own supersede mechanism) -------------------------------------------
    'SPCBaseline.superseded_by': MODEL,

    # --- SamplingRuleSet (own supersede mechanism; records stay) -----------------------
    'Parts.sampling_ruleset': STAYS,
    'SamplingAnalytics.ruleset': STAYS,
    'SamplingRule.ruleset': MODEL,
    'SamplingRuleSet.fallback_ruleset': MODEL,
    'SamplingRuleSet.supersedes': MODEL,
    'SamplingTriggerState.ruleset': STAYS,
    'StepGateFiring.ruleset': STAYS,

    # --- Shift (master data) -------------------------------------------------------------
    'Equipments.operating_shifts': FOLLOWS,
    'OvertimeWindow.shift': MODEL,     # services.mes.shifts
    'ScheduleSlot.shift': FOLLOWS,
    'User.default_shift': MODEL,       # services.mes.shifts

    # --- Steps (change control: a step version belongs to a draft process revision) ----
    'AssemblyUsage.step': STAYS,
    'BOMLine.consumed_at_step': MANAGED,
    'BatchExecution.step': STAYS,
    'CAPA.step': STAYS,
    'FPIRecord.step': STAYS,
    'Fixture.steps': COPIES,
    'MaterialStaging.step': STAYS,
    'MaterialUsage.step': STAYS,
    'MeasurementDefinition.step': MANAGED,
    'OutsideProcessShipment.step': STAYS,
    'Parts.step': MANAGED,             # parts move by the advancement engine / part remap
    'ProcessStep.step': MANAGED,
    'QaApproval.step': STAYS,
    'QualityReports.step': STAYS,
    'QuarantineDisposition.step': STAYS,
    'RepairCode.steps': COPIES,
    'SamplingRuleSet.step': MANAGED,
    'SamplingSeverityState.step': STAYS,
    'SamplingTriggerState.step': STAYS,
    'ScheduledTask.step': STAYS,
    'StepEdge.from_step': MANAGED,
    'StepEdge.to_step': MANAGED,
    'StepEquipmentAffinity.step': COPIES,
    'StepExecution.next_step': STAYS,
    'StepExecution.step': STAYS,
    'StepGateFiring.step': STAYS,
    'StepMeasurementRequirement.step': MODEL,
    'StepRequirement.step': MODEL,
    'StepTiming.step': MODEL,
    'StepTransitionLog.step': STAYS,
    'Substep.step': MODEL,
    'ThreeDModel.step': MANAGED,
    'TimeEntry.step': STAYS,
    'TrainingRequirement.step': MODEL,
    'WorkCenterChangeover.from_step': COPIES,
    'WorkCenterChangeover.to_step': COPIES,

    # --- ThreeDModel (spec) ----------------------------------------------------------------
    'HeatMapAnnotations.model': STAYS,

    # --- TrainingType (spec: records stay; qualification compares across the chain) -------
    'TrainingRecord.training_type': STAYS,
    'TrainingRequirement.training_type': MODEL,  # services.training

    # --- WorkCenter (master data; services.mes.work_centers moves every live link) -------
    'DowntimeEvent.work_center': MODEL,
    'ScheduleSlot.work_center': MODEL,
    'Steps.work_center': MODEL,
    'TimeEntry.work_center': MODEL,
    'UserWorkCenterMembership.work_center': MODEL,
}


_BY_TARGET = None


def _resolved():
    """{target model: [(owner, field, policy)]}, built once. Owners are found by class
    name across every app — a link's owner isn't always in Tracker (HubSpotCompanyLink
    lives in the integrations app)."""
    global _BY_TARGET
    if _BY_TARGET is None:
        from django.apps import apps
        by_name = {m.__name__: m for m in apps.get_models()}
        table: dict = {}
        for key, policy in LINKS.items():
            owner_name, field_name = key.split('.')
            owner = by_name[owner_name]
            field = owner._meta.get_field(field_name)
            table.setdefault(field.related_model, []).append((owner, field, policy))
        _BY_TARGET = table
    return _BY_TARGET


def links_to(model):
    """The (owner model, field, policy) links whose target is `model`."""
    return _resolved().get(model, [])


def apply_version_links(old, new, *, supersede_source: bool = True) -> None:
    """Carry out FOLLOWS and COPIES for every link to `type(old)`.

    FOLLOWS only when the new version replaces the old (`supersede_source`): a draft
    fork that doesn't yet supersede its source must not pull live links onto itself.
    COPIES always — the draft needs its own copy either way.

    Also carries the versioned row's OWN many-to-many sets forward when the new row has
    none: `create_new_version` copies columns only.
    """
    for field in type(old)._meta.many_to_many:
        # Plain sets only: one with its own through model (a step's required
        # measurements) is a composite child the model's override copies.
        if not field.remote_field.through._meta.auto_created:
            continue
        new_rel, old_rel = getattr(new, field.name), getattr(old, field.name)
        if not new_rel.exists():
            new_rel.set(old_rel.all())

    for owner, field, policy in links_to(type(old)):
        if policy == FOLLOWS and supersede_source:
            _follow(owner, field, old, new)
        elif policy == COPIES:
            _copy(owner, field, old, new)


def _follow(owner, field, old, new) -> None:
    if field.many_to_many:
        through = field.remote_field.through
        col = field.m2m_reverse_field_name()           # the column holding the target
        src = field.m2m_field_name()                    # the column holding the owner
        already = set(through._base_manager.filter(**{col: new.pk})  # tenant-safe: rows keyed to one in-tenant target
                      .values_list(src, flat=True))
        rows = through._base_manager.filter(**{col: old.pk})  # tenant-safe: rows keyed to one in-tenant target
        rows.exclude(**{f"{src}__in": already}).update(**{col: new.pk})
        rows.delete()  # any left were duplicates of a link to the new version
        return
    owner._base_manager.filter(**{field.name: old}).update(**{field.name: new})  # tenant-safe: rows keyed to one in-tenant target


def _copy(owner, field, old, new) -> None:
    if field.many_to_many:
        through = field.remote_field.through
        col, src = field.m2m_reverse_field_name(), field.m2m_field_name()
        owners = set(through._base_manager.filter(**{col: old.pk})  # tenant-safe: rows keyed to one in-tenant target
                     .values_list(src, flat=True))
        through._base_manager.bulk_create(
            [through(**{f"{src}_id": o, f"{col}_id": new.pk}) for o in owners],
            ignore_conflicts=True)
        return
    rows = owner._base_manager.filter(**{field.name: old})  # tenant-safe: rows keyed to one in-tenant target
    if any(f.name == 'archived' for f in owner._meta.concrete_fields):
        rows = rows.filter(archived=False)
    for row in list(rows):
        row.pk = None
        row.id = None
        row._state.adding = True
        setattr(row, field.name, new)
        row.save()
