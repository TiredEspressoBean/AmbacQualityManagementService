"""
Tests for StagingListAdapter.

The fixture is built to exercise every branch the template has, because a Typst
syntax error in a branch the sample never reaches would ship green: a staged job and
an unstaged one (the tick box), a short line and a covered one, a job with no material
at all, and the unmapped-components callout.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.staging_list import (
    StagingListAdapter,
    StagingListContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestStagingListAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = StagingListAdapter
    fixture_name = "staging_list_sample"

    def test_cross_tenant_id_is_rejected(self):
        # The adapter takes no object id — it reads the requesting tenant's own
        # schedule via staging_list(tenant, ...), so there is no cross-tenant
        # identifier to probe. Station filtering is tenant-filtered in build_context.
        self.skipTest(
            "No cross-tenant identifier: the report is scoped to the requesting "
            "tenant's schedule, and the optional work_center is tenant-filtered."
        )


class StagingListFixtureShapeTests(SimpleTestCase):
    """The fixture must keep covering every template branch."""

    def setUp(self):
        import json
        from pathlib import Path
        path = (Path(__file__).parent / "fixtures" / "staging_list_sample.json")
        self.ctx = StagingListContext(**json.loads(path.read_text(encoding="utf-8")))

    def _jobs(self):
        return [j for s in self.ctx.stations for j in s.jobs]

    def test_covers_both_tick_states(self):
        staged = {j.staged for j in self._jobs()}
        self.assertEqual(staged, {True, False},
                         "fixture must include a staged and an unstaged job")

    def test_covers_short_and_covered_lines(self):
        shorts = {m.is_short for j in self._jobs() for m in j.materials}
        self.assertEqual(shorts, {True, False})

    def test_covers_a_job_with_no_material(self):
        self.assertTrue(any(len(j.materials) == 0 for j in self._jobs()),
                        "a step that consumes nothing must render its own branch")

    def test_covers_the_unmapped_callout(self):
        self.assertTrue(self.ctx.unmapped)

    def test_totals_match_the_blocks(self):
        self.assertEqual(self.ctx.total_jobs, len(self._jobs()))
        self.assertEqual(self.ctx.total_short,
                         sum(s.short_count for s in self.ctx.stations))
