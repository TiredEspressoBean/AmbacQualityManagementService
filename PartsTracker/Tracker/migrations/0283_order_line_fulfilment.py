# An order line says how the customer is served (2026-11-03): new build, or
# remanufacture of their unit. Every line starts as New build; a line whose order already
# has the customer's cores of that part type takes those cores' mode (the commonest
# mode among them, when they disagree).

from collections import Counter

from django.db import migrations, models


def from_received_cores(apps, schema_editor):
    Core = apps.get_model('Tracker', 'Core')
    OrderLine = apps.get_model('Tracker', 'OrderLine')
    modes: dict = {}
    for r in (Core._default_manager
              .filter(part__order__isnull=False, fulfilment_mode__isnull=False)
              .values('part__order_id', 'part__part_type_id', 'fulfilment_mode')):
        modes.setdefault((r['part__order_id'], r['part__part_type_id']), Counter())[r['fulfilment_mode']] += 1
    for (order_id, part_type_id), counts in modes.items():
        (OrderLine._default_manager
         .filter(order_id=order_id, part_type_id=part_type_id)
         .update(fulfilment=counts.most_common(1)[0][0]))


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0282_demand_time_fence_in_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderline',
            name='fulfilment',
            field=models.CharField(choices=[('NEW_BUILD', 'New build'), ('EXCHANGE', 'Exchange — customer gets a unit from stock'), ('REPAIR_RETURN', 'Repair & return — this unit goes back to them')], default='NEW_BUILD', help_text="New build, or remanufacture of the customer's unit (repair & return / exchange). Reman lines don't use up the new-build forecast.", max_length=20),
        ),
        migrations.RunPython(from_received_cores, migrations.RunPython.noop),
    ]
