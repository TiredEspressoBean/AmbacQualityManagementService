"""
User and company seed data generation.
"""

import random
from django.contrib.auth.models import Group

from Tracker.models import Companies, User
from .base import BaseSeeder


class UserSeeder(BaseSeeder):
    """
    Seeds companies, users, and role assignments.

    Creates:
    - Companies (AMBAC + customer companies)
    - Internal employees (managers, QA, operators, doc controller)
    - External portal users (customers)
    - Group/role assignments
    """

    def seed(self):
        """Run the full user seeding process."""
        self.verify_groups_exist()
        companies = self.create_companies()
        users = self.create_users(companies)
        self.setup_user_activity_weights(users)
        admin = self.create_admin_user(companies[0])
        return {'companies': companies, 'users': users, 'admin': admin}

    def create_companies(self):
        """Create realistic diesel industry companies."""
        company_data = [
            # Internal Company (AMBAC) - always first
            ("AMBAC Manufacturing", "Diesel fuel injector remanufacturing company", "Internal"),

            # Customer Companies - OEMs
            ("Cummins Engine Company", "Diesel engine manufacturer", "OEM"),
            ("Caterpillar Inc.", "Heavy machinery and engines", "OEM"),
            ("Volvo Group Trucks", "Commercial vehicle manufacturer", "OEM"),
            ("Detroit Diesel Corporation", "Heavy-duty diesel engines", "OEM"),
            ("Navistar International", "Commercial trucks and engines", "OEM"),

            # Customer Companies - Fleets
            ("TransAmerica Logistics", "Long-haul trucking company", "Fleet"),
            ("Metro Transit Services", "Public transportation authority", "Fleet"),
            ("Construction Solutions LLC", "Heavy equipment contractor", "Fleet"),
            ("Agricultural Services Co.", "Farm equipment services", "Fleet"),
            ("Marine Transport Inc.", "Commercial marine vessels", "Fleet"),
        ]

        # Scale the number of companies
        company_limit = {
            'small': 5,
            'medium': 8,
            'large': 11,
        }.get(self.scale, 8)

        companies = []
        for name, desc, company_type in company_data[:company_limit]:
            company = Companies.objects.create(
                tenant=self.tenant,
                name=name,
                description=f"{desc} - {company_type}",
                hubspot_api_id=f"HS_{company_type}_{len(companies):03d}"
            )
            companies.append(company)

        self.log(f"Created {len(companies)} companies (including AMBAC)")
        return companies

    def create_users(self, companies):
        """Create realistic users with proper roles and company associations."""
        users = {'customers': [], 'employees': [], 'managers': [], 'qa_staff': []}

        ambac_company = companies[0]  # AMBAC Manufacturing - always first
        config = self.config

        # Get groups
        customer_group = Group.objects.get(name='Customer')
        production_manager_group = Group.objects.get(name='Production_Manager')
        production_operator_group = Group.objects.get(name='Production_Operator')
        qa_manager_group = Group.objects.get(name='QA_Manager')
        qa_inspector_group = Group.objects.get(name='QA_Inspector')
        document_controller_group = Group.objects.get(name='Document_Controller')

        # Create customers from external companies (portal users)
        for i in range(config['customers']):
            company = random.choice(companies[1:])  # Skip AMBAC
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            company_domain = company.name.lower().replace(' ', '').replace('.', '').replace(',', '')[:15] + '.com'

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.PORTAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}@{company_domain}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@{company_domain}",
                parent_company=company,
                is_active=True
            )
            self.assign_user_to_group(user, customer_group)
            users['customers'].append(user)

        # Production Managers (about 10% of employees)
        manager_count = max(2, config['employees'] // 10)
        for i in range(manager_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_staff=True,
                is_active=True
            )
            self.assign_user_to_group(user, production_manager_group)
            users['managers'].append(user)

        # QA Staff (about 15% of employees)
        qa_count = max(2, config['employees'] // 7)
        for i in range(qa_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}.qa",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}.qa@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_staff=True,
                is_active=True
            )
            # First QA person is manager, rest are inspectors
            if i == 0:
                self.assign_user_to_group(user, qa_manager_group)
            else:
                self.assign_user_to_group(user, qa_inspector_group)
            users['qa_staff'].append(user)

        # Document Controller (1 person)
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        doc_controller = User.objects.create_user(
            tenant=self.tenant,
            user_type=User.UserType.INTERNAL,
            first_name=first_name,
            last_name=last_name,
            username=f"{first_name.lower()}.{last_name.lower()}.doc",
            password="password123",
            email=f"{first_name.lower()}.{last_name.lower()}.doc@ambacmanufacturing.com",
            parent_company=ambac_company,
            is_staff=True,
            is_active=True
        )
        self.assign_user_to_group(doc_controller, document_controller_group)
        users['doc_controller'] = doc_controller

        # Production Operators (remaining employees)
        operator_count = config['employees'] - manager_count - qa_count - 1
        for i in range(max(1, operator_count)):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}.op{i}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}.op@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_active=True
            )
            self.assign_user_to_group(user, production_operator_group)
            users['employees'].append(user)

        # Include managers and QA staff in employees list for general use
        users['employees'].extend(users['managers'])
        users['employees'].extend(users['qa_staff'])
        users['employees'].append(doc_controller)

        self.log(
            f"Created {len(users['customers'])} customers, "
            f"{len(users['managers'])} managers, "
            f"{len(users['qa_staff'])} QA staff, "
            f"{operator_count} operators"
        )
        return users

    def create_admin_user(self, ambac_company):
        """Create or update the admin user for demos."""
        admin_group = Group.objects.get(name='Admin')

        # Look up by email to match user created by setup_tenant
        admin, created = User.objects.update_or_create(
            email='admin@ambacmanufacturing.com',
            defaults={
                'tenant': self.tenant,
                'user_type': User.UserType.INTERNAL,
                'username': 'admin@ambacmanufacturing.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'parent_company': ambac_company,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'us_person': True,  # Required for ITAR compliance
                'citizenship': 'US',
            }
        )
        if created:
            admin.set_password('admin')
            admin.save()

        self.assign_user_to_group(admin, admin_group)

        if created:
            self.log("Created admin user (admin/admin)", success=True)
        else:
            self.log("Updated existing admin user")

        return admin
