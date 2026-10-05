"""Locations become records, part 2: every location name in use becomes (or matches)
a StorageLocation — per tenant, ignoring case and surrounding spaces."""
from django.db import migrations

_LINKED = [
    ("materiallot", "location_text"),
    ("parts", "location_text"),
    ("equipments", "location_text"),
    ("cyclecount", "location_text"),
]


def backfill(apps, schema_editor):
    StorageLocation = apps.get_model("Tracker", "StorageLocation")
    # tenant-safe: data migration runs outside any request; every lookup is keyed by tenant_id.
    by_key = {}
    for loc in StorageLocation._base_manager.all():
        by_key.setdefault((loc.tenant_id, loc.name.strip().lower()), loc.pk)

    for model_name, tmp in _LINKED:
        Model = apps.get_model("Tracker", model_name)
        rows = (Model._base_manager.exclude(**{tmp: ""}).exclude(**{f"{tmp}__isnull": True})
                .values_list("pk", "tenant_id", tmp))
        for pk, tenant_id, text in rows.iterator():
            name = (text or "").strip()
            if not name:
                continue
            key = (tenant_id, name.lower())
            loc_id = by_key.get(key)
            if loc_id is None:
                loc_id = StorageLocation._base_manager.create(tenant_id=tenant_id, name=name[:100]).pk
                by_key[key] = loc_id
            Model._base_manager.filter(pk=pk).update(location_id=loc_id)


def unbackfill(apps, schema_editor):
    StorageLocation = apps.get_model("Tracker", "StorageLocation")
    # tenant-safe: reverse data migration; names copied row by row.
    names = dict(StorageLocation._base_manager.values_list("pk", "name"))
    for model_name, tmp in _LINKED:
        Model = apps.get_model("Tracker", model_name)
        for pk, loc_id in Model._base_manager.exclude(location_id=None).values_list("pk", "location_id"):
            Model._base_manager.filter(pk=pk).update(**{tmp: names.get(loc_id, "")})


class Migration(migrations.Migration):

    dependencies = [
        ("Tracker", "0218_storage_location_records"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
