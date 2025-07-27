from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from Tracker.models import (
    Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents,
    Equipments, EquipmentType, QualityErrorsList, QualityReports,
    EquipmentUsage, ArchiveReason, StepTransitionLog, WorkOrder, SamplingRuleSet, SamplingRule
)
import random
from faker import Faker
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = "Generate realistic test data for diesel fuel injector manufacturing"

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Create user groups
        employees_group, _ = Group.objects.get_or_create(name='employee')
        customers_group, _ = Group.objects.get_or_create(name='customer')
        managers_group, _ = Group.objects.get_or_create(name='manager')

        # Create companies
        companies = [
            Companies.objects.create(
                name=f"{fake.company()} Diesel Systems",
                description=fake.catch_phrase(),
                hubspot_api_id=f"HS_COMP_{i}"
            ) for i in range(3)
        ]

        # Create users
        employees, customers, managers = [], [], []
        for _ in range(3):
            emp = User.objects.create_user(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=fake.unique.user_name(),
                password="password",
                email=fake.company_email(),
                parent_company=random.choice(companies)
            )
            emp.groups.add(employees_group)
            employees.append(emp)

            cust = User.objects.create_user(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=fake.unique.user_name(),
                password="password",
                email=fake.email(),
                parent_company=random.choice(companies)
            )
            cust.groups.add(customers_group)
            customers.append(cust)

            mgr = User.objects.create_user(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=fake.unique.user_name(),
                password="password",
                email=fake.company_email(),
                parent_company=random.choice(companies)
            )
            mgr.groups.add(managers_group)
            managers.append(mgr)

        # Create equipment types and equipment
        eq_types = [EquipmentType.objects.create(name=et) for et in ["Assembly Rig", "Test Bench", "Seal Station"]]
        equipment_list = [
            Equipments.objects.create(
                name=f"EQ-{fake.random_int(100, 999)}",
                equipment_type=random.choice(eq_types)
            ) for _ in range(5)
        ]

        # Create part types, processes, steps
        part_types = []
        for _ in range(3):
            pt = PartTypes.objects.create(name=fake.word().capitalize() + " Injector", ID_prefix="DI")
            part_types.append(pt)

            for _ in range(2):
                proc = Processes.objects.create(
                    name=fake.word().capitalize(),
                    is_remanufactured=random.choice([True, False]),
                    part_type=pt,
                    num_steps=random.randint(5, 10),
                )
                proc.generate_steps()



        # Create orders
        orders = [
            Orders.objects.create(
                name=f"Batch-{fake.word().capitalize()}",
                customer=random.choice(customers),
                company=random.choice(companies),
                estimated_completion=timezone.now().date() + timedelta(days=random.randint(2, 10)),
                order_status=random.choice([s[0] for s in Orders.Status.choices]),
                archived=False
            ) for _ in range(5)
        ]

        # Create archived orders and parts
        for reason_key, note in [("completed", "Order fulfilled."), ("user_error", "Input error."), ("obsolete", "Obsolete model.")]:
            order = Orders.objects.create(
                name=f"Archived-{fake.word().capitalize()}",
                customer=random.choice(customers),
                company=random.choice(companies),
                estimated_completion=timezone.now().date() - timedelta(days=random.randint(5, 20)),
                order_status=Orders.Status.CANCELLED,
                archived=True
            )
            ArchiveReason.objects.create(
                reason=reason_key,
                notes=note,
                content_object=order,
                user=random.choice(employees)
            )
            pt = random.choice(part_types)
            process = pt.processes.first()
            if not process:
                continue
            step = process.steps.order_by('step').first()
            part = Parts.objects.create(
                ERP_id=fake.uuid4().split('-')[0].upper(),
                part_type=pt,
                step=step,
                order=order,
                part_status=Parts.Status.CANCELLED,
                archived=True
            )
            ArchiveReason.objects.create(
                reason=reason_key,
                notes=f"Part archived with order: {note}",
                content_object=part,
                user=random.choice(employees)
            )

        # Create work orders, parts, docs, quality reports, logs
        for _ in range(10):
            pt = random.choice(part_types)
            order = random.choice(orders)
            process = pt.processes.first()
            if not process:
                continue
            step = process.steps.order_by('step').first()

            # Work order
            wo = WorkOrder.objects.create(
                ERP_id=fake.uuid4().split('-')[0].upper(),
                operator=random.choice(employees),
                related_order=order,
                expected_completion=timezone.now().date() + timedelta(days=5)
            )

            # Sampling rule set with get_or_create to avoid IntegrityError
            srs, _ = SamplingRuleSet.objects.get_or_create(
                part_type=pt,
                process=process,
                step=step,
                version=1,
                defaults={
                    "name": "RuleSet A",
                    "origin": "auto_test",
                    "active": True,
                    "created_by": random.choice(employees),
                    "modified_by": random.choice(employees),
                }
            )

            rule = SamplingRule.objects.create(
                ruleset=srs,
                rule_type=random.choice(SamplingRule.RuleType),
                value=random.randint(1,20),
                created_by=random.choice(employees),
                modified_by=random.choice(employees)
            )

            # Part
            part = Parts.objects.create(
                ERP_id=fake.uuid4().split('-')[0].upper(),
                part_type=pt,
                step=step,
                order=order,
                part_status=random.choice([s[0] for s in Parts.Status.choices]),
                archived=False,
                work_order=wo,
                requires_sampling=True,
                sampling_rule=rule
            )

            # Document linked to part
            Documents.objects.create(
                is_image=random.choice([True, False]),
                file_name="example.txt",
                file=ContentFile(b"Sample file content.", name="example.txt"),
                uploaded_by=random.choice(employees),
                content_type=ContentType.objects.get_for_model(part),
                object_id=part.id
            )

            # Equipment usage
            EquipmentUsage.objects.create(
                equipment=random.choice(equipment_list),
                step=step,
                part=part,
                operator=random.choice(employees),
                notes="Routine usage"
            )

            # Quality error list
            errors = [QualityErrorsList.objects.create(
                error_name=fake.catch_phrase(),
                error_example=fake.sentence(),
                part_type=pt
            ) for _ in range(2)]

            # Quality report
            qr = QualityReports.objects.create(
                part=part,
                machine=random.choice(equipment_list),
                description=fake.text(max_nb_chars=300),
                sampling_method="manual",
                status=random.choice(["PASS", "FAIL"]),
            )
            qr.operator.add(random.choice(employees))
            qr.errors.set(errors)

            # Step transition logs
            for s in process.steps.all():
                StepTransitionLog.objects.create(
                    step=s,
                    part=part,
                    operator=random.choice(employees),
                    timestamp=timezone.now() - timedelta(hours=random.randint(1, 72))
                )

        # Admin
        if not User.objects.filter(email="admin@example.com").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="password",
                first_name="John",
                last_name="Doe"
            )
            self.stdout.write(self.style.SUCCESS("✅ Admin user created: admin@example.com / password"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Admin user already exists."))

        self.stdout.write(self.style.SUCCESS("✅ Fully populated test data with sampling, documents, equipment, and processes."))
