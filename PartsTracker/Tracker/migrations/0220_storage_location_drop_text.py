"""Locations become records, part 3: drop the old text columns (backfilled in 0219).

Separate from 0219 because Postgres won't ALTER a table with pending FK trigger events
from the backfill in the same transaction."""
import django.db.models.deletion
from django.db import migrations, models

_TMP = ["materiallot", "parts", "equipments", "cyclecount"]


class Migration(migrations.Migration):

    dependencies = [
        ("Tracker", "0219_storage_location_backfill"),
    ]

    operations = [
        *[migrations.RemoveField(model_name=m, name="location_text") for m in _TMP],
        migrations.AlterField(
            model_name="cyclecount", name="location",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    related_name="cycle_counts", to="Tracker.storagelocation"),
        ),
    ]
