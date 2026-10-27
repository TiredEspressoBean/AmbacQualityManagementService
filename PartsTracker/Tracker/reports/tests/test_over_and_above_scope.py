"""
Tests for OverAndAboveScopeAdapter — the scope document sent to a customer for their
authorisation of work beyond the rebuild level they bought.

- the four mixin tests against the fixture (validates, compiles, deterministic);
- DB-backed: the context carries each code awaiting the customer, its work, its parts
  and the finding behind it, leaves out what is pre-approved, and carries no price;
- refusals: another tenant's core, an exchange unit, and a unit with nothing to ask.
"""
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from Tracker.reports.adapters.over_and_above_scope import OverAndAboveScopeAdapter
from Tracker.reports.services.pdf_generator import PdfGenerator, ReportParamError
from Tracker.reports.tests.base import ReportAdapterTestMixin
from Tracker.tests.base import TenantTestCase

# No price in any form: UQMES produces scope, pricing happens in the system that owns it.
_PRICE_WORDS = ('price', 'cost', 'total', 'amount', 'quote', 'rate', 'charge', 'currency')


def _keys(obj):
    """Every key in a nested dict/list structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


class TestOverAndAboveScopeAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = OverAndAboveScopeAdapter
    fixture_name = "over_and_above_scope_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Cross-tenant probe is in OverAndAboveScopeContextTests (requires DB).")

    def test_context_model_has_no_price_fields(self):
        from Tracker.reports.adapters.over_and_above_scope import ScopeLineRow, ScopePartRow
        keys = set(_keys(self._load_fixture()))
        for model in (self.adapter_class.context_model_class, ScopeLineRow, ScopePartRow):
            keys |= set(model.model_fields)
        self.assertFalse([k for k in keys if any(w in k.lower() for w in _PRICE_WORDS)])


class _ScopeFixture(TenantTestCase):
    """Route: Clean → Check → Assemble, with Replace (NZL-REPLACE, not pre-approved) and
    Lap (VLV-RECON, pre-approved) off Check. The nozzle was scrapped at the bench; the
    valve came out grade C."""

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Companies, HarvestedComponent, Orders, PartTypes, Processes,
            ProcessStep, RepairCode, StepEdge, Steps, WorkOrder, WorkOrderStatus,
        )
        from Tracker.models.mes_lite import EdgeType
        from Tracker.services.reman.core_part import create_core

        t = self.tenant_a
        self.core_type = PartTypes.objects.create(tenant=t, name='Injector')
        self.nozzle = PartTypes.objects.create(tenant=t, name='Nozzle', ERP_id='NZL-7',
                                               can_recover=True)
        self.valve = PartTypes.objects.create(tenant=t, name='Valve', can_recover=True)
        process = Processes.objects.create(tenant=t, name='Reman', part_type=self.core_type,
                                           status='APPROVED')
        replace = RepairCode.objects.create(tenant=t, code='NZL-REPLACE', name='Replace nozzle',
                                            component_type=self.nozzle, trigger='REPLACE_BUY')
        lap = RepairCode.objects.create(tenant=t, code='VLV-RECON', name='Lap valve seat',
                                        component_type=self.valve, trigger='RECONDITION')
        steps = {}
        for i, (n, kw) in enumerate([
                ('Clean', {}), ('Check', {}), ('Assemble', {}),
                ('Nozzle Replacement', {'step_type': 'REPAIR', 'repair_code': replace}),
                ('Lap', {'step_type': 'REPAIR', 'repair_code': lap})], start=1):
            steps[n] = Steps.objects.create(tenant=t, part_type=self.core_type, name=n, **kw)
            ProcessStep.objects.create(process=process, step=steps[n], order=i)

        def edge(a, b, typ=EdgeType.DEFAULT, pre=False):
            StepEdge.objects.create(process=process, from_step=steps[a], to_step=steps[b],
                                    edge_type=typ, pre_approved=pre)
        edge('Clean', 'Check')
        edge('Check', 'Assemble')
        edge('Nozzle Replacement', 'Assemble')
        edge('Lap', 'Assemble')
        edge('Check', 'Nozzle Replacement', EdgeType.ALTERNATE, pre=False)
        edge('Check', 'Lap', EdgeType.ALTERNATE, pre=True)

        bom = BOM.objects.create(tenant=t, part_type=self.core_type, revision='A',
                                 bom_type='ASSEMBLY', status='RELEASED', is_current_version=True)
        BOMLine.objects.create(tenant=t, bom=bom, component_type=self.nozzle,
                               quantity=Decimal(1), source='BUY', line_number=1)
        BOMLine.objects.create(tenant=t, bom=bom, component_type=self.valve,
                               quantity=Decimal(1), source='BUY', line_number=2)

        self.customer = Companies.objects.create(tenant=t, name='Fleet Co', description='')
        order = Orders.objects.create(tenant=t, company=self.customer, name='Fleet order',
                                      order_number='ORD-77')
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id='WO-OAA', quantity=1,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS,
                                           process=process)
        self.steps = steps
        self.core = create_core(
            tenant=t, core_number='CORE-OAA-1', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='AWAITING_AUTHORISATION',
            work_order=self.wo, step=steps['Check'], order=order, customer=self.customer,
            serial_number='SN-1', received_date=date(2026, 10, 1), received_by=self.user_a)
        HarvestedComponent.objects.create(
            tenant=t, core=self.core, component_type=self.nozzle, condition_grade='SCRAP',
            is_scrapped=True, condition_notes='Hairline crack at the needle guide',
            disassembled_by=self.user_a)
        HarvestedComponent.objects.create(
            tenant=t, core=self.core, component_type=self.valve, condition_grade='C',
            disassembled_by=self.user_a)

    def _context(self, core=None, user=None):
        return OverAndAboveScopeAdapter().build_context(
            {'core_id': (core or self.core).id}, user or self.user_a, self.tenant_a)



class OverAndAboveScopeContextTests(_ScopeFixture):
    """The single-unit sheet's context, on the fixture route."""

    def test_lists_the_code_awaiting_the_customer_with_its_work_parts_and_finding(self):
        ctx = self._context()
        self.assertEqual([line.code for line in ctx.lines], ['NZL-REPLACE'])
        line = ctx.lines[0]
        self.assertEqual(line.name, 'Replace nozzle')
        self.assertEqual(line.work, ['Nozzle Replacement'])
        self.assertTrue(any('Hairline crack at the needle guide' in f for f in line.findings))
        part, = line.parts
        self.assertEqual((part.component, part.part_number, part.source),
                         ('Nozzle', 'NZL-7', 'Replacement part'))
        self.assertIn('Hairline crack', part.finding)

    def test_carries_the_unit_and_what_it_was_bought_with(self):
        ctx = self._context()
        self.assertEqual((ctx.core_number, ctx.serial, ctx.unit, ctx.customer_name, ctx.order),
                         ('CORE-OAA-1', 'SN-1', 'Injector', 'Fleet Co', 'ORD-77'))
        self.assertTrue(ctx.awaiting)

    def test_a_pre_approved_repair_is_not_asked_about(self):
        self.assertNotIn('VLV-RECON', [line.code for line in self._context().lines])

    def test_carries_no_price(self):
        dumped = self._context().model_dump(mode='json')
        self.assertFalse([k for k in _keys(dumped)
                          if any(w in k.lower() for w in _PRICE_WORDS)])

    def test_a_unit_in_rebuild_prints_what_a_request_would_ask(self):
        self.core.status = 'IN_REBUILD'
        self.core.save(update_fields=['status'])
        ctx = self._context()
        self.assertFalse(ctx.awaiting)
        self.assertEqual([line.code for line in ctx.lines], ['NZL-REPLACE'])

    def test_renders_through_the_generator(self):
        pdf = PdfGenerator().generate('over_and_above_scope', {'core_id': str(self.core.id)},
                                      user=self.user_a)
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_another_tenants_core_is_rejected(self):
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate('over_and_above_scope', {'core_id': str(self.core.id)},
                                    user=self.user_b)
        self.assertIn('core_id', ctx.exception.errors)

    def test_an_exchange_unit_is_rejected(self):
        self.core.fulfilment_mode = 'EXCHANGE'
        self.core.save(update_fields=['fulfilment_mode'])
        with self.assertRaises(ReportParamError):
            PdfGenerator().generate('over_and_above_scope', {'core_id': str(self.core.id)},
                                    user=self.user_a)

    def test_nothing_to_ask_is_refused(self):
        self.core.approved_repair_codes = ['NZL-REPLACE']
        self.core.save(update_fields=['approved_repair_codes'])
        with self.assertRaisesMessage(ReportParamError, 'nothing to authorise'):
            self._context()


