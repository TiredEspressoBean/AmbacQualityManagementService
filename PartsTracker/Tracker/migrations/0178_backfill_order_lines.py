"""Give existing orders the demand line they always implied.

`OrderLine` records what a customer asked for. Before it existed, that was recorded
nowhere — quantity and part type lived only on the work orders somebody created in
response. Leaving history line-less would mean two permanent tiers: every order created
before this migration could never be planned, quoted, or counted as demand, and the
order page would show an empty panel forever on exactly the orders with the most
history behind them.

The derivation is a RESTATEMENT, not an inference, and only because the data supports
it: one line per (order, part type), quantity summed from the non-cancelled work orders
already pegged to that order. Cancelled work orders are excluded to match
`OrderLine.planned_quantity`, so a backfilled line lands at remaining = 0 rather than
looking like it needs planning.

Every row it creates is marked in `notes` so a derived line stays distinguishable from
one a person typed — which is the honesty this owes, given a line is a record of a
customer commitment. The reverse deletes exactly those rows and nothing else.
"""
from django.db import migrations


DERIVED_NOTE = "Derived from existing work orders when order lines were introduced."


def _backfill(apps, schema_editor):
    Orders = apps.get_model('Tracker', 'Orders')
    OrderLine = apps.get_model('Tracker', 'OrderLine')
    WorkOrder = apps.get_model('Tracker', 'WorkOrder')

    # `_base_manager` because historical models have no SecureManager, and because a
    # migration is deliberately cross-tenant.
    for order in Orders._base_manager.all().iterator():
        # An order somebody has already given lines is not history to reconstruct —
        # whatever is there was entered deliberately and outranks anything derived.
        if OrderLine._base_manager.filter(order=order).exists():
            continue

        wos = list(
            WorkOrder._base_manager.filter(related_order=order)
            .exclude(workorder_status='CANCELLED')
            .select_related('process')
        )
        if not wos:
            continue

        # Group by the part type the job actually builds, resolved the same way the
        # rest of the system resolves it: work order -> process -> part type.
        by_part_type: dict = {}
        for wo in wos:
            pt_id = getattr(wo.process, 'part_type_id', None) if wo.process_id else None
            if pt_id is None:
                continue          # nothing to state a demand for
            by_part_type.setdefault(pt_id, []).append(wo)

        for i, (pt_id, group) in enumerate(sorted(by_part_type.items(), key=lambda kv: str(kv[0])), start=1):
            line = OrderLine._base_manager.create(
                tenant_id=order.tenant_id,
                order=order,
                line_number=i,
                part_type_id=pt_id,
                quantity=sum(w.quantity or 0 for w in group) or 1,
                # The order's own estimate. A line-level date didn't exist to recover,
                # and the header date is what anybody would have been working to.
                due_date=order.estimated_completion,
                status='OPEN',
                notes=DERIVED_NOTE,
            )
            # Peg the jobs, so the line reads as satisfied by the work that already
            # exists rather than as fresh demand nobody has started.
            WorkOrder._base_manager.filter(
                pk__in=[w.pk for w in group]).update(order_line=line)


def _unbackfill(apps, schema_editor):
    """Remove exactly the rows this migration created — identified by the marker it
    wrote — and unpeg the work orders it touched. A line a person entered afterwards
    carries no marker and is left alone."""
    OrderLine = apps.get_model('Tracker', 'OrderLine')
    WorkOrder = apps.get_model('Tracker', 'WorkOrder')

    derived = OrderLine._base_manager.filter(notes=DERIVED_NOTE)
    WorkOrder._base_manager.filter(order_line__in=derived).update(order_line=None)
    derived.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0177_orderline'),
    ]

    operations = [
        migrations.RunPython(_backfill, _unbackfill),
    ]
