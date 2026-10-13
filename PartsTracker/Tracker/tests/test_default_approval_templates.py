"""The default approval templates must name groups that actually exist.

`defaults_service.APPROVAL_TEMPLATES` provisions every new tenant. Two of its
fields are matched against `TenantGroup.name` **character for character**:

  * `auto_assign_by_role` — `approval.py` filters `user_roles__group__name=...`
  * `default_groups_names` — the M2M is set with `name__in=[...]`

A name that matches nothing assigns **nobody**, and nothing complains: a filter
that returns no rows is not an error. That is exactly how it failed — the list
carried an older underscored convention (`QA_Manager`, `Production_Manager`,
`Admin`) long after the groups were renamed, and on 2026-10-12 three of the four
templates on the demo tenant resolved to zero users.

No existing test caught it. The approval suites each set `auto_assign_by_role`
in their own fixtures, or never assert who ended up assigned, so 119 of them
passed before and after the fix.

These assert against `GROUP_PRESETS` rather than a seeded tenant, so they hold
without any data and fail the moment someone adds a template pointing at a group
that was never a preset.
"""
from django.test import SimpleTestCase

from Tracker.presets import GROUP_PRESETS
from Tracker.services.defaults_service import APPROVAL_TEMPLATES


def _preset_group_names() -> set[str]:
    """Exactly the names `GroupSeeder` creates, which is what the lookups match."""
    return {preset['name'] for preset in GROUP_PRESETS.values()}


class DefaultApprovalTemplateGroupNamesTests(SimpleTestCase):
    def test_every_auto_assign_role_is_a_real_group(self):
        valid = _preset_group_names()
        bad = [(t['approval_type'], t.get('auto_assign_by_role'))
               for t in APPROVAL_TEMPLATES
               if t.get('auto_assign_by_role') and t['auto_assign_by_role'] not in valid]
        self.assertEqual(
            bad, [],
            "auto_assign_by_role must match a preset group name exactly — a name "
            "that matches nothing assigns NOBODY, silently. Valid names: "
            f"{sorted(valid)}")

    def test_every_default_group_is_a_real_group(self):
        valid = _preset_group_names()
        bad = []
        for t in APPROVAL_TEMPLATES:
            for name in t.get('default_groups_names', []) or []:
                if name not in valid:
                    bad.append((t['approval_type'], name))
        self.assertEqual(
            bad, [],
            "default_groups_names entries are matched with name__in=[...]; an "
            f"unmatched name silently sets no groups. Valid names: {sorted(valid)}")

    def test_no_underscored_group_names_anywhere(self):
        """The specific regression. Group names have spaces, never underscores."""
        offenders = []
        for t in APPROVAL_TEMPLATES:
            names = [t.get('auto_assign_by_role')] + list(t.get('default_groups_names', []) or [])
            offenders += [(t['approval_type'], n) for n in names if n and '_' in n]
        self.assertEqual(offenders, [],
                         "Group names carry spaces, not underscores — 'QA Manager', "
                         "not 'QA_Manager'.")

    def test_the_change_control_chain_is_complete(self):
        """A tenant that can raise a change must be able to finish one.

        `submit_pcr` looks up PCR_APPROVAL, `submit_pco` looks up PCO_APPROVAL,
        and releasing a notice looks up PCN_RELEASE — each raising a 400 naming
        the type when it is absent. PCN_RELEASE was missing, so a tenant could
        approve a change and then stall at the point the floor is told about it.
        """
        present = {t['approval_type'] for t in APPROVAL_TEMPLATES}
        for required in ('PCR_APPROVAL', 'PCO_APPROVAL', 'PCN_RELEASE'):
            self.assertIn(required, present,
                          f"{required} is looked up by name; without it that stage "
                          "of change control refuses with a 400.")

    def test_approval_types_are_valid_choices(self):
        from Tracker.models.core import Approval_Type
        valid = {c[0] for c in Approval_Type.choices}
        bad = [t['approval_type'] for t in APPROVAL_TEMPLATES
               if t['approval_type'] not in valid]
        self.assertEqual(bad, [], f"not valid Approval_Type choices: {bad}")
