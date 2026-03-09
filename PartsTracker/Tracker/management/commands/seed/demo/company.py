"""
Demo company seeder with preset, deterministic companies.

Creates the exact companies specified in DEMO_DATA_SYSTEM.md:
    - AMBAC Manufacturing (internal company)
    - Midwest Fleet Services (main demo customer - in-progress order)
    - Great Lakes Diesel (completed order that triggered CAPA)
    - Northern Trucking Co (pending order)
"""

from Tracker.models import Companies

from ..base import BaseSeeder


# Preset demo companies from DEMO_DATA_SYSTEM.md
# Note: Companies model has: name, description, hubspot_api_id
DEMO_COMPANIES = [
    {
        'name': 'AMBAC Manufacturing',
        'is_internal': True,
        'description': 'Internal company - diesel fuel injector remanufacturer. Contact: info@ambacmanufacturing.com',
    },
    {
        'name': 'Midwest Fleet Services',
        'is_internal': False,
        'description': 'Fleet management company - main demo customer. Contact: Tom Bradley, orders@midwestfleet.com',
    },
    {
        'name': 'Great Lakes Diesel',
        'is_internal': False,
        'description': 'Diesel parts supplier - completed order that triggered CAPA-2024-003. Contact: Robert Martinez',
    },
    {
        'name': 'Northern Trucking Co',
        'is_internal': False,
        'description': 'Trucking company - pending order shows intake process. Contact: Linda Thompson',
    },
]


class DemoCompanySeeder(BaseSeeder):
    """
    Creates preset demo companies for the demo scenario.

    Companies are linked to specific demo narratives:
    - Midwest Fleet: In-progress order with active work
    - Great Lakes: Completed order that triggered quality investigation
    - Northern Trucking: New order showing intake process
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self):
        """
        Create all demo companies.

        Returns:
            dict with companies organized by name and type
        """
        self.log("Creating demo companies...")

        result = {
            'internal': None,
            'customers': [],
            'by_name': {},
        }

        for company_data in DEMO_COMPANIES:
            company = self._create_company(company_data)
            result['by_name'][company.name] = company

            if company_data['is_internal']:
                result['internal'] = company
            else:
                result['customers'].append(company)

        self.log(f"  Created {len(DEMO_COMPANIES)} demo companies")
        return result

    def _create_company(self, company_data):
        """Create a single demo company."""
        company, created = Companies.objects.update_or_create(
            tenant=self.tenant,
            name=company_data['name'],
            defaults={
                'description': company_data.get('description', ''),
            }
        )

        action = "Created" if created else "Updated"
        company_type = "internal" if company_data['is_internal'] else "customer"
        if self.verbose:
            self.log(f"    {action}: {company.name} ({company_type})")

        return company

    @property
    def verbose(self):
        """Check if verbose output is enabled."""
        return getattr(self, '_verbose', False)

    @verbose.setter
    def verbose(self, value):
        self._verbose = value
