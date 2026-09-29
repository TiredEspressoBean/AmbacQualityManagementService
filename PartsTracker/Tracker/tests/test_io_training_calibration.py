"""Import/export for JobRole, TrainingType, TrainingRequirement and CalibrationRecord.

TrainingType is versioned: an import edits it the way its API does, by forking a new
version. TrainingRequirement is found by its training type + target. CalibrationRecord
is evidence, so an import adds records and never changes one. See io_base.py.
"""
from Tracker.tests.io_base import ImportExportTestCase


class JobRoleImportExportTests(ImportExportTestCase):
    endpoint = "JobRoles"
    tenant_slug = "io-jobrole"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import JobRole
        JobRole.objects.create(tenant=cls.tenant, name="Machinist", description="CNC")
        JobRole.objects.create(tenant=cls.tenant, name="Retired role", active=False)

    def test_a_typed_csv_creates_job_roles(self):
        from Tracker.models import JobRole
        body = self.import_csv("name,description,active\nCMM Inspector,Runs the CMM,yes\n",
                               mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertTrue(JobRole.objects.get(name="CMM Inspector").active)

    def test_a_row_is_matched_on_its_name(self):
        from Tracker.models import JobRole
        body = self.import_csv("name,description\nmachinist,Mill and lathe\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(JobRole.objects.get(name="Machinist").description, "Mill and lathe")

    def test_a_name_two_roles_share_is_refused(self):
        from Tracker.models import JobRole
        JobRole.objects.create(tenant=self.tenant, name="Machinist")
        body = self.import_csv("name,description\nMachinist,Which one?\n", mode="update")
        self.assert_row_errors(body, mentions="matches more than one")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import JobRole
        self.assert_round_trips(JobRole)


class TrainingTypeImportExportTests(ImportExportTestCase):
    endpoint = "TrainingTypes"
    tenant_slug = "io-trainingtype"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import TrainingType
        TrainingType.objects.create(tenant=cls.tenant, name="Blueprint Reading",
                                    validity_period_days=365)
        # A type with history: the list (and so the export) shows every version.
        v1 = TrainingType.objects.create(tenant=cls.tenant, name="CMM Operation",
                                         description="Zeiss")
        v1.create_new_version(user=cls.user, description="Zeiss and Hexagon")

    def test_a_typed_csv_creates_training_types(self):
        from Tracker.models import TrainingType
        body = self.import_csv("name,description,validity_period_days\n"
                               "Soldering IPC-A-610,Class 3,730\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(TrainingType.objects.get(name="Soldering IPC-A-610")
                         .validity_period_days, 730)

    def test_an_update_by_name_forks_a_new_version_as_the_api_does(self):
        from Tracker.models import TrainingType
        body = self.import_csv("name,validity_period_days\nBlueprint Reading,180\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        rows = TrainingType.objects.filter(name="Blueprint Reading")
        self.assertEqual(rows.count(), 2)
        self.assertEqual(rows.get(is_current_version=True).validity_period_days, 180)
        self.assertEqual(rows.get(is_current_version=False).validity_period_days, 365)

    def test_a_name_matches_the_current_version(self):
        from Tracker.models import TrainingType
        body = self.import_csv("name,validity_period_days\nCMM Operation,90\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = TrainingType.objects.get(name="CMM Operation", is_current_version=True)
        self.assertEqual(current.description, "Zeiss and Hexagon")
        self.assertEqual(current.validity_period_days, 90)

    def test_a_name_two_types_share_is_refused(self):
        from Tracker.models import TrainingType
        TrainingType.objects.create(tenant=self.tenant, name="Blueprint Reading")
        body = self.import_csv("name,description\nBlueprint Reading,Which one?\n",
                               mode="update")
        self.assert_row_errors(body, mentions="matches more than one")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import TrainingType
        self.assert_round_trips(TrainingType)


class TrainingRequirementImportExportTests(ImportExportTestCase):
    endpoint = "TrainingRequirements"
    tenant_slug = "io-trainingreq"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import (
            EquipmentType, JobRole, PartTypes, Processes, ProcessStep, Steps,
            TrainingRequirement, TrainingType,
        )
        pt = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
        cls.steps, cls.processes = {}, {}
        # "Drill" is in both processes: only `Process > Step` says which.
        for pname in ("Pump Build", "Pump Repair"):
            proc = Processes.objects.create(tenant=cls.tenant, name=pname, part_type=pt,
                                            status="APPROVED")
            cls.processes[pname] = proc
            for i, sname in enumerate(("Drill", "Tap"), start=1):
                st = Steps.objects.create(tenant=cls.tenant, part_type=pt, name=sname)
                ProcessStep.objects.create(process=proc, step=st, order=i)
                cls.steps[(pname, sname)] = st
        cls.blueprint = TrainingType.objects.create(tenant=cls.tenant, name="Blueprint Reading")
        cls.cmm = TrainingType.objects.create(tenant=cls.tenant, name="CMM Operation")
        cls.cmm_type = EquipmentType.objects.create(tenant=cls.tenant, name="CMM")
        cls.machinist = JobRole.objects.create(tenant=cls.tenant, name="Machinist")
        # One requirement per kind of target, so the round trip covers every FK.
        TrainingRequirement.objects.create(tenant=cls.tenant, training_type=cls.blueprint,
                                           step=cls.steps[("Pump Build", "Drill")], min_level=2)
        TrainingRequirement.objects.create(tenant=cls.tenant, training_type=cls.blueprint,
                                           process=cls.processes["Pump Repair"])
        TrainingRequirement.objects.create(tenant=cls.tenant, training_type=cls.cmm,
                                           equipment_type=cls.cmm_type, notes="Per WI-042")
        TrainingRequirement.objects.create(tenant=cls.tenant, training_type=cls.cmm,
                                           job_role=cls.machinist, min_level=4)

    def test_a_typed_csv_creates_requirements(self):
        from Tracker.models import TrainingRequirement
        body = self.import_csv(
            "training_type,step,process,job_role,min_level\n"
            "CMM Operation,Pump Repair > Drill,,,2\n"
            "Blueprint Reading,,,Machinist,3\n", mode="create")
        self.assertEqual(body["summary"]["created"], 2, body)
        req = TrainingRequirement.objects.get(training_type=self.cmm,
                                              step=self.steps[("Pump Repair", "Drill")])
        self.assertEqual(req.min_level, 2)
        self.assertTrue(TrainingRequirement.objects.filter(
            training_type=self.blueprint, job_role=self.machinist).exists())

    def test_a_row_is_matched_on_its_training_type_and_target(self):
        from Tracker.models import TrainingRequirement
        body = self.import_csv(
            "training_type,step,min_level\nBlueprint Reading,Pump Build > Drill,3\n",
            mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(TrainingRequirement.objects.get(
            training_type=self.blueprint, step=self.steps[("Pump Build", "Drill")]).min_level, 3)
        body = self.import_csv("training_type,job_role,notes\nCMM Operation,Machinist,Lead\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(TrainingRequirement.objects.get(
            training_type=self.cmm, job_role=self.machinist).notes, "Lead")
        self.assertEqual(TrainingRequirement.objects.count(), 4)

    def test_the_same_type_and_target_in_create_mode_is_refused(self):
        body = self.import_csv("training_type,process\nBlueprint Reading,Pump Repair\n",
                               mode="create")
        self.assert_row_errors(body, mentions="already exists")

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv("training_type,step\nCMM Operation,Drill\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_a_training_type_that_names_nothing_is_refused(self):
        body = self.import_csv("training_type,job_role\nUnderwater Welding,Machinist\n",
                               mode="create")
        self.assert_row_errors(body, mentions="Underwater Welding")

    def test_the_export_writes_steps_with_their_process(self):
        csv_text = self.export("csv").decode("utf-8-sig")
        self.assertIn("Pump Build > Drill", csv_text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import TrainingRequirement
        self.assert_round_trips(TrainingRequirement)


class CalibrationRecordImportExportTests(ImportExportTestCase):
    endpoint = "CalibrationRecords"
    tenant_slug = "io-calibration"

    @classmethod
    def build_fixtures(cls):
        import datetime
        from Tracker.models import CalibrationRecord, EquipmentType, Equipments
        gauge = EquipmentType.objects.create(tenant=cls.tenant, name="Micrometer")
        cls.mic = Equipments.objects.create(tenant=cls.tenant, name="Mic 0-1in",
                                            serial_number="SN-100", equipment_type=gauge)
        cls.record = CalibrationRecord.objects.create(
            tenant=cls.tenant, equipment=cls.mic,
            calibration_date=datetime.date(2026, 1, 15), due_date=datetime.date(2027, 1, 15),
            result="PASS", calibration_type="SCHEDULED", performed_by="J. Smith",
            external_lab="Acme Cal", certificate_number="C-1",
            standards_used="NIST gauge blocks", as_found_in_tolerance=True,
            adjustments_made=False, notes="Routine")

    def test_a_typed_csv_adds_records(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv(
            "equipment,calibration_date,due_date,result,certificate_number\n"
            "SN-100,2026-07-15,2027-07-15,PASS,C-2\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(CalibrationRecord.objects.get(certificate_number="C-2").equipment_id,
                         self.mic.id)

    def test_the_same_calibration_again_is_refused_not_a_second_record(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv(
            "equipment,calibration_date,due_date,certificate_number\n"
            "SN-100,1/15/2026,2027-01-15,C-1\n", mode="create")
        self.assert_row_errors(body, mentions="already exists")
        self.assertEqual(CalibrationRecord.objects.count(), 1)

    def test_a_changed_value_on_update_is_refused(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv(f"id,notes\n{self.record.id},Rewritten\n", mode="update")
        self.assert_row_errors(body, mentions="are records")
        self.assertEqual(CalibrationRecord.objects.get(pk=self.record.pk).notes, "Routine")

    def test_a_changed_value_matched_on_the_calibration_is_refused(self):
        from Tracker.models import CalibrationRecord
        body = self.import_csv(
            "equipment,calibration_date,certificate_number,result\nSN-100,2026-01-15,C-1,FAIL\n",
            mode="upsert")
        self.assert_row_errors(body, mentions="are records")
        self.assertEqual(CalibrationRecord.objects.get(pk=self.record.pk).result, "PASS")

    def test_an_equipment_that_names_nothing_is_refused(self):
        body = self.import_csv(
            "equipment,calibration_date,due_date\nSN-999,2026-02-01,2027-02-01\n",
            mode="create")
        self.assert_row_errors(body, mentions="SN-999")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import CalibrationRecord
        self.assert_round_trips(CalibrationRecord)
