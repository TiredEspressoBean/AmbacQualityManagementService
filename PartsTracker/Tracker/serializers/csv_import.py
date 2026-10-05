"""
CSV Import Serializers for bulk data import.

Provides base class and model-specific serializers for importing
data from CSV/Excel files with foreign key resolution and validation.

Supports automatic model introspection for zero-config usage.
"""

import numbers
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from django.db import models, transaction
from django.db.models import Q
from rest_framework import serializers

from Tracker.services.csv_utils import (
    ambiguous_day_month,
    ImportResult,
    parse_date,
    parse_boolean,
    parse_integer,
    parse_decimal,
    parse_time,
)

# Fields to skip during auto-introspection
SKIP_FIELDS = {
    'id', 'tenant', 'created_at', 'updated_at', 'archived',
    'created_by', 'modified_by', 'version', 'previous_version',
    'is_current_version', 'classification',
}


# How a many-to-many column lists its items, on import and export alike.
M2M_SEPARATOR = '; '

# Where `_canonical_columns` keeps an FK's ID when the row also names it.
FK_ID_PREFIX = '__fk_id__'


class ImportMode:
    """Import mode constants."""
    CREATE = 'create'
    UPDATE = 'update'
    UPSERT = 'upsert'

    CHOICES = [
        (CREATE, 'Create only (error if exists)'),
        (UPDATE, 'Update only (error if not found)'),
        (UPSERT, 'Create or update (default)'),
    ]


