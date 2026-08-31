"""Work-queue row DTO — one row per (WorkOrder, Step) with open executions.

Ranked, aggregate view built for the operator home's UP NEXT / THEN tiles and
the shop's queue page. Not tied to a model — the row is computed by
WorkQueueViewSet from the StepExecution grain.
"""
from rest_framework import serializers


class WorkQueueRowSerializer(serializers.Serializer):
    """One ready-or-blocked row on the floor. All fields are read-only projections."""

    work_order = serializers.UUIDField()
    work_order_erp_id = serializers.CharField(allow_null=True)
    step = serializers.UUIDField()
    step_name = serializers.CharField(allow_null=True)
    part_type_name = serializers.CharField(allow_null=True)

    # WorkOrder.priority is IntegerChoices (1=Urgent, 2=High, 3=Normal, 4=Low —
    # lower number = higher priority; the number IS the sort rank).
    priority = serializers.IntegerField(allow_null=True)
    expected_completion = serializers.DateField(allow_null=True)

    qty_ready = serializers.IntegerField()
    earliest_entered_at = serializers.DateTimeField(allow_null=True)

    # Earliest planned start for this (WO, step) on the live APS schedule; null
    # when the solver hasn't placed it. Drives the queue's order (scheduled rows
    # lead in planned order) and the "planned HH:MM" hint on the operator home.
    scheduled_start = serializers.DateTimeField(allow_null=True)

    # Which surface this row belongs on. See Documents/WORK_CENTER_DESIGN.md.
    work_center = serializers.UUIDField(allow_null=True)
    work_center_kind = serializers.CharField(allow_null=True)

    # The machine the live schedule assigned this cohort to — lets the floor see (and the
    # queue scope to) the specific station, not just the work center. Null when the step
    # needs no machine or the solver hasn't placed it.
    machine = serializers.UUIDField(allow_null=True)
    machine_name = serializers.CharField(allow_null=True)

    # v1 readiness bucket: 'blocked' when the WO has an active hold, else 'ready'.
    # Upstream-done is implicit (open executions exist here); certified/cal/
    # downtime/blocker predicates are separate concerns that layer on later.
    readiness = serializers.CharField()
    is_held = serializers.BooleanField()
