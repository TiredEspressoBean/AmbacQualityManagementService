"""Locations become records.

The free-text location on lots, units, machines and cycle counts becomes a foreign key
to StorageLocation. Every distinct name already in use (per tenant, ignoring case and
surrounding spaces) becomes, or matches, one StorageLocation, so no lot loses where it is.
Order: keep the text under a temporary name → add the FK (0218) → backfill (0219) →
drop the text (0220). Three migrations because Postgres refuses DDL on a table with
pending FK trigger events from rows written earlier in the same transaction.
"""
import django.db.models.deletion
from django.db import migrations, models

# (model, old text column, temporary name)
_LINKED = [
    ("materiallot", "storage_location", "location_text"),
    ("parts", "storage_location", "location_text"),
    ("equipments", "location", "location_text"),
    ("cyclecount", "location", "location_text"),
]


def _fk(related_name, null=True):
    return models.ForeignKey(
        blank=null, null=null, on_delete=django.db.models.deletion.PROTECT,
        related_name=related_name, to="Tracker.storagelocation")


class Migration(migrations.Migration):

    dependencies = [
        ("Tracker", "0217_cycle_count"),
    ]

    operations = [
        # 1. StorageLocation grows its controls and hierarchy.
        migrations.AddField(
            model_name="storagelocation", name="parent",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="children", to="Tracker.storagelocation",
                help_text="The location this one is inside (a bin's rack, a rack's area)."),
        ),
        migrations.AddField(
            model_name="storagelocation", name="kind",
            field=models.CharField(choices=[
                ("WAREHOUSE", "Warehouse"), ("AREA", "Area"), ("RACK", "Rack"), ("SHELF", "Shelf"),
                ("BIN", "Bin"), ("CAGE", "Cage"), ("YARD", "Yard"), ("DOCK", "Dock"),
                ("CELL", "Work cell"), ("LINE_SIDE", "Line-side"), ("OTHER", "Other"),
            ], default="OTHER", max_length=20),
        ),
        migrations.AddField(
            model_name="storagelocation", name="code",
            field=models.CharField(blank=True, max_length=40,
                                   help_text="Short code for the label barcode. Optional; the name is used without one."),
        ),
        migrations.AddField(
            model_name="storagelocation", name="held_only",
            field=models.BooleanField(default=False,
                                      help_text="Only held or rejected stock may be put here (an MRB or quarantine cage)."),
        ),
        migrations.AddField(
            model_name="storagelocation", name="receiving_dock",
            field=models.BooleanField(default=False, help_text="Where receiving puts deliveries by default."),
        ),
        migrations.AddConstraint(
            model_name="storagelocation",
            constraint=models.UniqueConstraint(
                condition=~models.Q(code=""), fields=("tenant", "code"),
                name="storage_location_code_unique_per_tenant"),
        ),

        # 2. Keep the text under a temporary name.
        *[migrations.RenameField(model_name=m, old_name=old, new_name=tmp) for m, old, tmp in _LINKED],

        # 3. Add the links (cycle counts nullable until backfilled).
        migrations.AddField(model_name="materiallot", name="location", field=_fk("lots")),
        migrations.AddField(model_name="parts", name="location", field=_fk("parts")),
        migrations.AddField(model_name="equipments", name="location", field=_fk("equipment")),
        migrations.AddField(model_name="cyclecount", name="location", field=_fk("cycle_counts")),

    ]