class BaseCSVImportSerializer(serializers.Serializer):
    """
    Base serializer for CSV imports with FK resolution and upsert support.

    Subclasses should define:
    - Meta.model: The Django model to import into
    - Meta.lookup_fields: Fields to use for finding existing records (in order)
    - Meta.field_mapping: Dict mapping CSV column names to model fields
    - Meta.fk_fields: Dict mapping field name to (Model, lookup_fields) for FK resolution

    Example:
        class PartsCSVImportSerializer(BaseCSVImportSerializer):
            class Meta:
                model = Parts
                lookup_fields = ['id', 'ERP_id']
                field_mapping = {
                    'part_id': 'ERP_id',
                    'type': 'part_type',
                }
                fk_fields = {
                    'part_type': (PartTypes, ['name', 'ERP_id']),
                    'order': (Orders, ['name', 'order_number', 'id']),
                }
    """

    class Meta:
        model = None
        lookup_fields = ['id']
        field_mapping = {}
        fk_fields = {}
        required_fields = []

    def __init__(self, *args, tenant=None, user=None, mode=ImportMode.UPSERT,
                 api_serializer_class=None, api_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.user = user
        self.mode = mode
        self.warnings = []
        # The viewset's own API serializer. An import is another way to write the
        # model, so it may write only what the API accepts, and each row must pass
        # the API's own validation — see `_check_against_api`.
        self.api_serializer_class = api_serializer_class
        self.api_context = api_context or {}

    def resolve_fk(
        self,
        field_name: str,
        value: Any,
        model: Type[models.Model],
        lookup_fields: List[str],
    ) -> Optional[models.Model]:
        """
        Resolve a foreign key value to a model instance.

        Tries each lookup field in order until a match is found.
        Accepts name, ERP_id, id (UUID), or the actual instance.

        Args:
            field_name: Name of the FK field (for error messages)
            value: Value from CSV (name, id, ERP_id, etc.)
            model: Related model class
            lookup_fields: Fields to try for lookup (in order)

        Returns:
            Model instance or None if not found
        """
        if value is None or value == '':
            return None

        # Already a model instance
        if isinstance(value, model):
            return value

        # A step is named with its process ("Pump Build > Assembly"): step names repeat
        # across processes. See Tracker.services.step_refs.
        from Tracker.models import Steps
        if model is Steps:
            from Tracker.services.step_refs import resolve_step_ref
            return resolve_step_ref(value, field_name)

        qs = self._candidates(model)
        # Try each lookup field
        for lookup_field in lookup_fields:
            try:
                # An integer primary key (User): `id` used to go to the UUID branch
                # only, so a user could never be found by ID. A CSV export writes a
                # nullable integer FK as `5.0`, hence the float step.
                int_pk = isinstance(model._meta.pk, (models.AutoField, models.BigAutoField,
                                                     models.IntegerField))
                if lookup_field == 'pk' or (lookup_field == 'id' and int_pk):
                    try:
                        int_val = int(float(str(value)))
                        if str(value).strip() not in (str(int_val), f"{int_val}.0"):
                            continue
                        obj = qs.filter(pk=int_val).first()
                        if obj:
                            return obj
                    except (ValueError, TypeError):
                        continue

                # Handle UUID id field
                elif lookup_field == 'id':
                    try:
                        uuid_val = UUID(str(value))
                        obj = qs.filter(id=uuid_val).first()
                        if obj:
                            return obj
                    except (ValueError, AttributeError):
                        continue

                # Try case-insensitive match for string fields
                else:
                    obj = self._unique_match(qs, lookup_field, value, field_name, model)
                    if obj:
                        return obj
            except serializers.ValidationError:
                raise
            except Exception:
                continue
        return None

    def _candidates(self, model):
        """Rows an import may match: this tenant's, not archived.

        `.objects` scopes by tenant but does not exclude soft-deleted rows, so an
        import used to link to — or upsert onto — a voided record.
        """
        qs = model.objects.all()  # tenant-safe: .objects auto-scopes; tenant narrows further below
        if self.tenant and hasattr(model, 'tenant'):
            qs = qs.filter(tenant=self.tenant)
        if any(f.name == 'archived' for f in model._meta.concrete_fields):
            qs = qs.filter(archived=False)
        return qs

    def _unique_match(self, qs, lookup_field, value, what, model):
        """The ONE row whose `lookup_field` equals `value` (case-insensitive), or None.

        A versioned model's name matches every version, so the current one is preferred
        — `.first()` with no ordering used to pick any version. If more than one row
        still matches, the row is refused rather than guessed: two part types called
        "Injector" are two different things.
        """
        matches = qs.filter(**{f"{lookup_field}__iexact": str(value)})
        if any(f.name == 'is_current_version' for f in model._meta.concrete_fields):
            current = matches.filter(is_current_version=True)
            if current.exists():
                matches = current
        found = list(matches[:2])
        if len(found) > 1:
            raise serializers.ValidationError({what: (
                f"'{value}' matches more than one {model._meta.verbose_name} by "
                f"{lookup_field}. Use its ID to say which.")})
        return found[0] if found else None

    def validate_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate that required fields are present.

        Returns list of missing field names.
        """
        meta = getattr(self, 'Meta', None)
        required = getattr(meta, 'required_fields', [])

        missing = []
        for field in required:
            value = data.get(field)
            if value is None or value == '':
                missing.append(field)

        return missing

    def find_existing(self, data: Dict[str, Any]) -> Optional[models.Model]:
        """
        Find an existing record that matches the import data.

        Uses lookup_fields in order: id, ERP_id, then model-specific fields.
        """
        meta = getattr(self, 'Meta', None)
        model = getattr(meta, 'model', None)
        lookup_fields = getattr(meta, 'lookup_fields', ['id'])

        if not model:
            return None

        qs = self._candidates(model)

        for field in lookup_fields:
            # A combination (`('training_type', 'step')`): the row matches on all of
            # them, references resolved first. Skipped unless every part is given.
            if isinstance(field, (tuple, list)):
                obj = self._find_by_combination(qs, model, field, data)
                if obj:
                    return obj
                continue

            value = data.get(field)
            if value is None or value == '':
                continue

            try:
                # Handle UUID
                if field == 'id':
                    try:
                        uuid_val = UUID(str(value))
                        obj = qs.filter(id=uuid_val).first()
                        if obj:
                            return obj
                    except (ValueError, AttributeError):
                        continue

                # Handle other fields
                obj = self._unique_match(qs, field, value, field, model)
                if obj:
                    return obj

            except serializers.ValidationError:
                raise
            except Exception:
                continue

        return None

    def _fk_by_id_if_it_agrees(self, field_name, row_id, named, model):
        """The row `row_id` names, if its name is `named`; else None.

        An export writes an FK's ID and its name. The name is what a person edits, so it
        decides — but when it still matches the ID's row, that exact row is kept, which
        is what keeps a link to an older version on that version (a name alone finds the
        current one).
        """
        if row_id in (None, ''):
            return None
        obj = None
        try:
            if isinstance(model._meta.pk, (models.AutoField, models.BigAutoField, models.IntegerField)):
                obj = model.objects.filter(pk=int(float(str(row_id)))).first()  # tenant-safe: .objects auto-scopes
            else:
                obj = model.objects.filter(pk=UUID(str(row_id))).first()  # tenant-safe: .objects auto-scopes
        except (ValueError, TypeError):
            return None
        if obj is None:
            return None
        want = str(named).strip().lower()
        names = [getattr(obj, a, None) for a in ('name', 'ERP_id', 'code', 'serial_number',
                                                 'email', 'username', 'error_name', 'label')]
        if model._meta.label == 'Tracker.Steps':
            from Tracker.services.step_refs import step_ref
            names.append(step_ref(obj))
        names.append(str(obj.pk))
        return obj if any(n is not None and str(n).strip().lower() == want for n in names) else None

    def _tenant_timezone(self):
        import zoneinfo
        name = getattr(self.tenant, 'default_timezone', None) or 'UTC'
        try:
            return zoneinfo.ZoneInfo(name)
        except Exception:
            return zoneinfo.ZoneInfo('UTC')

    def _find_by_combination(self, qs, model, fields, data):
        """The one row matching `data` on every field in `fields`, or None.

        A part left blank skips the combination — `('training_type', 'step')` says
        nothing about a row with no step. A part marked `?` (`'part_type?'`) may be
        blank, and then means "has none": the row matches one whose field is empty.
        Values are read as the import reads them (a date typed `1/15/2026` matches the
        stored date), not compared as typed text.
        """
        fk_fields = getattr(getattr(self, 'Meta', None), 'fk_fields', {}) or {}
        lookup = {}
        for f in fields:
            optional = f.endswith('?')
            f = f.rstrip('?')
            value = data.get(f)
            if value is None or value == '':
                if not optional:
                    return None
                mf = model._meta.get_field(f)
                if mf.null:
                    lookup[f"{f}__isnull"] = True
                else:
                    lookup[f] = ''
                continue
            if f in fk_fields:
                fk_model, fk_lookups = fk_fields[f]
                value = (self._fk_by_id_if_it_agrees(f, data.get(FK_ID_PREFIX + f), value, fk_model)
                         or self.resolve_fk(f, value, fk_model, fk_lookups))
                if value is None:
                    return None
                lookup[f] = value
            else:
                saved = list(getattr(self, 'warnings', []))
                value = BaseCSVImportSerializer.transform_data(self, {f: value}).get(f, value)
                self.warnings = saved  # the row's own read reports these
                lookup[f"{f}__iexact" if isinstance(value, str) else f] = value
        matches = qs.filter(**lookup)
        if any(x.name == 'is_current_version' for x in model._meta.concrete_fields):
            current = matches.filter(is_current_version=True)
            if current.exists():
                matches = current
        found = list(matches[:2])
        if len(found) > 1:
            raise serializers.ValidationError({fields[0]: (
                f"More than one {model._meta.verbose_name} matches this "
                f"{' + '.join(fields)}. Use its ID to say which.")})
        return found[0] if found else None

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw CSV data for model creation/update.

        Handles:
        - FK resolution
        - Date parsing
        - Boolean conversion
        - Field name mapping

        Subclasses can override for model-specific transformations.
        """
        meta = getattr(self, 'Meta', None)
        fk_fields = getattr(meta, 'fk_fields', {})
        m2m_fields = getattr(meta, 'm2m_fields', {}) or {}
        model = getattr(meta, 'model', None)

        result = {}

        for field_name, value in data.items():
            # Skip empty values (will use model defaults), and the IDs kept beside an
            # FK's name (read with the FK itself, below).
            if value is None or value == '' or str(field_name).startswith(FK_ID_PREFIX):
                continue

            # FK resolution. A value that names nothing is an error: it used to be a
            # warning, and the row was saved without the reference it asked for.
            if field_name in fk_fields:
                fk_model, fk_lookups = fk_fields[field_name]
                resolved = self._fk_by_id_if_it_agrees(
                    field_name, data.get(FK_ID_PREFIX + field_name), value, fk_model)
                if resolved is None:
                    resolved = self.resolve_fk(field_name, value, fk_model, fk_lookups)
                if resolved is None:
                    raise serializers.ValidationError({field_name: (
                        f"No {fk_model._meta.verbose_name} matches '{value}'.")})
                result[field_name] = resolved
                continue

            # Many-to-many: a list, `Mill 1; Mill 2` (what an export writes). The whole
            # set is replaced; a blank cell leaves it as it is.
            if field_name in m2m_fields:
                rel_model, rel_lookups = m2m_fields[field_name]
                items = []
                for item in (p.strip() for p in str(value).split(M2M_SEPARATOR.strip())):
                    if not item:
                        continue
                    resolved = self.resolve_fk(field_name, item, rel_model, rel_lookups)
                    if resolved is None:
                        raise serializers.ValidationError({field_name: (
                            f"No {rel_model._meta.verbose_name} matches '{item}'.")})
                    items.append(resolved)
                result[field_name] = items
                continue

            # An FK this importer has no lookup for (a part's sampling ruleset, a part
            # type's disassembly process): read it by ID, or a name, like any other. Left
            # as text it reached the model as a string ("must be a ... instance"), so an
            # exported file carrying one couldn't be imported back.
            if model:
                try:
                    plain_fk = model._meta.get_field(field_name)
                except Exception:
                    plain_fk = None
                if isinstance(plain_fk, models.ForeignKey):
                    related = plain_fk.related_model
                    lookups = ['id'] + [f for f in ('name', 'ERP_id', 'code', 'email')
                                        if any(x.name == f for x in related._meta.concrete_fields)]
                    resolved = self.resolve_fk(field_name, value, related, lookups)
                    if resolved is None:
                        raise serializers.ValidationError({field_name: (
                            f"No {related._meta.verbose_name} matches '{value}'.")})
                    result[field_name] = resolved
                    continue

            # Get model field for type conversion
            if model:
                try:
                    model_field = model._meta.get_field(field_name)

                    # A value that doesn't parse used to be dropped silently: the field
                    # kept its old value and the row reported success. Now it is still
                    # skipped, but the row says so.
                    def _unread(kind):
                        self.warnings.append(
                            f"{field_name}: couldn't read {value!r} as {kind}; left unchanged")

                    # Text that Excel stored as a number: a characteristic "7" or a part
                    # number "10045" comes back from an xlsx as 7.0 — written as "7.0",
                    # which is a different value (and versioned the record).
                    if isinstance(model_field, (models.CharField, models.TextField)) \
                            and not isinstance(value, (str, bool)) and isinstance(value, numbers.Real):
                        result[field_name] = (str(int(value)) if float(value).is_integer()
                                              else str(value))
                        continue

                    # Time of day. Left as text it never equalled the stored time, so an
                    # unchanged re-import looked like an edit (and versioned a Shift).
                    if isinstance(model_field, models.TimeField):
                        parsed = parse_time(value)
                        if parsed is None:
                            _unread("a time of day")
                        else:
                            result[field_name] = parsed
                        continue

                    # Structured JSON (a list of break windows, say): written as JSON by
                    # the export, read back the same.
                    if isinstance(model_field, models.JSONField) and isinstance(value, str) \
                            and value.strip()[:1] in ('[', '{'):
                        import json as _json
                        try:
                            result[field_name] = _json.loads(value)
                        except ValueError:
                            _unread("JSON")
                        continue

                    # Date fields
                    if isinstance(model_field, (models.DateField, models.DateTimeField)):
                        parsed = parse_date(value)
                        if not parsed:
                            _unread("a date")
                            continue
                        ambiguous = ambiguous_day_month(value)
                        if ambiguous:
                            self.warnings.append(
                                f"{field_name}: read {value!r} as {parsed:%d %b %Y} (month "
                                f"first). If that's wrong, write dates as YYYY-MM-DD.")
                        if isinstance(model_field, models.DateTimeField):
                            from django.utils import timezone as _tz
                            if _tz.is_naive(parsed):
                                # On the tenant's shop-floor clock — the zone the export
                                # writes in — not the server's.
                                parsed = _tz.make_aware(parsed, self._tenant_timezone())
                        else:
                            parsed = parsed.date()
                        result[field_name] = parsed
                        continue

                    # Boolean fields
                    if isinstance(model_field, models.BooleanField):
                        parsed = parse_boolean(value)
                        if parsed is None:
                            _unread("yes/no")
                        else:
                            result[field_name] = parsed
                        continue

                    # Integer fields
                    if isinstance(model_field, models.IntegerField):
                        parsed = parse_integer(value)
                        if parsed is None:
                            _unread("a whole number")
                        else:
                            result[field_name] = parsed
                        continue

                    # Decimal/Float fields. A DecimalField gets a Decimal: a float never
                    # equals it (92.3 != Decimal('92.30')), so an unchanged value looked
                    # edited and was saved — or versioned.
                    if isinstance(model_field, (models.DecimalField, models.FloatField)):
                        parsed = parse_decimal(value)
                        if parsed is None:
                            _unread("a number")
                        elif isinstance(model_field, models.DecimalField):
                            from decimal import Decimal as _D
                            result[field_name] = _D(str(parsed)).quantize(
                                _D(1).scaleb(-model_field.decimal_places))
                        else:
                            result[field_name] = parsed
                        continue

                except Exception:
                    pass

            # Default: use value as-is
            result[field_name] = value

        return result

    def create_instance(self, data: Dict[str, Any]) -> models.Model:
        """Create a new model instance."""
        meta = getattr(self, 'Meta', None)
        model = getattr(meta, 'model', None)

        if not model:
            raise ValueError("Meta.model not defined")

        # Add tenant if applicable
        if self.tenant and hasattr(model, 'tenant'):
            data['tenant'] = self.tenant

        # Add created_by if applicable
        if self.user and hasattr(model, 'created_by'):
            data['created_by'] = self.user

        return model.objects.create(**data)

    def update_instance(self, instance: models.Model, data: Dict[str, Any]) -> models.Model:
        """Update an existing model instance.

        Saved only when a value actually changes: re-importing an unchanged export
        otherwise wrote every row, bumped every `updated_at`, and filled the audit log
        with edits that changed nothing.
        """
        changed = [f for f, v in data.items() if not self._same(f, getattr(instance, f, None), v)]
        if not changed:
            # Matched and already as the row says: reported as "no change", not as an
            # update — re-uploading an untouched export claimed to update every row.
            self.unchanged = True
            return instance
        changes = {f: data[f] for f in changed}
        meta = getattr(self, 'Meta', None)
        version_kwargs = {'user': self.user, 'change_description': "Imported from a spreadsheet"}

        # An import edits a record the way its API does.
        # - The viewset versions every edit (Shift): `Meta.update_via_new_version`.
        if getattr(meta, 'update_via_new_version', False):
            return self._carry_m2m(instance, instance.create_new_version(**version_kwargs, **changes))
        # - A versioned model whose serializer routes edits through
        #   `apply_versioned_update`: the same routing, with the serializer's own
        #   `_NON_VERSIONING_FIELDS` — a content edit versions, a status flip doesn't.
        non_versioning = getattr(self.api_serializer_class, '_NON_VERSIONING_FIELDS', None)
        if getattr(type(instance), '_is_versioned', False) and non_versioning is not None:
            from Tracker.services.core.versioning import apply_versioned_update
            result = apply_versioned_update(
                instance, changes, non_versioning_fields=non_versioning,
                default_update=self._save_in_place, version_kwargs=version_kwargs)
            return self._carry_m2m(instance, result)
        # - Otherwise in place.
        return self._save_in_place(instance, changes)

    def _save_in_place(self, instance, changes):
        for field_name, value in changes.items():
            setattr(instance, field_name, value)
        if self.user and hasattr(instance, 'modified_by'):
            instance.modified_by = self.user
        instance.save()
        return instance

    def _same(self, field_name, current, new) -> bool:
        """Whether writing `new` would change nothing.

        The column a row was MATCHED on counts the same ignoring case — `cmm` found
        "CMM", so writing `cmm` back is no edit (and must not version the record).
        """
        if current == new:
            return True
        if isinstance(current, str) and isinstance(new, str) and current.lower() == new.lower():
            keys = getattr(getattr(self, 'Meta', None), 'lookup_fields', ()) or ()
            flat = {k.rstrip('?') for key in keys
                    for k in (key if isinstance(key, (tuple, list)) else (key,))}
            return field_name in flat
        return False

    def _carry_m2m(self, old, new):
        """A new version keeps the old one's many-to-many sets.

        `create_new_version` copies columns only, so a row that edited a name — and left
        its steps cell blank — produced a version with no steps. A set the row did give
        is written afterwards by `_write_m2m`.
        """
        if new is old or new is None:
            return new
        given = set(getattr(self, '_pending_m2m', None) or {})
        for field in type(old)._meta.many_to_many:
            if field.name not in given:
                getattr(new, field.name).set(getattr(old, field.name).all())
        return new

    def import_row(self, row_data: Dict[str, Any]) -> Tuple[Optional[models.Model], bool, List[str]]:
        """
        Import a single row of data.

        Returns:
            Tuple of (instance, created, warnings)
            - instance: Created or updated model instance (None on error)
            - created: True if created, False if updated
            - warnings: List of warning messages
        """
        self.warnings = []
        self.unchanged = False

        # Headers arrive lowercased (csv_utils.normalize_header), so a column named after
        # a field with capitals — `ERP_id`, `ID_prefix` — never matched its own field and
        # was refused. Map each column back to the field it names, ignoring case.
        row_data = self._canonical_columns(row_data)

        # Find existing record
        existing = self.find_existing(row_data)

        # Required columns are what a NEW record needs. A row that updates an existing
        # one may carry only the columns it changes (`id,step`).
        if existing is None:
            missing = self.validate_required_fields(row_data)
            if missing:
                raise serializers.ValidationError({
                    field: "This field is required" for field in missing
                })

        # Transform data (FK resolution, type conversion)
        transformed = self.transform_data(row_data)

        # `id` only says which record a row updates; it is never written (a create
        # doesn't get to choose its primary key).
        transformed.pop('id', None)

        # A deleted row that still holds this row's unique key (`Meta.revive_key`) is
        # added back: revived here, before the API check, whose unique validator would
        # otherwise see the archived row and refuse the create as a duplicate.
        revived = False
        revive_key = getattr(getattr(self, 'Meta', None), 'revive_key', ()) or ()
        if existing is None and self.mode != ImportMode.UPDATE and revive_key and all(
                transformed.get(f) not in (None, '') for f in revive_key):
            from Tracker.services.core.soft_delete import find_archived, revive
            archived = find_archived(type(self).Meta.model, self.tenant,
                                     {f: transformed[f] for f in revive_key})
            if archived is not None:
                existing, revived = revive(archived), True

        # Columns whose meaning depends on the matched record (see Parts' step).
        self.resolve_with_existing(row_data, transformed, existing)

        # Only what the API itself accepts, and only if the API would accept it.
        self._check_against_api(transformed, existing)

        # Many-to-many sets are written after the row exists (see _write_m2m).
        m2m_names = getattr(getattr(self, 'Meta', None), 'm2m_fields', {}) or {}
        self._pending_m2m = {f: transformed.pop(f) for f in list(transformed) if f in m2m_names}

        # Handle based on mode
        if self.mode == ImportMode.CREATE and existing and not revived:
            raise serializers.ValidationError(
                f"Record already exists (matched by lookup fields)"
            )
        if self.mode == ImportMode.UPDATE and not existing:
            raise serializers.ValidationError(
                f"Record not found (no match for lookup fields)"
            )
        if existing:
            instance = self.update_instance(existing, transformed)
        else:
            instance = self.create_instance(transformed)
        self._write_m2m(instance)
        return instance, existing is None or revived, self.warnings

    def _write_m2m(self, instance) -> None:
        """Replace each many-to-many set the row gave (a blank cell gave none)."""
        for field_name, items in (getattr(self, '_pending_m2m', None) or {}).items():
            related = getattr(instance, field_name)
            if set(related.values_list('pk', flat=True)) != {i.pk for i in items}:
                related.set(items)


    # System timestamps an export carries. Ignored rather than refused: no import means
    # to set them, and refusing them made every row of a re-imported export fail.
    EXPORT_ONLY_COLUMNS = frozenset({'created_at', 'updated_at'})

    # Columns an import never writes, whatever the file says. `tenant_id` is the one
    # that mattered: every column used to be setattr'd onto the row, so a `tenant_id`
    # column on an update moved the record into another tenant.
    NEVER_IMPORTED = frozenset({
        'id', 'pk', 'tenant', 'tenant_id', 'created_at', 'updated_at', 'created_by',
        'created_by_id', 'modified_by', 'modified_by_id', 'archived', 'deleted_at',
        'version', 'previous_version', 'previous_version_id', 'is_current_version',
        'classification',
    })

    def resolve_with_existing(self, row: Dict[str, Any], transformed: Dict[str, Any],
                              existing) -> None:
        """Resolve columns that need the matched record. Nothing by default."""

    def _canonical_columns(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """`row` with each key renamed to the model field it names, case-insensitively.

        A key that already names a field, or names none, is left as it is (an unknown
        column is refused later, by name, in `_check_against_api`).
        """
        model = getattr(getattr(self, 'Meta', None), 'model', None)
        if model is None:
            return row
        names = {f.name for f in model._meta.get_fields() if getattr(f, 'concrete', False)}
        fks = {n.lower(): n for n in (getattr(self.Meta, 'fk_fields', {}) or {})}
        fks.update({n.lower(): n for n in (getattr(self.Meta, 'm2m_fields', {}) or {})})
        # Plus FKs the importer resolves itself (a part's step): exported by name too.
        fks.update({n.lower(): n for n in (getattr(self.Meta, 'import_only_fields', ()) or ())
                    if isinstance(model._meta.get_field(n), models.ForeignKey)})
        names |= set(fks.values())
        by_lower = {n.lower(): n for n in names}
        out = {}
        fk_names = set(fks.values())
        as_given, by_name = {}, {}  # an FK's own column / its name column
        for k, v in row.items():
            kl = k.lower()
            # Our own export's columns, so an exported file imports back: an older
            # export's looked-up ID column (`Part Type (auto)`) is a formula with no
            # stored value, and the timestamps are the system's.
            if kl.endswith('(auto)') or kl in self.EXPORT_ONLY_COLUMNS:
                continue
            key = k if k in names else by_lower.get(kl)
            if key in fk_names:
                as_given[key] = v
                continue
            if key is not None:
                out[key] = v
                continue
            # An FK exported by name (`part_type__name`, labelled `Part Type Name`) is
            # the FK itself: resolve_fk looks it up by name.
            for suffix in ('__name', '_name', '__email', '_email', '__ref', '_ref'):
                base = kl[:-len(suffix)] if kl.endswith(suffix) else None
                if base in fks:
                    by_name[fks[base]] = v
                    break
            else:
                out[k] = v
        # An FK given both ways — an export writes its ID and its name — is resolved by
        # the name, with the ID kept beside it (`FK_ID_PREFIX`): where the ID's row has
        # that name, the ID wins, so a link to an older version stays on it; where the
        # name was changed, the name wins.
        for f in fk_names:
            given, named = as_given.get(f), by_name.get(f)
            if named not in (None, ''):
                out[f] = named
                if given not in (None, ''):
                    out[FK_ID_PREFIX + f] = given
            elif f in as_given:
                out[f] = given
        return out

    def _writable_columns(self) -> set:
        """Columns this import may write: the API serializer's writable fields.

        Without an API serializer, the model's own editable concrete fields. Either way
        NEVER_IMPORTED is excluded, and a subclass may add columns it consumes itself
        (`Meta.import_only_fields`, e.g. a quantity that becomes parts).
        """
        extra = set(getattr(getattr(self, 'Meta', None), 'import_only_fields', ()) or ())
        if self.api_serializer_class is not None:
            api = self.api_serializer_class(context=self.api_context)
            cols = {name for name, f in api.fields.items() if not f.read_only}
        else:
            model = getattr(getattr(self, 'Meta', None), 'model', None)
            cols = {f.name for f in model._meta.concrete_fields
                    if getattr(f, 'editable', True)} if model else set()
        return (cols | extra) - self.NEVER_IMPORTED

    def _shown_columns(self) -> set:
        """Every field the API shows, read-only ones included (what an export carries)."""
        if self.api_serializer_class is not None:
            return set(self.api_serializer_class(context=self.api_context).fields)
        model = getattr(getattr(self, 'Meta', None), 'model', None)
        return {f.name for f in model._meta.concrete_fields} if model else set()

    @staticmethod
    def _unchanged(column: str, value, existing) -> bool:
        """Whether `value` is what `existing` already holds for `column` — or, for a new
        record, blank or false: either way, importing it would change nothing."""
        def norm(v):
            if isinstance(v, models.Model):
                v = v.pk
            return '' if v is None else str(v).strip().lower()
        if existing is None:
            return norm(value) in ('', 'false', '0')
        model = type(existing)
        try:
            attname = model._meta.get_field(column.removesuffix('_id')).attname
        except Exception:
            return False
        return norm(value) == norm(getattr(existing, attname, None))

    def _check_against_api(self, transformed: Dict[str, Any], existing) -> None:
        """Refuse a row the API would refuse.

        Two checks. (1) Every column must be one the API accepts — an import used to
        write any model field, including ones the API deliberately keeps read-only, by
        `create(**data)` / `setattr` + `save()`. (2) The row must pass the API
        serializer's own validation (its `validate()` and field rules), as a partial
        update of the matched record. The import's own create/update still does the
        write, so model-specific import behaviour (a work order's parts, appended
        notes) is kept.
        """
        allowed = self._writable_columns()
        shown = self._shown_columns()
        refused, ignored = [], []
        for k in sorted(k for k in transformed if k not in allowed):
            # A column the import can't write is IGNORED, never written, when it is one
            # an export carries: a read-only field the API shows, or a system field
            # holding the value the record already has. Anything else — a system field
            # being changed (`tenant_id` to another tenant), or a column that names no
            # field (usually a typo) — is refused, so it can't pass unnoticed.
            system = k in self.NEVER_IMPORTED or k.removesuffix('_id') in self.NEVER_IMPORTED
            if (self._unchanged(k, transformed[k], existing) if system else k in shown):
                ignored.append(k)
            else:
                refused.append(k)
        if refused:
            raise serializers.ValidationError({
                k: "Can't be imported — the API doesn't accept this field." for k in refused})
        for k in ignored:
            transformed.pop(k)
        if ignored:
            self.warnings.append(f"Read-only, so not imported: {', '.join(ignored)}.")
        if self.api_serializer_class is None:
            return
        import datetime as _dt
        # An update is checked as the API checks a PATCH; a create as it checks a POST —
        # partial there left a serializer's own "which of these" rules (a training
        # requirement's scope) looking at keys it never got.
        partial = existing is not None
        api = self.api_serializer_class(instance=existing, data={}, partial=True,
                                        context=self.api_context)
        payload = {}
        for k, v in transformed.items():
            field = api.fields.get(k)
            if isinstance(v, models.Model):
                v = v.pk
            elif isinstance(v, list):
                v = [i.pk if isinstance(i, models.Model) else i for i in v]
            elif (isinstance(field, serializers.DateField) and not isinstance(field, serializers.DateTimeField)
                  and isinstance(v, _dt.datetime)):
                v = v.date()
            payload[k] = v
        checker = self.api_serializer_class(instance=existing, data=payload, partial=partial,
                                            context=self.api_context)
        checker.is_valid(raise_exception=True)


# ===== Model-specific CSV Import Serializers =====


class PartTypesCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for PartTypes."""

    class Meta:
        from Tracker.models import PartTypes
        model = PartTypes
        lookup_fields = ['id', 'ERP_id', 'name']
        field_mapping = {}
        fk_fields = {}
        required_fields = ['name']


class PartsCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Parts."""

    class Meta:
        from Tracker.models import Parts, PartTypes, Orders, WorkOrder, Steps
        model = Parts
        lookup_fields = ['id', 'ERP_id']
        field_mapping = {
            'part_id': 'ERP_id',
            'type': 'part_type',
            'status': 'part_status',
        }
        fk_fields = {
            'part_type': (PartTypes, ['name', 'ERP_id', 'id']),
            'order': (Orders, ['name', 'order_number', 'id']),
            'work_order': (WorkOrder, ['ERP_id', 'id']),
            # `step` is NOT resolved here: a step name is only meaningful within the
            # part's own process — see resolve_with_existing.
        }
        required_fields = ['part_type']
        # Placing parts at a step is what loading in-flight work means, so an import may
        # set it although the API keeps `step` read-only (the API moves a part through
        # the advancement engine). It is set directly, as a change-control RELOCATE is:
        # no step executions are created for the steps it skips.
        import_only_fields = ['step']
        import_column_help = {
            'step': ("Step name within the part's work-order process (or its ID). Needs "
                     "work_order on the row or already on the part. Not for reman cores."),
        }

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for Parts."""
        result = super().transform_data({k: v for k, v in data.items() if k != 'step'})

        # Handle part_status choices validation
        from Tracker.models import PartsStatus
        if 'part_status' in result:
            status_value = str(result['part_status']).upper()
            valid_statuses = [s.value for s in PartsStatus]
            if status_value in valid_statuses:
                result['part_status'] = status_value
            else:
                self.warnings.append(f"Invalid part_status '{result['part_status']}', using PENDING")
                result['part_status'] = PartsStatus.PENDING

        return result

    def resolve_with_existing(self, row, transformed, existing) -> None:
        """Resolve `step` within the part's process: its work order's, from the file or
        from the part being updated.

        Step names repeat across processes ("Assembly" is in most of them), so a
        tenant-wide name match is usually ambiguous and, when it isn't, may be the wrong
        process's step. A core's part is refused: its position follows its reman stage,
        and it moves through the reman actions.
        """
        from Tracker.models import ProcessStep, Steps
        from Tracker.services.step_refs import SEPARATOR, step_ref
        raw = row.get('step')
        if raw in (None, ''):
            return
        # The step it is already at (an exported file, imported back) moves nothing, so it
        # is no attempt to move a core either.
        if existing is not None and existing.step_id is not None and str(raw) in (
                str(existing.step_id), existing.step.name, step_ref(existing.step)):
            return
        # `Process > Step` (what an export writes): the step name is resolved within the
        # part's own process below, so only that half is needed.
        if SEPARATOR in str(raw):
            raw = str(raw).split(SEPARATOR, 1)[1].strip()
        # A missing reverse one-to-one raises a subclass of AttributeError, so getattr's
        # default covers an ordinary part.
        if existing is not None and getattr(existing, 'core_role', None) is not None:
            raise serializers.ValidationError({'step': (
                "This part is a reman core; its step follows its stage. Move it with "
                "the core's teardown and rebuild actions instead.")})
        wo = transformed.get('work_order') or getattr(existing, 'work_order', None)
        process = getattr(wo, 'process', None)
        if process is None:
            raise serializers.ValidationError({'step': (
                "A step can only be set for a part on a work order with a process — "
                "give the work_order too.")})
        in_process = Steps.objects.filter(  # tenant-safe: .objects auto-scopes; narrowed to this process's steps
            id__in=ProcessStep.objects.filter(process=process).values('step_id'))  # tenant-safe: scoped by `process` FK
        step = None
        try:
            from uuid import UUID
            step = in_process.filter(id=UUID(str(raw))).first()
        except (ValueError, AttributeError):
            step = self._unique_match(in_process, 'name', raw, 'step', Steps)
        if step is None:
            raise serializers.ValidationError({'step': (
                f"'{raw}' is not a step of {process} (work order {wo}).")})
        transformed['step'] = step


class OrdersCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Orders."""

    class Meta:
        from Tracker.models import Orders, Companies, User
        model = Orders
        lookup_fields = ['id', 'order_number', 'name']
        field_mapping = {
            'status': 'order_status',
            'customer_name': 'customer',
        }
        fk_fields = {
            'company': (Companies, ['name', 'id']),
            'customer': (User, ['email', 'username', 'id']),
        }
        required_fields = ['name']

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for Orders."""
        result = super().transform_data(data)

        # Handle order_status choices validation
        from Tracker.models import OrdersStatus
        if 'order_status' in result:
            status_value = str(result['order_status']).upper()
            valid_statuses = [s.value for s in OrdersStatus]
            if status_value in valid_statuses:
                result['order_status'] = status_value
            else:
                self.warnings.append(f"Invalid order_status '{result['order_status']}', using PENDING")
                result['order_status'] = OrdersStatus.PENDING

        return result


class WorkOrderCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for WorkOrders.

    Build-plan-aware. Maps planner spreadsheet columns to WorkOrder fields,
    silently drops known-legacy ERP columns (PC, Dept, WC Desc., Line, …)
    that don't map to anything in UQMES yet, and warns on truly unknown
    columns so typos get caught instead of silently failing the import.

    On upsert, the `notes` field is *appended* to rather than overwritten;
    identical lines are de-duped so re-importing the same plan doesn't
    bloat the field.
    """

    # Legacy ERP / build-plan columns we know about but deliberately don't
    # map to WorkOrder fields. Dropped silently — no warning, no metadata
    # bucket. Keys are in their *normalized* form (lower-snake-case as
    # produced by `normalize_header`).
    KNOWN_IGNORED_COLUMNS = {
        'pc',
        'description',
        'dept',
        'wc_desc',
        'wc_desc.',
        'op/area',
        'op_area',
        'last_op',
        'oh',
        'line',
    }

    class Meta:
        from Tracker.models import WorkOrder, Orders, PartTypes, Processes
        model = WorkOrder
        lookup_fields = ['id', 'ERP_id']
        field_mapping = {
            'wo_number': 'ERP_id',
            'item': 'part_type_erp_id',  # Special handling
            'due_date': 'expected_completion',
            'start_date': 'expected_start',
            'req/note': 'notes',
            'req_note': 'notes',
        }
        fk_fields = {
            'related_order': (Orders, ['name', 'order_number', 'id']),
            'process': (Processes, ['name', 'id']),
        }
        required_fields = ['ERP_id', 'quantity']

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for WorkOrders."""
        # Drop known-legacy columns silently. They land in `data` because the
        # parse-time field_mapping didn't recognize them. Stripping here keeps
        # them out of `create(**data)` and out of the unknown-column warning.
        data = {
            k: v for k, v in data.items()
            if k not in self.KNOWN_IGNORED_COLUMNS
        }

        # Warn on columns that aren't on the model AND aren't known-ignored.
        # These are typos or columns we haven't been told about — surface
        # them so the planner can fix the source before the next import.
        from Tracker.models import WorkOrder as _WO
        model_field_names = {f.name for f in _WO._meta.get_fields()}
        # `part_type_erp_id` is consumed below for FK resolution, not a model
        # field. fk_fields kwargs are also acceptable transport keys.
        fk_fields = getattr(self.Meta, 'fk_fields', {})
        allowed_transport_keys = (
            model_field_names
            | set(fk_fields.keys())
            | {'part_type_erp_id'}
        )
        for key in list(data.keys()):
            if key not in allowed_transport_keys:
                self.warnings.append(f"Unknown column '{key}' - ignored")

        result = super().transform_data(data)
        # `part_type_erp_id` is a transport-only key; remove from result so
        # `create(**result)` doesn't fail with an unexpected kwarg.
        result.pop('part_type_erp_id', None)

        # Handle part_type_erp_id -> find process for part type
        part_type_ref = data.get('part_type_erp_id') or data.get('part_type')
        if part_type_ref and 'process' not in result:
            from Tracker.models import PartTypes, Processes, ProcessStatus
            pt = self.resolve_fk('part_type', part_type_ref, PartTypes, ['name', 'ERP_id', 'id'])
            if pt:
                # Find approved process for this part type
                process = Processes.objects.filter(
                    part_type=pt,
                    status__in=[ProcessStatus.APPROVED, ProcessStatus.DEPRECATED],
                    is_current_version=True
                ).first()
                if process:
                    result['process'] = process
                else:
                    self.warnings.append(f"No approved process found for part type '{pt.name}'")

        # Handle workorder_status choices validation
        from Tracker.models import WorkOrderStatus
        if 'workorder_status' in result:
            status_value = str(result['workorder_status']).upper()
            valid_statuses = [s.value for s in WorkOrderStatus]
            if status_value in valid_statuses:
                result['workorder_status'] = status_value
            else:
                self.warnings.append(f"Invalid workorder_status, using PENDING")
                result['workorder_status'] = WorkOrderStatus.PENDING

        return result

    def create_instance(self, data: Dict[str, Any]) -> 'WorkOrder':
        """Create work order with parts if quantity specified."""
        from Tracker.models import WorkOrder

        quantity = data.pop('quantity', 1)
        instance = super().create_instance(data)

        # Create parts if process is set
        if instance.process and quantity > 0:
            instance.create_parts(quantity, user=self.user)

        return instance

    def update_instance(self, instance, data: Dict[str, Any]):
        """Override notes-write to append-and-dedupe instead of overwriting.

        Re-importing the same plan over the same WO should *grow* the notes
        field with new lines, not replace the existing one. Identical lines
        are skipped so repeat imports don't bloat the field.
        """
        if 'notes' in data:
            new_line = (data['notes'] or '').strip()
            if new_line:
                existing = (instance.notes or '').rstrip()
                existing_lines = {ln.strip() for ln in existing.splitlines()}
                if new_line in existing_lines:
                    # Already present — leave notes untouched.
                    data.pop('notes')
                else:
                    data['notes'] = f"{existing}\n{new_line}" if existing else new_line
            else:
                # Empty CSV cell: don't blow away existing notes.
                data.pop('notes')
        return super().update_instance(instance, data)


class EquipmentCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Equipment."""

    class Meta:
        from Tracker.models import Equipments, EquipmentType
        model = Equipments
        lookup_fields = ['id', 'serial_number', 'name']
        field_mapping = {
            'type': 'equipment_type',
        }
        fk_fields = {
            'equipment_type': (EquipmentType, ['name', 'id']),
        }
        required_fields = ['name', 'equipment_type']


class QualityReportsCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for QualityReports."""

    class Meta:
        from Tracker.models import QualityReports, Parts, Steps, User
        model = QualityReports
        lookup_fields = ['id']
        field_mapping = {
            'inspector': 'recorded_by',
        }
        fk_fields = {
            'part': (Parts, ['ERP_id', 'id']),
            'step': (Steps, ['name', 'id']),
            'recorded_by': (User, ['email', 'username', 'id']),
        }
        required_fields = ['part']


# ===== Serializer Registry =====

CSV_IMPORT_SERIALIZERS = {
    'part-types': PartTypesCSVImportSerializer,
    'parttypes': PartTypesCSVImportSerializer,
    'parts': PartsCSVImportSerializer,
    'orders': OrdersCSVImportSerializer,
    'work-orders': WorkOrderCSVImportSerializer,
    'workorders': WorkOrderCSVImportSerializer,
    'equipment': EquipmentCSVImportSerializer,
    'equipments': EquipmentCSVImportSerializer,
    'quality-reports': QualityReportsCSVImportSerializer,
    'qualityreports': QualityReportsCSVImportSerializer,
}


def get_csv_import_serializer(model_name: str) -> Optional[Type[BaseCSVImportSerializer]]:
    """
    Get the CSV import serializer class for a model name.

    Args:
        model_name: Model name or URL path segment (e.g., 'parts', 'work-orders')

    Returns:
        Serializer class or None if not found
    """
    return CSV_IMPORT_SERIALIZERS.get(model_name.lower())


# ===== Automatic Serializer Generation =====

def introspect_model_for_import(model: Type[models.Model]) -> Dict[str, Any]:
    """
    Introspect a Django model to auto-generate import serializer configuration.

    Returns:
        Dict with lookup_fields, fk_fields, required_fields
    """
    lookup_fields = ['id']
    fk_fields = {}
    m2m_fields = {}
    required_fields = []

    def best_lookups(related_model):
        lookups = ['id']
        for fk_field in ['name', 'ERP_id', 'order_number', 'email', 'username', 'serial_number']:
            if hasattr(related_model, fk_field):
                lookups.insert(0, fk_field)
        return lookups

    # Check for common lookup fields
    for field_name in ['ERP_id', 'name', 'serial_number', 'order_number', 'code']:
        if hasattr(model, field_name):
            lookup_fields.append(field_name)

    for model_field in model._meta.get_fields():
        # Skip reverse relations
        if model_field.auto_created and not model_field.concrete:
            continue

        # Skip system fields
        if model_field.name in SKIP_FIELDS:
            continue

        # Handle ForeignKey - auto-configure FK lookups
        if isinstance(model_field, models.ForeignKey):
            related_model = model_field.related_model

            fk_fields[model_field.name] = (related_model, best_lookups(related_model))

            # FK required if not null/blank
            if not model_field.null and not model_field.blank:
                required_fields.append(model_field.name)
            continue

        # ManyToMany: a `; `-separated list, each item resolved like an FK
        if isinstance(model_field, models.ManyToManyField):
            m2m_fields[model_field.name] = (model_field.related_model,
                                            best_lookups(model_field.related_model))
            continue

        # Track required fields (not null, not blank, no default)
        if hasattr(model_field, 'blank') and hasattr(model_field, 'null'):
            has_default = model_field.has_default()
            if not model_field.blank and not model_field.null and not has_default:
                required_fields.append(model_field.name)

    return {
        'lookup_fields': lookup_fields,
        'fk_fields': fk_fields,
        'm2m_fields': m2m_fields,
        'required_fields': required_fields,
    }


def create_import_serializer_for_model(
    model: Type[models.Model],
    extra_fk_fields: Optional[Dict] = None,
    extra_required_fields: Optional[List[str]] = None,
    extra_lookup_fields: Optional[List[str]] = None,
    lookup_fields: Optional[List] = None,
    base: Type['BaseCSVImportSerializer'] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Type[BaseCSVImportSerializer]:
    """
    Dynamically create a CSV import serializer for any Django model.

    This function introspects the model and creates a serializer class
    with appropriate FK resolution, lookup fields, and required field validation.

    Args:
        model: Django model class
        extra_fk_fields: Additional FK field configurations to merge
        extra_required_fields: Additional required fields
        extra_lookup_fields: Additional lookup fields

    Returns:
        A new serializer class for the model

    Example:
        # Auto-create serializer for any model
        MyModelSerializer = create_import_serializer_for_model(MyModel)

        # Use in viewset
        serializer = MyModelSerializer(tenant=tenant, user=user)
        instance, created, warnings = serializer.import_row(row_data)
    """
    # Introspect model
    config = introspect_model_for_import(model)

    # Merge extra config
    if extra_fk_fields:
        config['fk_fields'].update(extra_fk_fields)
    if extra_required_fields:
        config['required_fields'].extend(extra_required_fields)
    if extra_lookup_fields:
        config['lookup_fields'].extend(extra_lookup_fields)
    if lookup_fields is not None:
        # How an existing row is found, in order. An entry may be a tuple — a
        # combination the row must match on all of: ('training_type', 'step').
        config['lookup_fields'] = list(lookup_fields)

    # Create Meta class dynamically
    meta_attrs = {
        'model': model,
        'lookup_fields': config['lookup_fields'],
        'fk_fields': config['fk_fields'],
        'm2m_fields': config['m2m_fields'],
        'required_fields': config['required_fields'],
        'field_mapping': {},
    }
    # Anything else a Meta takes — `update_via_new_version`, `import_only_fields`,
    # `import_column_help` — or an override of the above.
    meta_attrs.update(meta or {})
    Meta = type('Meta', (), meta_attrs)

    # Create serializer class dynamically
    serializer_class = type(
        f'{model.__name__}CSVImportSerializer',
        (base or BaseCSVImportSerializer,),
        {'Meta': Meta}
    )

    return serializer_class


def get_or_create_import_serializer(
    model: Type[models.Model]
) -> Type[BaseCSVImportSerializer]:
    """
    Get a registered import serializer or create one dynamically.

    First checks the registry for a custom serializer, then falls back
    to auto-generating one via model introspection.

    Args:
        model: Django model class

    Returns:
        Serializer class for the model
    """
    # Try registry first (for custom serializers)
    model_name = model.__name__.lower()
    registered = CSV_IMPORT_SERIALIZERS.get(model_name)
    if registered:
        return registered

    # Try with hyphens
    hyphenated = ''.join([
        f'-{c.lower()}' if c.isupper() else c
        for c in model.__name__
    ]).lstrip('-')
    registered = CSV_IMPORT_SERIALIZERS.get(hyphenated)
    if registered:
        return registered

    # Auto-create
    return create_import_serializer_for_model(model)
