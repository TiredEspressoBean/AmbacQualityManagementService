"""Loading history at go-live: training records and material lots from the old system.

History brought in at go-live wasn't captured here, so it is loaded as a controlled
record of where it came from (ISO 9001 7.5, AS9100): every row belongs to a
`MigrationBatch` (what, from which system, who loaded it, when, how many rows) and
carries a `source_reference` — where its original evidence lives. The batch is verified
ONCE, by a person, after the load (quantities against the go-live count, a sample of
records against the originals); rows aren't approved one by one.

- Training records count toward qualification straight away, and must name their
  source.
- Material lots come in ACCEPTED when they carry traceability — a supplier lot or cert
  reference, and an expiry wherever the material has a shelf life. Without it they land
  in QUARANTINE with a hold reason naming what's missing: uncertified stock is held, as
  an auditor would expect.

Both are create-only (a migration adds history, it never rewrites it) and refuse a row
that's already here: the same person + training + date, or a lot number in use.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from Tracker.services.csv_utils import ImportResult, parse_date, parse_integer

KIND_TRAINING = 'TRAINING_RECORDS'
KIND_LOTS = 'MATERIAL_LOTS'


def _col(row: dict, *names):
    lowered = {str(k).lower(): v for k, v in row.items()}
    for n in names:
        v = lowered.get(n.lower())
        if v not in (None, '') and str(v).strip() != '':
            return v
    return None


def _need(value, what):
    if value in (None, ''):
        raise serializers.ValidationError({what: "Required."})
    return value


def _date(value, what, *, required=False):
    if value in (None, ''):
        if required:
            raise serializers.ValidationError({what: "Required."})
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise serializers.ValidationError({what: f"'{value}' isn't a date (use YYYY-MM-DD)."})
    return parsed.date() if hasattr(parsed, 'date') else parsed


def _user(value, what):
    from Tracker.models import User
    v = str(value).strip()
    found = (User.objects.filter(email__iexact=v).first()  # tenant-safe: User isn't tenant-scoped; narrowed by tenant below
             or User.objects.filter(username__iexact=v).first())  # tenant-safe: as above
    if found is None:
        raise serializers.ValidationError({what: f"No user has the email or username '{v}'."})
    return found


def _by_name(model, value, what, fields=('name',)):
    from uuid import UUID
    qs = model.objects.filter(archived=False)  # tenant-safe: .objects auto-scopes to the request tenant
    if any(f.name == 'is_current_version' for f in model._meta.concrete_fields):
        qs = qs.filter(is_current_version=True)
    try:
        found = model.objects.filter(pk=UUID(str(value))).first()  # tenant-safe: .objects auto-scopes
        if found:
            return found
    except ValueError:
        pass
    for f in fields:
        matches = list(qs.filter(**{f"{f}__iexact": str(value).strip()})[:2])
        if len(matches) > 1:
            raise serializers.ValidationError({what: f"'{value}' matches more than one — use its ID."})
        if matches:
            return matches[0]
    raise serializers.ValidationError({what: f"Nothing matches '{value}'."})


def start_batch(*, tenant, user, kind: str, source_system: str, notes: str = ''):
    from Tracker.models import MigrationBatch
    if not (source_system or '').strip():
        raise serializers.ValidationError(
            {'source_system': "Name the system this history comes from."})
    return MigrationBatch.objects.create(
        tenant=tenant, kind=kind, source_system=source_system.strip(), notes=notes,
        imported_by=user)


def import_training_records(rows, *, batch, user) -> dict:
    from Tracker.models import TrainingRecord, TrainingType
    result = ImportResult()
    for i, row in enumerate(rows, start=1):
        sid = transaction.savepoint()
        try:
            person = _user(_need(_col(row, 'user', 'email', 'user__email', 'person'), 'user'),
                           'user')
            if getattr(person, 'tenant_id', None) not in (None, batch.tenant_id):
                raise serializers.ValidationError({'user': "That user belongs to another tenant."})
            ttype = _by_name(TrainingType, _need(_col(row, 'training_type',
                                                      'training_type__name', 'training'),
                                                 'training_type'), 'training_type')
            completed = _date(_col(row, 'completed_date', 'completed', 'date'),
                              'completed_date', required=True)
            source_ref = _col(row, 'source_reference', 'source', 'evidence')
            if source_ref is None:
                raise serializers.ValidationError({'source_reference': (
                    "Required: where the original record lives (e.g. 'HR system, cert "
                    "#4471'). Migrated history must point at its evidence.")})
            if TrainingRecord.objects.filter(  # tenant-safe: .objects auto-scopes
                    archived=False, user=person, training_type=ttype,
                    completed_date=completed).exists():
                raise serializers.ValidationError(
                    "Already here: this person has this training on that date.")
            fields = dict(tenant=batch.tenant, user=person, training_type=ttype,
                          completed_date=completed, migration_batch=batch,
                          source_reference=str(source_ref).strip())
            level = _col(row, 'level', 'competency_level')
            if level is not None:
                parsed = parse_integer(level)
                if parsed is None:
                    raise serializers.ValidationError({'level': f"'{level}' isn't a level."})
                fields['level'] = parsed
            expires = _date(_col(row, 'expires_date', 'expires', 'expiry'), 'expires_date')
            if expires is not None:
                fields['expires_date'] = expires
            trainer = _col(row, 'trainer', 'trainer__email')
            if trainer is not None:
                fields['trainer'] = _user(trainer, 'trainer')
            notes = _col(row, 'notes')
            if notes is not None:
                fields['notes'] = str(notes)
            rec = TrainingRecord.objects.create(**fields)  # tenant-safe: fields carries tenant=batch.tenant
            transaction.savepoint_commit(sid)
            result.add_created(i, rec.id)
        except serializers.ValidationError as e:
            transaction.savepoint_rollback(sid)
            result.add_error(i, e.detail)
    _finish(batch, result)
    return result.to_response()


def import_material_lots(rows, *, batch, user) -> dict:
    from Tracker.models import Companies, Material, MaterialLot, PartTypes
    result = ImportResult()
    for i, row in enumerate(rows, start=1):
        sid = transaction.savepoint()
        try:
            lot_number = str(_need(_col(row, 'lot_number', 'lot'), 'lot_number')).strip()
            if MaterialLot.objects.filter(lot_number__iexact=lot_number).exists():  # tenant-safe: .objects auto-scopes
                raise serializers.ValidationError({'lot_number': f"Lot {lot_number} is already here."})
            material = material_type = None
            if _col(row, 'material', 'material__name') is not None:
                material = _by_name(Material, _col(row, 'material', 'material__name'),
                                    'material', ('part_number', 'name'))
            if _col(row, 'material_type', 'part_type', 'material_type__name') is not None:
                material_type = _by_name(
                    PartTypes, _col(row, 'material_type', 'part_type', 'material_type__name'),
                    'material_type', ('ERP_id', 'name'))
            if (material is None) == (material_type is None):
                raise serializers.ValidationError(
                    "Name exactly one of material (a raw material) or material_type (a part).")
            try:
                qty = Decimal(str(_need(_col(row, 'quantity', 'qty'), 'quantity')).strip())
                remaining = Decimal(str(_col(row, 'quantity_remaining', 'on_hand') or qty).strip())
            except InvalidOperation:
                raise serializers.ValidationError({'quantity': "Quantities must be numbers."})
            supplier = None
            if _col(row, 'supplier', 'supplier__name') is not None:
                supplier = _by_name(Companies, _col(row, 'supplier', 'supplier__name'), 'supplier')
            supplier_lot = _col(row, 'supplier_lot_number', 'supplier_lot')
            source_ref = _col(row, 'source_reference', 'cert_reference', 'cert', 'certificate')
            expiry = _date(_col(row, 'expiration_date', 'expiry', 'expires'), 'expiration_date')

            # Traceability decides where the lot lands: accepted, or held.
            missing = []
            if supplier_lot is None and source_ref is None:
                missing.append("a supplier lot number or certificate reference")
            if expiry is None and _has_shelf_life(material, material_type):
                missing.append("an expiry date (this material has a shelf life)")
            status = 'QUARANTINE' if missing else 'ACCEPTED'

            lot = MaterialLot.objects.create(
                tenant=batch.tenant, lot_number=lot_number, material=material,
                material_type=material_type, supplier=supplier,
                supplier_lot_number=str(supplier_lot or ''),
                quantity=qty, quantity_remaining=remaining,
                unit_of_measure=str(_col(row, 'unit_of_measure', 'uom') or 'EA'),
                status=status,
                # A hold is a short code the receiving queue explains; what's missing is
                # in the row's warning. A held lot lands in incoming inspection to review.
                hold_reason='MIGRATED_UNTRACEABLE' if missing else '',
                received_date=_date(_col(row, 'received_date', 'received'), 'received_date'),
                manufacture_date=_date(_col(row, 'manufacture_date'), 'manufacture_date'),
                expiration_date=expiry,
                storage_location=str(_col(row, 'storage_location', 'location') or ''),
                received_by=user, migration_batch=batch,
                source_reference=str(source_ref or ''))
            transaction.savepoint_commit(sid)
            result.add_created(i, lot.id, [
                "Quarantined: migrated without " + " and ".join(missing) + "."] if missing else None)
        except serializers.ValidationError as e:
            transaction.savepoint_rollback(sid)
            result.add_error(i, e.detail)
    _finish(batch, result)
    return result.to_response()


def _has_shelf_life(material, material_type) -> bool:
    """Whether this item carries a calendar (shelf-life) life limit."""
    if material_type is None:
        return False
    from Tracker.models import PartTypeLifeLimit
    return PartTypeLifeLimit.objects.filter(  # tenant-safe: narrowed to one in-tenant part type
        part_type=material_type, archived=False,
        definition__is_calendar_based=True).exists()


def _finish(batch, result) -> None:
    batch.row_count = result.to_response()['summary']['created']
    batch.save(update_fields=['row_count', 'updated_at'])


def verify_batch(batch, *, user, notes: str = ''):
    """The one sign-off a migration gets: a person confirms the load was checked."""
    from django.utils import timezone
    if batch.verified_at is not None:
        raise serializers.ValidationError({'detail': "This batch is already verified."})
    if batch.imported_by_id == getattr(user, 'id', None):
        raise serializers.ValidationError(
            {'detail': "Someone other than the person who loaded it verifies a migration."})
    batch.verified_by = user
    batch.verified_at = timezone.now()
    if notes:
        batch.verification_notes = notes
    batch.save(update_fields=['verified_by', 'verified_at', 'verification_notes', 'updated_at'])
    return batch
