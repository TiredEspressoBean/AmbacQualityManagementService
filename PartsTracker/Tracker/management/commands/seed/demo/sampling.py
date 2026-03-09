"""
Demo sampling seeder with preset sampling rules and rulesets.

Creates deterministic sampling configuration matching quality inspection needs:
- Standard Inspection ruleset (every 5th part)
- Enhanced Inspection ruleset (every 3rd part + first 5 parts)
- 100% Inspection ruleset (every part)
- Rules linked to appropriate inspection steps
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    SamplingRuleSet, SamplingRule, SamplingTriggerState,
    SamplingRuleType, Steps,
)

from ..base import BaseSeeder


# Demo sampling rulesets
# SamplingRuleSet model fields:
# - part_type: FK to PartTypes (required)
# - process: FK to Processes (optional)
# - step: FK to Steps (required)
# - name: CharField
# - origin: CharField (blank=True)
# - active: BooleanField (default=True)
# - supersedes: OneToOneField to self (optional)
# - fallback_ruleset: OneToOneField to self (optional)
# - fallback_threshold: PositiveIntegerField (optional)
# - fallback_duration: PositiveIntegerField (optional)
# - is_fallback: BooleanField (default=False)
# - created_by: FK to User (optional)
# - modified_by: FK to User (optional)
#
# SamplingRule model fields:
# - ruleset: FK to SamplingRuleSet (required)
# - rule_type: CharField with SamplingRuleType choices (UPPERCASE values)
# - value: PositiveIntegerField (optional)
# - order: PositiveIntegerField (default=0)
# - algorithm_description: TextField (default="SHA-256 hash modulo arithmetic")
# - last_validated: DateTimeField (optional)
# - created_by: FK to User (optional)
# - modified_by: FK to User (optional)
DEMO_SAMPLING_RULESETS = [
    # Standard inspection for Flow Testing
    {
        'id': 'flow-standard',
        'name': 'Standard Inspection - Flow Testing',
        'step': 'Flow Testing',
        'origin': 'QMS-SAMP-001 Rev A',
        'active': True,
        'is_fallback': False,
        'fallback_threshold': 3,  # Switch to enhanced after 3 consecutive failures
        'fallback_duration': 10,  # Need 10 good parts to revert
        'rules': [
            {
                'rule_type': 'EVERY_NTH_PART',  # UPPERCASE enum value
                'value': 5,  # Every 5th part
                'order': 1,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
        ],
    },
    # Enhanced inspection for Flow Testing (used as fallback)
    {
        'id': 'flow-enhanced',
        'name': 'Enhanced Inspection - Flow Testing',
        'step': 'Flow Testing',
        'origin': 'QMS-SAMP-002 Rev A',
        'active': True,
        'is_fallback': True,
        'fallback_threshold': None,
        'fallback_duration': None,
        'rules': [
            {
                'rule_type': 'FIRST_N_PARTS',  # UPPERCASE enum value
                'value': 5,  # First 5 parts of order
                'order': 1,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
            {
                'rule_type': 'EVERY_NTH_PART',  # UPPERCASE enum value
                'value': 3,  # Then every 3rd part
                'order': 2,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
        ],
    },
    # Standard inspection for Nozzle Inspection
    {
        'id': 'nozzle-standard',
        'name': 'Standard Inspection - Nozzle',
        'step': 'Nozzle Inspection',
        'origin': 'QMS-SAMP-003 Rev A',
        'active': True,
        'is_fallback': False,
        'fallback_threshold': 2,  # Switch to 100% after 2 consecutive failures
        'fallback_duration': 15,  # Need 15 good parts to revert
        'rules': [
            {
                'rule_type': 'EVERY_NTH_PART',  # UPPERCASE enum value
                'value': 4,  # Every 4th part
                'order': 1,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
        ],
    },
    # 100% inspection for Nozzle (used as fallback)
    {
        'id': 'nozzle-100pct',
        'name': '100% Inspection - Nozzle',
        'step': 'Nozzle Inspection',
        'origin': 'QMS-SAMP-004 Rev A',
        'active': True,
        'is_fallback': True,
        'fallback_threshold': None,
        'fallback_duration': None,
        'rules': [
            {
                'rule_type': 'EVERY_NTH_PART',  # UPPERCASE enum value
                'value': 1,  # Every part
                'order': 1,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
        ],
    },
    # Final test - combination of first/last and percentage
    {
        'id': 'final-standard',
        'name': 'Standard Inspection - Final Test',
        'step': 'Final Test',
        'origin': 'QMS-SAMP-005 Rev A',
        'active': True,
        'is_fallback': False,
        'fallback_threshold': None,
        'fallback_duration': None,
        'rules': [
            {
                'rule_type': 'FIRST_N_PARTS',  # UPPERCASE enum value
                'value': 3,  # First 3 parts
                'order': 1,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
            {
                'rule_type': 'LAST_N_PARTS',  # UPPERCASE enum value
                'value': 2,  # Last 2 parts
                'order': 2,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
            {
                'rule_type': 'PERCENTAGE',  # UPPERCASE enum value
                'value': 10,  # 10% of remaining parts
                'order': 3,
                'algorithm_description': 'SHA-256 hash modulo arithmetic',
                'last_validated': None,
            },
        ],
    },
]


class DemoSamplingSeeder(BaseSeeder):
    """
    Creates preset sampling rulesets and rules.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, part_types, process, users=None):
        """
        Create all demo sampling rulesets and rules.

        Args:
            part_types: list of PartTypes
            process: the Processes object to use
            users: optional dict with user lists for audit fields

        Returns:
            dict with created rulesets, rules
        """
        self.log("Creating demo sampling rulesets...")

        result = {
            'rulesets': [],
            'rules': [],
        }

        # Get part type (default to first one)
        part_type = part_types[0] if part_types else None
        if not part_type:
            self.log("  Warning: No part types available, skipping sampling rules", warning=True)
            return result

        # Get QA manager for audit fields
        qa_manager = None
        if users:
            qa_staff = users.get('qa_staff', [])
            qa_manager = qa_staff[0] if qa_staff else None

        # Get step lookup
        steps = Steps.objects.filter(tenant=self.tenant)
        step_map = {s.name: s for s in steps}

        # Create rulesets and rules
        ruleset_map = {}  # For linking fallbacks
        for rs_data in DEMO_SAMPLING_RULESETS:
            step = step_map.get(rs_data['step'])
            if not step:
                self.log(f"  Warning: Step '{rs_data['step']}' not found", warning=True)
                continue

            ruleset = self._create_ruleset(rs_data, part_type, process, step, qa_manager)
            result['rulesets'].append(ruleset)
            ruleset_map[rs_data['id']] = ruleset

            # Create rules for this ruleset
            for rule_data in rs_data.get('rules', []):
                rule = self._create_rule(rule_data, ruleset, qa_manager)
                result['rules'].append(rule)

        # Link fallback rulesets (second pass after all rulesets exist)
        self._link_fallbacks(ruleset_map)

        self.log(f"  Created {len(result['rulesets'])} sampling rulesets")
        self.log(f"  Created {len(result['rules'])} sampling rules")

        return result

    def _create_ruleset(self, rs_data, part_type, process, step, qa_manager=None):
        """Create a sampling ruleset.

        SamplingRuleSet model fields:
        - part_type: FK to PartTypes
        - process: FK to Processes (optional)
        - step: FK to Steps
        - name: CharField
        - origin: CharField
        - active: BooleanField
        - is_fallback: BooleanField
        - fallback_threshold: PositiveIntegerField (optional)
        - fallback_duration: PositiveIntegerField (optional)
        - supersedes: OneToOneField to self (optional)
        - fallback_ruleset: OneToOneField to self (optional, set in second pass)
        - created_by: FK to User (optional)
        - modified_by: FK to User (optional)
        """
        # Don't set fallback_ruleset here - will be set in second pass
        # Explicitly set ALL fields - do not rely on model defaults
        defaults = {
            'part_type': part_type,
            'process': process,
            'step': step,
            'origin': rs_data.get('origin', ''),
            'active': rs_data.get('active', True),
            'is_fallback': rs_data.get('is_fallback', False),
            'fallback_threshold': rs_data.get('fallback_threshold', None),
            'fallback_duration': rs_data.get('fallback_duration', None),
            'supersedes': None,
            'fallback_ruleset': None,
            'created_by': qa_manager,  # QA manager who created the ruleset
            'modified_by': qa_manager,
        }

        ruleset, _ = SamplingRuleSet.objects.update_or_create(
            tenant=self.tenant,
            name=rs_data['name'],
            defaults=defaults
        )

        return ruleset

    def _create_rule(self, rule_data, ruleset, qa_manager=None):
        """Create a sampling rule.

        SamplingRule model fields:
        - ruleset: FK to SamplingRuleSet
        - rule_type: CharField (choices from SamplingRuleType - UPPERCASE values)
        - value: PositiveIntegerField (optional)
        - order: PositiveIntegerField
        - algorithm_description: TextField
        - last_validated: DateTimeField (optional)
        - created_by: FK to User (optional)
        - modified_by: FK to User (optional)
        """
        # Explicitly set ALL fields - do not rely on model defaults
        # rule_type must be UPPERCASE: EVERY_NTH_PART, PERCENTAGE, RANDOM,
        # FIRST_N_PARTS, LAST_N_PARTS, EXACT_COUNT
        # Set last_validated to 30 days ago to show audit trail
        last_validated = self.today - timedelta(days=30)

        defaults = {
            'value': rule_data.get('value', None),
            'algorithm_description': rule_data.get('algorithm_description', 'SHA-256 hash modulo arithmetic'),
            'last_validated': last_validated,  # Show audit trail
            'created_by': qa_manager,
            'modified_by': qa_manager,
        }

        # Use update_or_create with unique identifier combining ruleset, type, and order
        rule, _ = SamplingRule.objects.update_or_create(
            tenant=self.tenant,
            ruleset=ruleset,
            rule_type=rule_data['rule_type'],  # UPPERCASE enum value
            order=rule_data.get('order', 0),
            defaults=defaults
        )

        return rule

    def _link_fallbacks(self, ruleset_map):
        """Link fallback rulesets (second pass).

        This must be done after all rulesets are created.
        """
        # Flow Testing: standard -> enhanced
        if 'flow-standard' in ruleset_map and 'flow-enhanced' in ruleset_map:
            flow_standard = ruleset_map['flow-standard']
            flow_enhanced = ruleset_map['flow-enhanced']
            flow_standard.fallback_ruleset = flow_enhanced
            flow_standard.save()

        # Nozzle Inspection: standard -> 100%
        if 'nozzle-standard' in ruleset_map and 'nozzle-100pct' in ruleset_map:
            nozzle_standard = ruleset_map['nozzle-standard']
            nozzle_100pct = ruleset_map['nozzle-100pct']
            nozzle_standard.fallback_ruleset = nozzle_100pct
            nozzle_standard.save()
