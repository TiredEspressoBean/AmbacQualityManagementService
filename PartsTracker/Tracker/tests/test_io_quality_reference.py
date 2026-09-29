"""Import/export for quality and reference catalogs.

QualityErrorsList (the defect catalog), MeasurementDefinition, PartTypeLifeLimit,
ExternalContact and RepairCode. Shape follows test_io_examples.py (see io_base.py).

Three of these are versioned and their API versions a content edit, so an import edit
creates a new version: the tests read the CURRENT version back after an update.
"""
from Tracker.tests.io_base import ImportExportTestCase


def _process_steps(tenant, part_type, process_names, step_names):
    """`{(process, step): Steps}` — each process gets its own step of each name."""
    from Tracker.models import Processes, ProcessStep, Steps
    steps = {}
    for pname in process_names:
        proc = Processes.objects.create(tenant=tenant, name=pname, part_type=part_type,
                                        status="APPROVED")
        for i, sname in enumerate(step_names, start=1):
            st = Steps.objects.create(tenant=tenant, part_type=part_type, name=sname)
            ProcessStep.objects.create(process=proc, step=st, order=i)
            steps[(pname, sname)] = st
    return steps


class ErrorTypeImportExportTests(ImportExportTestCase):
    endpoint = "Error-types"
    tenant_slug = "io-errortype"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import PartTypes, QualityErrorsList
        cls.injector = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
        # "Crack" twice: a general entry and one for injectors. Only the part type —
        # or its absence — says which.
        cls.general = QualityErrorsList.objects.create(
            tenant=cls.tenant, error_name="Crack", error_example="Any visible crack")
        cls.specific = QualityErrorsList.objects.create(
            tenant=cls.tenant, error_name="Crack", error_example="Crack at the nozzle seat",
            part_type=cls.injector, requires_3d_annotation=True)

    def test_a_typed_csv_creates_error_types(self):
        from Tracker.models import QualityErrorsList
        body = self.import_csv(
            "error_name,error_example,part_type,requires_3d_annotation\n"
            "Porosity,Pinholes in the casting,Injector,yes\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        e = QualityErrorsList.objects.get(error_name="Porosity")
        self.assertEqual(e.part_type_id, self.injector.id)
        self.assertTrue(e.requires_3d_annotation)

    def test_a_blank_part_type_matches_the_general_entry(self):
        from Tracker.models import QualityErrorsList
        body = self.import_csv(
            "error_name,part_type,error_example\nCrack,,Hairline or through crack\n",
            mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = QualityErrorsList.objects.get(
            error_name="Crack", part_type__isnull=True, is_current_version=True)
        self.assertEqual(current.error_example, "Hairline or through crack")
        # The API versions a content edit; so does the import.
        self.assertEqual(current.version, 2)
        self.assertEqual(current.previous_version_id, self.general.id)
        # The injector's entry of the same name is untouched.
        specific = QualityErrorsList.objects.get(pk=self.specific.pk)
        self.assertTrue(specific.is_current_version)
        self.assertEqual(specific.error_example, "Crack at the nozzle seat")

    def test_a_row_is_matched_on_name_and_part_type(self):
        from Tracker.models import QualityErrorsList
        body = self.import_csv(
            "error_name,part_type,error_example\nCrack,Injector,Crack across the seat\n",
            mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = QualityErrorsList.objects.get(
            error_name="Crack", part_type=self.injector, is_current_version=True)
        self.assertEqual(current.error_example, "Crack across the seat")
        self.assertTrue(QualityErrorsList.objects.get(pk=self.general.pk).is_current_version)

    def test_a_part_type_that_names_nothing_is_refused(self):
        body = self.import_csv(
            "error_name,error_example,part_type\nDent,A dent,Nobody Pump\n", mode="create")
        self.assert_row_errors(body, mentions="Nobody Pump")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import QualityErrorsList
        self.assert_round_trips(QualityErrorsList)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import QualityErrorsList
        self.assert_round_trips(QualityErrorsList, fmt="csv")


class MeasurementDefinitionImportExportTests(ImportExportTestCase):
    endpoint = "MeasurementDefinitions"
    tenant_slug = "io-measdef"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Equipments, MeasurementDefinition, PartTypes
        pt = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
        # "Drill" is in both processes: only `Process > Step` says which.
        cls.steps = _process_steps(cls.tenant, pt, ("Pump Build", "Pump Repair"),
                                   ("Drill", "Tap"))
        cls.bore_gauge = Equipments.objects.create(
            tenant=cls.tenant, name="Bore gauge", serial_number="SN-100")
        cls.caliper = Equipments.objects.create(
            tenant=cls.tenant, name="Caliper", serial_number="SN-200")
        cls.bore = MeasurementDefinition.objects.create(
            tenant=cls.tenant, step=cls.steps[("Pump Build", "Drill")], label="Bore",
            type="NUMERIC", unit="mm", nominal="10.5", upper_tol="0.02", lower_tol="0.01",
            characteristic_number="7", default_equipment=cls.bore_gauge,
            backup_equipment=cls.caliper)
        MeasurementDefinition.objects.create(
            tenant=cls.tenant, step=cls.steps[("Pump Repair", "Drill")], label="Bore",
            type="PASS_FAIL", required=False)

    def test_a_typed_csv_creates_measurements(self):
        from Tracker.models import MeasurementDefinition
        body = self.import_csv(
            "step,label,type,unit,nominal,upper_tol,lower_tol,default_equipment,backup_equipment\n"
            "Pump Build > Tap,Thread depth,NUMERIC,mm,12.5,0.1,0.1,SN-100,Caliper\n",
            mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        m = MeasurementDefinition.objects.get(label="Thread depth")
        self.assertEqual(m.step_id, self.steps[("Pump Build", "Tap")].id)
        self.assertEqual(m.default_equipment_id, self.bore_gauge.id)
        self.assertEqual(m.backup_equipment_id, self.caliper.id)

    def test_a_row_is_matched_on_its_step_and_label(self):
        from Tracker.models import MeasurementDefinition
        body = self.import_csv("step,label,unit\nPump Build > Drill,Bore,in\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = MeasurementDefinition.objects.get(
            step=self.steps[("Pump Build", "Drill")], label="Bore", is_current_version=True)
        self.assertEqual(current.unit, "in")
        self.assertEqual(current.version, 2)
        self.assertEqual(current.default_equipment_id, self.bore_gauge.id)
        # The same label at the other process's Drill is a different measurement.
        other = MeasurementDefinition.objects.get(step=self.steps[("Pump Repair", "Drill")])
        self.assertEqual(other.unit, "")

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv("step,label,type\nDrill,Depth,NUMERIC\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_equipment_that_names_nothing_is_refused(self):
        body = self.import_csv(
            "step,label,type,default_equipment\nPump Build > Tap,Pitch,NUMERIC,SN-999\n",
            mode="create")
        self.assert_row_errors(body, mentions="SN-999")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import MeasurementDefinition
        self.assert_round_trips(MeasurementDefinition)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import MeasurementDefinition
        self.assert_round_trips(MeasurementDefinition, fmt="csv")


class PartTypeLifeLimitImportExportTests(ImportExportTestCase):
    endpoint = "PartTypeLifeLimits"
    tenant_slug = "io-ptlifelimit"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import LifeLimitDefinition, PartTypeLifeLimit, PartTypes
        cls.injector = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
        cls.pump = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
        cls.cycles_v1 = LifeLimitDefinition.objects.create(
            tenant=cls.tenant, name="Flight Cycles", unit="cycles", unit_label="Cycles",
            hard_limit="20000")
        PartTypeLifeLimit.objects.create(
            tenant=cls.tenant, part_type=cls.injector, definition=cls.cycles_v1)
        # Revising the definition copies the link onto v2 and leaves the original pinned
        # to v1 — so the export lists both, with the same part type and definition name.
        cls.cycles = cls.cycles_v1.create_new_version(
            user=cls.user, change_description="Raise the limit", hard_limit="25000")
        cls.shelf = LifeLimitDefinition.objects.create(
            tenant=cls.tenant, name="Shelf Life", unit="days", unit_label="Days",
            is_calendar_based=True, hard_limit="365")

    def test_a_typed_csv_creates_links_to_the_current_definition(self):
        from Tracker.models import PartTypeLifeLimit
        body = self.import_csv(
            "part_type,definition,is_required\nPump,Flight Cycles,no\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        link = PartTypeLifeLimit.objects.get(part_type=self.pump)
        self.assertEqual(link.definition_id, self.cycles.id)
        self.assertFalse(link.is_required)

    def test_a_row_is_matched_on_part_type_and_definition(self):
        from Tracker.models import PartTypeLifeLimit
        body = self.import_csv(
            "part_type,definition,is_required\nInjector,Flight Cycles,no\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        # The current definition's link, not the one pinned to v1.
        self.assertFalse(PartTypeLifeLimit.objects.get(definition=self.cycles).is_required)
        self.assertTrue(PartTypeLifeLimit.objects.get(definition=self.cycles_v1).is_required)

    def test_a_definition_that_names_nothing_is_refused(self):
        body = self.import_csv("part_type,definition\nPump,Operating Hours\n", mode="create")
        self.assert_row_errors(body, mentions="Operating Hours")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import PartTypeLifeLimit
        self.assert_round_trips(PartTypeLifeLimit)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import PartTypeLifeLimit
        self.assert_round_trips(PartTypeLifeLimit, fmt="csv")


class ExternalContactImportExportTests(ImportExportTestCase):
    endpoint = "notifications/external-contacts"
    tenant_slug = "io-extcontact"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Companies, ExternalContact
        cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
        cls.globex = Companies.objects.create(tenant=cls.tenant, name="Globex")
        # One person, a contact at two customers: only the customer says which row.
        ExternalContact.objects.create(tenant=cls.tenant, customer=cls.acme, name="Jane Roe",
                                       email="jane@example.com", role="quality")
        ExternalContact.objects.create(tenant=cls.tenant, customer=cls.globex, name="Jane Roe",
                                       email="jane@example.com", role="primary", enabled=False)

    def test_a_typed_csv_creates_contacts(self):
        from Tracker.models import ExternalContact
        body = self.import_csv(
            "customer,name,email,role\nAcme,Bob Smith,bob@acme.example,procurement\n",
            mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        c = ExternalContact.objects.get(email="bob@acme.example")
        self.assertEqual(c.customer_id, self.acme.id)
        self.assertTrue(c.enabled)

    def test_a_row_is_matched_on_customer_and_email(self):
        from Tracker.models import ExternalContact
        body = self.import_csv("customer,email,role\nGlobex,JANE@example.com,procurement\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(ExternalContact.objects.get(customer=self.globex).role, "procurement")
        self.assertEqual(ExternalContact.objects.get(customer=self.acme).role, "quality")

    def test_a_customer_that_names_nothing_is_refused(self):
        body = self.import_csv("customer,name,email\nInitech,Pat,pat@initech.example\n",
                               mode="create")
        self.assert_row_errors(body, mentions="Initech")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import ExternalContact
        self.assert_round_trips(ExternalContact)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import ExternalContact
        self.assert_round_trips(ExternalContact, fmt="csv")


class RepairCodeImportExportTests(ImportExportTestCase):
    endpoint = "RepairCodes"
    tenant_slug = "io-repaircode"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import PartTypes, RepairCode
        cls.nozzle = PartTypes.objects.create(tenant=cls.tenant, name="Nozzle")
        # "Hone" is in both processes: only `Process > Step` says which.
        cls.steps = _process_steps(cls.tenant, cls.nozzle,
                                   ("Injector Rebuild", "Pump Rebuild"), ("Clean", "Hone"))
        cls.recon = RepairCode.objects.create(
            tenant=cls.tenant, code="NZL-RECON", name="Recondition nozzle",
            component_type=cls.nozzle, trigger="RECONDITION", notes="Per SOP 12")
        cls.recon.steps.set([cls.steps[("Injector Rebuild", "Hone")],
                             cls.steps[("Pump Rebuild", "Clean")]])
        RepairCode.objects.create(tenant=cls.tenant, code="FINAL", name="Final test",
                                  trigger="ALWAYS")

    def test_a_typed_csv_creates_repair_codes(self):
        from Tracker.models import RepairCode
        body = self.import_csv(
            'code,name,component_type,trigger,steps\n'
            'NZL-RPL,Replace nozzle,Nozzle,REPLACE_BUY,"Injector Rebuild > Clean; Pump Rebuild > Hone"\n',
            mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        rc = RepairCode.objects.get(code="NZL-RPL")
        self.assertEqual(rc.component_type_id, self.nozzle.id)
        self.assertEqual(set(rc.steps.values_list("id", flat=True)),
                         {self.steps[("Injector Rebuild", "Clean")].id,
                          self.steps[("Pump Rebuild", "Hone")].id})

    def test_an_edit_matched_on_its_code_versions_and_keeps_its_steps(self):
        from Tracker.models import RepairCode
        body = self.import_csv("code,name\nNZL-RECON,Recondition nozzle tip\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = RepairCode.objects.get(code="NZL-RECON", is_current_version=True)
        self.assertEqual(current.name, "Recondition nozzle tip")
        self.assertEqual(current.version, 2)
        # create_new_version copies scalar fields only; the import carries the set over.
        self.assertEqual(set(current.steps.values_list("id", flat=True)),
                         set(self.recon.steps.values_list("id", flat=True)))

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv("code,name,steps\nHONE,Hone only,Hone\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_a_component_type_that_names_nothing_is_refused(self):
        body = self.import_csv("code,name,component_type\nX-1,Mystery,Nobody Part\n",
                               mode="create")
        self.assert_row_errors(body, mentions="Nobody Part")

    def test_the_export_writes_the_steps_as_it_reads_them(self):
        csv_text = self.export("csv").decode("utf-8-sig")
        self.assertIn("Injector Rebuild > Hone; Pump Rebuild > Clean", csv_text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import RepairCode
        self.assert_round_trips(RepairCode)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import RepairCode
        self.assert_round_trips(RepairCode, fmt="csv")