class TestOverAndAboveLotAdapter(ReportAdapterTestMixin, SimpleTestCase):
    from Tracker.reports.adapters.over_and_above_scope import OverAndAboveLotAdapter as adapter_class
    fixture_name = "over_and_above_scope_lot_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Cross-tenant probe is in OverAndAboveLotTests (requires DB).")


class OverAndAboveLotTests(OverAndAboveScopeContextTests):
    """A second unit of the same customer's, its nozzle also scrapped: the lot sheet and
    the bulk send / answer. Inherits the single-unit tests' route and first unit."""

    def setUp(self):
        super().setUp()
        from Tracker.models import HarvestedComponent
        from Tracker.services.reman.core_part import create_core
        self.core2 = create_core(
            tenant=self.tenant_a, core_number='CORE-OAA-2', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='AWAITING_AUTHORISATION',
            work_order=self.wo, step=self.steps['Check'], customer=self.customer,
            serial_number='SN-2', received_date=date(2026, 10, 2), received_by=self.user_a)
        HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core2, component_type=self.nozzle,
            condition_grade='SCRAP', is_scrapped=True, condition_notes='Seized needle',
            disassembled_by=self.user_a)

    def _lot(self, *cores, user=None):
        from Tracker.reports.adapters.over_and_above_scope import OverAndAboveLotAdapter
        return OverAndAboveLotAdapter().build_context(
            {'core_ids': [c.id for c in cores]}, user or self.user_a, self.tenant_a)

    def test_the_lot_sheet_lists_each_unit_with_its_own_items(self):
        ctx = self._lot(self.core2, self.core)
        self.assertEqual([u.core_number for u in ctx.units], ['CORE-OAA-1', 'CORE-OAA-2'])
        self.assertEqual([[line.code for line in u.lines] for u in ctx.units],
                         [['NZL-REPLACE'], ['NZL-REPLACE']])
        self.assertTrue(any('Seized needle' in f for f in ctx.units[1].lines[0].findings))
        self.assertEqual((ctx.customer_name, ctx.reference), ('Fleet Co', 'CORE-OAA-1 +1'))

    def test_the_lot_sheet_renders_and_carries_no_price(self):
        pdf = PdfGenerator().generate(
            'over_and_above_scope_lot', {'core_ids': [str(self.core.id), str(self.core2.id)]},
            user=self.user_a)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertFalse([k for k in _keys(self._lot(self.core, self.core2).model_dump(mode='json'))
                          if any(w in k.lower() for w in _PRICE_WORDS)])

    def test_the_lot_sheet_is_for_one_customer(self):
        from Tracker.models import Companies
        self.core2.customer = Companies.objects.create(tenant=self.tenant_a, name='Other', description='')
        self.core2.save(update_fields=['customer'])
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                'over_and_above_scope_lot', {'core_ids': [str(self.core.id), str(self.core2.id)]},
                user=self.user_a)
        self.assertIn('more than one customer', str(ctx.exception.errors))

    def test_one_answer_is_recorded_on_every_unit(self):
        from Tracker.services.reman.release import record_authorisation_for
        cores = record_authorisation_for([self.core, self.core2], True, self.user_a,
                                         contact='Pat', method='email', reference='PO-9')
        for c in cores:
            c.refresh_from_db()
            self.assertEqual((c.status, c.authorisation_reference), ('IN_REBUILD', 'PO-9'))
            self.assertIn('NZL-REPLACE', c.approved_repair_codes)

    def test_a_unit_that_cant_take_the_answer_refuses_the_batch(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import record_authorisation_for
        self.core2.status = 'IN_REBUILD'
        self.core2.save(update_fields=['status'])
        with self.assertRaisesMessage(ValidationError, 'CORE-OAA-2'):
            record_authorisation_for([self.core, self.core2], True, self.user_a)
        self.core.refresh_from_db()
        self.assertEqual(self.core.status, 'AWAITING_AUTHORISATION')  # not half-answered

    def test_a_lot_is_sent_for_authorisation_together(self):
        from Tracker.services.reman.release import request_authorisation_for
        for c in (self.core, self.core2):
            c.status = 'IN_REBUILD'
            c.save(update_fields=['status'])
        cores = request_authorisation_for([self.core, self.core2], self.user_a)
        self.assertEqual({c.status for c in cores}, {'AWAITING_AUTHORISATION'})

    def test_bulk_answer_endpoint(self):
        from rest_framework.test import APIClient
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_core', 'change_core', 'full_tenant_access'])
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        resp = client.post('/api/Cores/bulk_record_authorisation/', {
            'core_ids': [str(self.core.id), str(self.core2.id)], 'approved': False,
            'contact': 'Pat'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual({c['status'] for c in resp.json()}, {'DECLINED'})


class PerItemAnswerTests(_ScopeFixture):
    """The customer answers item by item. The valve recondition (VLV-RECON) is made to
    wait on them too, and the shop marks it optional; the nozzle stays required."""

    def setUp(self):
        super().setUp()
        from Tracker.models import RepairCode, StepEdge
        StepEdge.objects.filter(to_step=self.steps['Lap']).update(pre_approved=False)
        RepairCode.objects.filter(code='VLV-RECON').update(required=False)

    def _answer(self, declined, approved=True):
        from Tracker.services.reman.release import record_authorisation
        record_authorisation(self.core, approved, self.user_a, contact='Pat',
                             declined_codes=declined)
        self.core.refresh_from_db()
        return self.core

    def test_both_repairs_wait_and_the_scope_says_which_is_required(self):
        from Tracker.services.reman.release import pending_authorisation_scope
        scope = {i['code']: i['required'] for i in pending_authorisation_scope(self.core)}
        self.assertEqual(scope, {'NZL-REPLACE': True, 'VLV-RECON': False})
        lines = {line.code: line.required for line in self._context().lines}
        self.assertEqual(lines, {'NZL-REPLACE': True, 'VLV-RECON': False})

    def test_declining_an_optional_repair_rebuilds_without_it(self):
        from Tracker.services.reman.repair_routing import codes_needing_approval
        from Tracker.services.reman.rebuild import resolve_rebuild_plan
        core = self._answer(['VLV-RECON'])
        self.assertEqual(core.status, 'IN_REBUILD')
        self.assertIn('NZL-REPLACE', core.approved_repair_codes)
        self.assertNotIn('VLV-RECON', core.approved_repair_codes)
        self.assertEqual(core.declined_repair_codes, ['VLV-RECON'])
        self.assertEqual(codes_needing_approval(core), [])          # not asked again
        self.assertNotIn('VLV-RECON',
                         [r.code for r in resolve_rebuild_plan(core).expected_repairs])

    def test_a_declined_repair_is_not_taken_at_the_check(self):
        from Tracker.services.reman.repair_routing import repair_route
        core = self._answer(['VLV-RECON'])
        self.assertEqual(repair_route(core.part, self.steps['Check']),
                         self.steps['Nozzle Replacement'])

    def test_declining_a_required_repair_declines_the_unit(self):
        core = self._answer(['NZL-REPLACE'])
        self.assertEqual(core.status, 'DECLINED')
        self.assertEqual((core.approved_repair_codes, core.declined_repair_codes), ([], []))
        self.assertIn('required for the rebuild', core.condition_notes)

    def test_a_code_not_waiting_is_refused(self):
        from django.core.exceptions import ValidationError
        with self.assertRaisesMessage(ValidationError, 'not waiting'):
            self._answer(['PLG-REPLACE'])
        self.core.refresh_from_db()
        self.assertEqual(self.core.status, 'AWAITING_AUTHORISATION')

    def test_an_item_recorded_wrong_is_corrected_on_its_own(self):
        from Tracker.services.reman.release import correct_authorisation
        core = self._answer(['VLV-RECON'])
        correct_authorisation(core, True, self.user_a, 'They approved the valve too',
                              declined_codes=[])
        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_REBUILD')
        self.assertEqual(sorted(core.authorisation_codes), ['NZL-REPLACE', 'VLV-RECON'])
        self.assertEqual(core.declined_repair_codes, [])
        # And back the other way: the valve declined after all.
        correct_authorisation(core, True, self.user_a, 'Email says no valve',
                              declined_codes=['VLV-RECON'])
        core.refresh_from_db()
        self.assertEqual(core.declined_repair_codes, ['VLV-RECON'])
        self.assertNotIn('VLV-RECON', core.approved_repair_codes)

    def test_the_same_answer_is_refused_as_a_correction(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import correct_authorisation
        core = self._answer(['VLV-RECON'])
        with self.assertRaisesMessage(ValidationError, 'already on record'):
            correct_authorisation(core, True, self.user_a, 'no change',
                                  declined_codes=['VLV-RECON'])

    def test_the_answer_endpoint_takes_declined_items(self):
        from rest_framework.test import APIClient
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_core', 'change_core', 'full_tenant_access'])
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        resp = client.post(f'/api/Cores/{self.core.id}/record_authorisation/', {
            'approved': True, 'declined_codes': ['VLV-RECON'], 'contact': 'Pat'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()['status'], resp.json()['declined_repair_codes']),
                         ('IN_REBUILD', ['VLV-RECON']))


class DeclinedWorkOnShippingDocsTests(SimpleTestCase):
    """A unit rebuilt without a declined repair: the CoC and packing list say so."""

    def test_the_coc_and_packing_list_list_declined_work(self):
        import json
        from pathlib import Path
        from Tracker.reports.adapters.shipment_documents import ShipmentDocumentContext
        from Tracker.reports.services.typst_generator import generate_typst_pdf
        data = json.loads((Path(__file__).parent / 'fixtures' / 'shipment_document_sample.json')
                          .read_text(encoding='utf-8'))
        data['declined_work'] = [{'unit': 'SN-1 (CORE-1)', 'code': 'VLV-RECON',
                                  'name': 'Lap valve seat'}]
        ctx = ShipmentDocumentContext(**data).model_dump(mode='json')
        for template in ('shipment_coc.typ', 'packing_list.typ'):
            self.assertTrue(generate_typst_pdf(template, ctx).startswith(b'%PDF'))
