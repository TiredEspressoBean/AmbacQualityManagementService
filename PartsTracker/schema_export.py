# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class TrackerArchivereason(models.Model):
    id = models.BigAutoField(primary_key=True)
    reason = models.CharField(max_length=50)
    notes = models.TextField()
    object_id = models.IntegerField()
    archived_at = models.DateTimeField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    user = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_archivereason'
        unique_together = (('content_type', 'object_id'),)


class TrackerCompanies(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    hubspot_api_id = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_companies'


class TrackerDocuments(models.Model):
    id = models.BigAutoField(primary_key=True)
    ai_readable = models.BooleanField()
    is_image = models.BooleanField()
    file_name = models.CharField(max_length=50)
    file = models.CharField(max_length=100)
    upload_date = models.DateField()
    object_id = models.BigIntegerField(blank=True, null=True)
    version = models.IntegerField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    uploaded_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    classification = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Tracker_documents'


class TrackerEquipments(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    equipment_type = models.ForeignKey('TrackerEquipmenttype', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_equipments'


class TrackerEquipmenttype(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_equipmenttype'


class TrackerEquipmentusage(models.Model):
    id = models.BigAutoField(primary_key=True)
    used_at = models.DateTimeField()
    notes = models.TextField()
    equipment = models.ForeignKey(TrackerEquipments, models.DO_NOTHING, blank=True, null=True)
    part = models.ForeignKey('TrackerParts', models.DO_NOTHING, blank=True, null=True)
    error_report = models.ForeignKey('TrackerQualityreports', models.DO_NOTHING, blank=True, null=True)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING, blank=True, null=True)
    operator = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_equipmentusage'


class TrackerExternalapiorderidentifier(models.Model):
    id = models.BigAutoField(primary_key=True)
    stage_name = models.CharField(unique=True, max_length=100)
    api_id = models.CharField(db_column='API_id', max_length=50)  # Field name made lowercase.
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_externalapiorderidentifier'


class TrackerMeasurementdefinition(models.Model):
    id = models.BigAutoField(primary_key=True)
    label = models.CharField(max_length=100)
    type = models.CharField(max_length=20)
    unit = models.CharField(max_length=50)
    nominal = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    upper_tol = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lower_tol = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    required = models.BooleanField()
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_measurementdefinition'


class TrackerMeasurementdisposition(models.Model):
    id = models.BigAutoField(primary_key=True)
    disposition_type = models.CharField()
    notes = models.TextField()
    resolved_at = models.DateTimeField()
    resolved_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    measurement = models.OneToOneField('TrackerMeasurementresult', models.DO_NOTHING)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_measurementdisposition'


class TrackerMeasurementresult(models.Model):
    id = models.BigAutoField(primary_key=True)
    value_numeric = models.FloatField(blank=True, null=True)
    value_pass_fail = models.CharField(max_length=4, blank=True, null=True)
    is_within_spec = models.BooleanField()
    created_at = models.DateTimeField()
    created_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    definition = models.ForeignKey(TrackerMeasurementdefinition, models.DO_NOTHING)
    report = models.ForeignKey('TrackerQualityreports', models.DO_NOTHING)
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_measurementresult'


class TrackerOrders(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    name = models.CharField(max_length=50)
    customer_note = models.TextField(blank=True, null=True)
    estimated_completion = models.DateField(blank=True, null=True)
    order_status = models.CharField(max_length=50)
    archived = models.BooleanField()
    hubspot_deal_id = models.CharField(unique=True, max_length=60, blank=True, null=True)
    last_synced_hubspot_stage = models.CharField(max_length=100, blank=True, null=True)
    company = models.ForeignKey(TrackerCompanies, models.DO_NOTHING, blank=True, null=True)
    current_hubspot_gate = models.ForeignKey(TrackerExternalapiorderidentifier, models.DO_NOTHING, blank=True, null=True)
    customer = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    original_completion_date = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_orders'


class TrackerParts(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    erp_id = models.CharField(db_column='ERP_id', max_length=50)  # Field name made lowercase.
    part_status = models.CharField(max_length=50)
    archived = models.BooleanField()
    order = models.ForeignKey(TrackerOrders, models.DO_NOTHING, blank=True, null=True)
    part_type = models.ForeignKey('TrackerParttypes', models.DO_NOTHING, blank=True, null=True)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING, blank=True, null=True)
    work_order = models.ForeignKey('TrackerWorkorder', models.DO_NOTHING, blank=True, null=True)
    requires_sampling = models.BooleanField()
    sampling_rule = models.ForeignKey('TrackerSamplingrule', models.DO_NOTHING, blank=True, null=True)
    sampling_ruleset = models.ForeignKey('TrackerSamplingruleset', models.DO_NOTHING, blank=True, null=True)
    sampling_context = models.JSONField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_parts'


class TrackerParttypes(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    name = models.CharField(max_length=50)
    id_prefix = models.CharField(db_column='ID_prefix', max_length=50, blank=True, null=True)  # Field name made lowercase.
    version = models.IntegerField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    erp_id = models.CharField(db_column='ERP_id', max_length=50, blank=True, null=True)  # Field name made lowercase.
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    is_current_version = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'Tracker_parttypes'


class TrackerProcesses(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    name = models.CharField(max_length=50)
    is_remanufactured = models.BooleanField()
    num_steps = models.IntegerField()
    version = models.IntegerField()
    part_type = models.ForeignKey(TrackerParttypes, models.DO_NOTHING)
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    is_current_version = models.BooleanField()
    is_batch_process = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'Tracker_processes'


class TrackerQaapproval(models.Model):
    id = models.BigAutoField(primary_key=True)
    qa_staff = models.ForeignKey('TrackerUser', models.DO_NOTHING)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING)
    work_order = models.ForeignKey('TrackerWorkorder', models.DO_NOTHING)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_qaapproval'


class TrackerQualityerrorslist(models.Model):
    id = models.BigAutoField(primary_key=True)
    error_name = models.CharField(max_length=50)
    error_example = models.TextField()
    part_type = models.ForeignKey(TrackerParttypes, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_qualityerrorslist'


class TrackerQualityreports(models.Model):
    id = models.BigAutoField(primary_key=True)
    sampling_method = models.CharField(max_length=50)
    status = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    file = models.ForeignKey(TrackerDocuments, models.DO_NOTHING, blank=True, null=True)
    machine = models.ForeignKey(TrackerEquipments, models.DO_NOTHING, blank=True, null=True)
    part = models.ForeignKey(TrackerParts, models.DO_NOTHING, blank=True, null=True)
    sampling_rule = models.ForeignKey('TrackerSamplingrule', models.DO_NOTHING, blank=True, null=True)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING, blank=True, null=True)
    sampling_audit_log = models.ForeignKey('TrackerSamplingauditlog', models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_qualityreports'


class TrackerQualityreportsErrors(models.Model):
    id = models.BigAutoField(primary_key=True)
    qualityreports = models.ForeignKey(TrackerQualityreports, models.DO_NOTHING)
    qualityerrorslist = models.ForeignKey(TrackerQualityerrorslist, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_qualityreports_errors'
        unique_together = (('qualityreports', 'qualityerrorslist'),)


class TrackerQualityreportsOperator(models.Model):
    id = models.BigAutoField(primary_key=True)
    qualityreports = models.ForeignKey(TrackerQualityreports, models.DO_NOTHING)
    user = models.ForeignKey('TrackerUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_qualityreports_operator'
        unique_together = (('qualityreports', 'user'),)


class TrackerSamplinganalytics(models.Model):
    id = models.BigAutoField(primary_key=True)
    parts_sampled = models.IntegerField()
    parts_total = models.IntegerField()
    defects_found = models.IntegerField()
    actual_sampling_rate = models.FloatField()
    target_sampling_rate = models.FloatField()
    variance = models.FloatField()
    created_at = models.DateTimeField()
    ruleset = models.ForeignKey('TrackerSamplingruleset', models.DO_NOTHING)
    work_order = models.ForeignKey('TrackerWorkorder', models.DO_NOTHING)
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_samplinganalytics'
        unique_together = (('ruleset', 'work_order'),)


class TrackerSamplingauditlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    sampling_decision = models.BooleanField()
    timestamp = models.DateTimeField()
    ruleset_type = models.CharField(max_length=20)
    part = models.ForeignKey(TrackerParts, models.DO_NOTHING)
    rule = models.ForeignKey('TrackerSamplingrule', models.DO_NOTHING)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_samplingauditlog'


class TrackerSamplingrule(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.IntegerField()
    created_at = models.DateTimeField()
    ruleset = models.ForeignKey('TrackerSamplingruleset', models.DO_NOTHING)
    rule_type = models.CharField(max_length=32)
    created_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    modified_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, related_name='trackersamplingrule_modified_by_set', blank=True, null=True)
    value = models.IntegerField(blank=True, null=True)
    algorithm_description = models.TextField()
    last_validated = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_samplingrule'


class TrackerSamplingruleset(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    active = models.BooleanField()
    version = models.IntegerField()
    created_at = models.DateTimeField()
    part_type = models.ForeignKey(TrackerParttypes, models.DO_NOTHING)
    process = models.ForeignKey(TrackerProcesses, models.DO_NOTHING)
    supersedes = models.OneToOneField('self', models.DO_NOTHING, blank=True, null=True)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING)
    created_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    modified_by = models.ForeignKey('TrackerUser', models.DO_NOTHING, related_name='trackersamplingruleset_modified_by_set', blank=True, null=True)
    fallback_duration = models.IntegerField(blank=True, null=True)
    fallback_ruleset = models.OneToOneField('self', models.DO_NOTHING, related_name='trackersamplingruleset_fallback_ruleset_set', blank=True, null=True)
    fallback_threshold = models.IntegerField(blank=True, null=True)
    is_fallback = models.BooleanField()
    archived = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, related_name='trackersamplingruleset_previous_version_set', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Tracker_samplingruleset'
        unique_together = (('part_type', 'process', 'step', 'is_fallback'),)


class TrackerSamplingtriggerstate(models.Model):
    id = models.BigAutoField(primary_key=True)
    active = models.BooleanField()
    triggered_at = models.DateTimeField()
    success_count = models.IntegerField()
    fail_count = models.IntegerField()
    ruleset = models.ForeignKey(TrackerSamplingruleset, models.DO_NOTHING)
    step = models.ForeignKey('TrackerSteps', models.DO_NOTHING)
    triggered_by = models.ForeignKey(TrackerQualityreports, models.DO_NOTHING, blank=True, null=True)
    work_order = models.ForeignKey('TrackerWorkorder', models.DO_NOTHING)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()
    notification_sent = models.BooleanField()
    notification_sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Tracker_samplingtriggerstate'
        unique_together = (('ruleset', 'work_order', 'step'),)


class TrackerSamplingtriggerstateNotifiedUsers(models.Model):
    id = models.BigAutoField(primary_key=True)
    samplingtriggerstate = models.ForeignKey(TrackerSamplingtriggerstate, models.DO_NOTHING)
    user = models.ForeignKey('TrackerUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_samplingtriggerstate_notified_users'
        unique_together = (('samplingtriggerstate', 'user'),)


class TrackerSamplingtriggerstatePartsInspected(models.Model):
    id = models.BigAutoField(primary_key=True)
    samplingtriggerstate = models.ForeignKey(TrackerSamplingtriggerstate, models.DO_NOTHING)
    parts = models.ForeignKey(TrackerParts, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_samplingtriggerstate_parts_inspected'
        unique_together = (('samplingtriggerstate', 'parts'),)


class TrackerSteps(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField()
    expected_duration = models.DurationField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_last_step = models.BooleanField()
    part_type = models.ForeignKey(TrackerParttypes, models.DO_NOTHING)
    process = models.ForeignKey(TrackerProcesses, models.DO_NOTHING)
    block_on_quarantine = models.BooleanField()
    pass_threshold = models.FloatField()
    requires_qa_signoff = models.BooleanField()
    min_sampling_rate = models.FloatField()
    sampling_required = models.BooleanField()
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_steps'
        unique_together = (('process', 'order'),)


class TrackerStepsNotificationUsers(models.Model):
    id = models.BigAutoField(primary_key=True)
    steps = models.ForeignKey(TrackerSteps, models.DO_NOTHING)
    user = models.ForeignKey('TrackerUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_steps_notification_users'
        unique_together = (('steps', 'user'),)


class TrackerStepsRequiredMeasurements(models.Model):
    id = models.BigAutoField(primary_key=True)
    steps = models.ForeignKey(TrackerSteps, models.DO_NOTHING)
    measurementdefinition = models.ForeignKey(TrackerMeasurementdefinition, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_steps_required_measurements'
        unique_together = (('steps', 'measurementdefinition'),)


class TrackerSteptransitionlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField()
    part = models.ForeignKey(TrackerParts, models.DO_NOTHING, blank=True, null=True)
    step = models.ForeignKey(TrackerSteps, models.DO_NOTHING, blank=True, null=True)
    operator = models.ForeignKey('TrackerUser', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    updated_at = models.DateTimeField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_steptransitionlog'


class TrackerUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    parent_company = models.ForeignKey(TrackerCompanies, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Tracker_user'


class TrackerUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(TrackerUser, models.DO_NOTHING)
    group = models.ForeignKey('AuthGroup', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_user_groups'
        unique_together = (('user', 'group'),)


class TrackerUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(TrackerUser, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Tracker_user_user_permissions'
        unique_together = (('user', 'permission'),)


class TrackerWorkorder(models.Model):
    id = models.BigAutoField(primary_key=True)
    workorder_status = models.CharField(max_length=50)
    erp_id = models.CharField(db_column='ERP_id', max_length=50)  # Field name made lowercase.
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    expected_completion = models.DateField(blank=True, null=True)
    expected_duration = models.DurationField(blank=True, null=True)
    true_completion = models.DateField(blank=True, null=True)
    true_duration = models.DurationField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    related_order = models.ForeignKey(TrackerOrders, models.DO_NOTHING, blank=True, null=True)
    quantity = models.IntegerField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField()
    is_current_version = models.BooleanField()
    previous_version = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    version = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tracker_workorder'


class AccountEmailaddress(models.Model):
    email = models.CharField(unique=True, max_length=254)
    verified = models.BooleanField()
    primary = models.BooleanField()
    user = models.ForeignKey(TrackerUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'account_emailaddress'
        unique_together = (('user', 'email'), ('user', 'primary'),)


class AccountEmailconfirmation(models.Model):
    created = models.DateTimeField()
    sent = models.DateTimeField(blank=True, null=True)
    key = models.CharField(unique=True, max_length=64)
    email_address = models.ForeignKey(AccountEmailaddress, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'account_emailconfirmation'


class AuditlogLogentry(models.Model):
    object_pk = models.CharField(max_length=255)
    object_id = models.BigIntegerField(blank=True, null=True)
    object_repr = models.TextField()
    action = models.SmallIntegerField()
    changes = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField()
    actor = models.ForeignKey(TrackerUser, models.DO_NOTHING, blank=True, null=True)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    additional_data = models.JSONField(blank=True, null=True)
    serialized_data = models.JSONField(blank=True, null=True)
    cid = models.CharField(max_length=255, blank=True, null=True)
    changes_text = models.TextField()
    remote_port = models.IntegerField(blank=True, null=True)
    actor_email = models.CharField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'auditlog_logentry'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthtokenToken(models.Model):
    key = models.CharField(primary_key=True, max_length=40)
    created = models.DateTimeField()
    user = models.OneToOneField(TrackerUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'authtoken_token'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(TrackerUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class SocialaccountSocialaccount(models.Model):
    provider = models.CharField(max_length=200)
    uid = models.CharField(max_length=191)
    last_login = models.DateTimeField()
    date_joined = models.DateTimeField()
    extra_data = models.JSONField()
    user = models.ForeignKey(TrackerUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'socialaccount_socialaccount'
        unique_together = (('provider', 'uid'),)


class SocialaccountSocialapp(models.Model):
    provider = models.CharField(max_length=30)
    name = models.CharField(max_length=40)
    client_id = models.CharField(max_length=191)
    secret = models.CharField(max_length=191)
    key = models.CharField(max_length=191)
    provider_id = models.CharField(max_length=200)
    settings = models.JSONField()

    class Meta:
        managed = False
        db_table = 'socialaccount_socialapp'


class SocialaccountSocialtoken(models.Model):
    token = models.TextField()
    token_secret = models.TextField()
    expires_at = models.DateTimeField(blank=True, null=True)
    account = models.ForeignKey(SocialaccountSocialaccount, models.DO_NOTHING)
    app = models.ForeignKey(SocialaccountSocialapp, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'socialaccount_socialtoken'
        unique_together = (('app', 'account'),)
