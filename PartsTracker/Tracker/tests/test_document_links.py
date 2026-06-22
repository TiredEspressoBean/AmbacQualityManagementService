"""
Tests for multi-target Document associations (`DocumentLink`).

A Document keeps its single *primary* GenericForeignKey owner; `DocumentLink`
adds *additional* targets on top. Coverage:

- service helpers (attach/detach/query) — idempotency, revive, dedup;
- version carry-forward (own re-version + clone helper);
- the load-bearing customer access filter — a linked doc is visible iff its
  link target is accessible, the classification gate still applies, and links
  never leak a document across tenants.
"""

from django.contrib.contenttypes.models import ContentType

from Tracker.tests.base import TenantTestCase


class DocumentLinkServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, PartTypes, Documents

        # ContextVar is tenant_a (TenantTestCase.setUp).
        self.order = self.create_for_tenant(Orders, self.tenant_a, name="ORDER-1")
        self.part_type = self.create_for_tenant(PartTypes, self.tenant_a, name="Widget")
        self.doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="sheet.xlsx", file="parts_docs/a/sheet.xlsx", classification="PUBLIC",
        )

    def _live_links(self, document):
        return document.links.filter(archived=False)

    def test_attach_is_idempotent(self):
        from Tracker.services.core.documents import attach_document_to

        first = attach_document_to(self.doc, self.order)
        second = attach_document_to(self.doc, self.order)

        self.assertEqual(first.pk, second.pk, "Re-attach must return the same link.")
        self.assertEqual(self._live_links(self.doc).count(), 1)

    def test_detach_then_reattach_revives(self):
        from Tracker.services.core.documents import attach_document_to, detach_document_from

        link = attach_document_to(self.doc, self.order)
        detach_document_from(self.doc, self.order)
        self.assertEqual(self._live_links(self.doc).count(), 0, "Detach soft-deletes the link.")

        # Re-attaching must revive the archived row, not raise IntegrityError
        # against the partial unique constraint.
        revived = attach_document_to(self.doc, self.order)
        self.assertEqual(revived.pk, link.pk, "Re-attach revives the prior link row.")
        self.assertEqual(self._live_links(self.doc).count(), 1)

    def test_attach_never_touches_primary_gfk(self):
        from Tracker.services.core.documents import attach_document_to

        # doc starts with no primary owner
        self.assertIsNone(self.doc.content_type)
        attach_document_to(self.doc, self.part_type)
        self.doc.refresh_from_db()
        self.assertIsNone(self.doc.content_type, "Linking must not set the primary GFK.")

    def test_documents_attached_to_unions_and_dedupes(self):
        from Tracker.services.core.documents import attach_document_to, documents_attached_to
        from Tracker.models import Documents

        # primary_doc owns the order via the primary GFK
        order_ct = ContentType.objects.get_for_model(type(self.order))
        primary_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="primary.pdf", file="parts_docs/a/primary.pdf", classification="PUBLIC",
            content_type=order_ct, object_id=str(self.order.pk),
        )
        # self.doc reaches the order only via a link
        attach_document_to(self.doc, self.order)
        # primary_doc *also* gets a (redundant) link to the same order
        attach_document_to(primary_doc, self.order)

        attached = list(documents_attached_to(self.order))
        ids = {d.pk for d in attached}
        self.assertEqual(ids, {primary_doc.pk, self.doc.pk})
        self.assertEqual(len(attached), 2, "Union must be deduplicated.")


class DocumentLinkVersioningTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, PartTypes, Documents

        self.order = self.create_for_tenant(Orders, self.tenant_a, name="ORDER-V")
        self.part_type = self.create_for_tenant(PartTypes, self.tenant_a, name="Gadget")
        self.doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="v.pdf", file="parts_docs/a/v.pdf", classification="PUBLIC",
        )

    def test_own_reversion_carries_links_forward(self):
        from Tracker.services.core.documents import attach_document_to

        attach_document_to(self.doc, self.order)
        attach_document_to(self.doc, self.part_type)

        new_version = self.doc.create_new_version(change_description="rev")

        carried = {
            (l.content_type_id, l.object_id)
            for l in new_version.links.filter(archived=False)
        }
        expected = {
            (ContentType.objects.get_for_model(type(self.order)).id, str(self.order.pk)),
            (ContentType.objects.get_for_model(type(self.part_type)).id, str(self.part_type.pk)),
        }
        self.assertEqual(carried, expected, "New version must inherit the source's links.")

    def test_clone_document_links_is_idempotent(self):
        from Tracker.services.core.documents import attach_document_to, clone_document_links
        from Tracker.models import Documents

        attach_document_to(self.doc, self.order)
        target = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="clone.pdf", file="parts_docs/a/clone.pdf", classification="PUBLIC",
        )

        clone_document_links(source_document=self.doc, target_document=target)
        clone_document_links(source_document=self.doc, target_document=target)  # again

        self.assertEqual(
            target.links.filter(archived=False).count(), 1,
            "Cloning links twice must not duplicate.",
        )


class DocumentLinkAccessFilterTests(TenantTestCase):
    """The load-bearing case: links folded into the customer access filter."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, Documents
        from Tracker.services.core.documents import attach_document_to

        # user_a sees documents via relationship scoping, NOT full access.
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_documents'])

        # order_mine is owned by user_a; order_other has no customer (not accessible).
        self.order_mine = self.create_for_tenant(
            Orders, self.tenant_a, name="MINE", customer=self.user_a,
        )
        self.order_other = self.create_for_tenant(Orders, self.tenant_a, name="OTHER")

        self.doc_linked = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="linked.pdf", file="parts_docs/a/linked.pdf", classification="PUBLIC",
        )
        self.doc_inaccessible = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="inacc.pdf", file="parts_docs/a/inacc.pdf", classification="PUBLIC",
        )
        self.doc_confidential = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="conf.pdf", file="parts_docs/a/conf.pdf", classification="CONFIDENTIAL",
        )

        attach_document_to(self.doc_linked, self.order_mine)
        attach_document_to(self.doc_inaccessible, self.order_other)
        attach_document_to(self.doc_confidential, self.order_mine)

    def _visible_ids(self):
        from Tracker.models import Documents
        return set(Documents.objects.for_user(self.user_a).values_list('id', flat=True))

    def test_doc_linked_to_accessible_order_is_visible(self):
        self.assertIn(self.doc_linked.id, self._visible_ids())

    def test_doc_linked_to_inaccessible_order_is_hidden(self):
        self.assertNotIn(self.doc_inaccessible.id, self._visible_ids())

    def test_classification_gate_still_applies_to_linked_docs(self):
        # Linked to an accessible order, but CONFIDENTIAL — customer path only
        # exposes PUBLIC, so the link must not bypass classification.
        self.assertNotIn(self.doc_confidential.id, self._visible_ids())

    def test_no_cross_tenant_leak_via_links(self):
        from Tracker.models import Documents

        # A document in tenant_b must never appear for a tenant_a user, even if
        # something tried to link to a tenant_a object.
        tenant_b_doc = self.create_for_tenant(
            Documents, self.tenant_b,
            file_name="b.pdf", file="parts_docs/b/b.pdf", classification="PUBLIC",
        )
        self.assertNotIn(tenant_b_doc.id, self._visible_ids())


class DocumentListFilterLinkAwarenessTests(TenantTestCase):
    """The list endpoint's content_type+object_id filter must be link-aware."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, Documents
        from Tracker.services.core.documents import attach_document_to

        self.order = self.create_for_tenant(Orders, self.tenant_a, name="FILTER-ORDER")
        self.order_ct = ContentType.objects.get_for_model(Orders)

        # primary_doc: attached via the primary GFK
        self.primary_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="primary.pdf", file="parts_docs/a/primary.pdf", classification="PUBLIC",
            content_type=self.order_ct, object_id=str(self.order.pk),
        )
        # linked_doc: reaches the order ONLY via a secondary link (no primary owner)
        self.linked_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="linked.pdf", file="parts_docs/a/linked.pdf", classification="PUBLIC",
        )
        attach_document_to(self.linked_doc, self.order)
        # unrelated_doc: nothing to do with the order
        self.unrelated_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="unrelated.pdf", file="parts_docs/a/unrelated.pdf", classification="PUBLIC",
        )

    def _filtered_ids(self, data):
        from Tracker.filters import DocumentFilter
        from Tracker.models import Documents
        f = DocumentFilter(data, queryset=Documents.objects.all())
        return set(f.qs.values_list('id', flat=True))

    def test_content_type_and_object_id_includes_linked(self):
        ids = self._filtered_ids({
            'content_type': self.order_ct.pk, 'object_id': str(self.order.pk),
        })
        self.assertIn(self.primary_doc.id, ids)
        self.assertIn(self.linked_doc.id, ids, "Link-attached doc must appear when filtering by target.")
        self.assertNotIn(self.unrelated_doc.id, ids)

    def test_object_id_only_preserves_primary_only_behavior(self):
        # Single-field filtering keeps the prior semantics: linked_doc has no
        # primary object_id, so it must NOT appear.
        ids = self._filtered_ids({'object_id': str(self.order.pk)})
        self.assertIn(self.primary_doc.id, ids)
        self.assertNotIn(self.linked_doc.id, ids)

    def test_content_type_only_preserves_primary_only_behavior(self):
        ids = self._filtered_ids({'content_type': self.order_ct.pk})
        self.assertIn(self.primary_doc.id, ids)
        self.assertNotIn(self.linked_doc.id, ids)


class DocumentLinkTargetVersioningTests(TenantTestCase):
    """P1.2 — a link to a versioned target follows it forward on re-version."""

    def setUp(self):
        super().setUp()
        from Tracker.models import PartTypes, Documents

        self.part_type = self.create_for_tenant(PartTypes, self.tenant_a, name="Versioned")
        self.doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="spec.pdf", file="parts_docs/a/spec.pdf", classification="PUBLIC",
        )

    def test_link_forwards_to_new_target_version(self):
        from Tracker.services.core.documents import attach_document_to, documents_attached_to

        attach_document_to(self.doc, self.part_type)  # link to v1
        v2 = self.part_type.create_new_version(change_description="rev")

        # The new version inherits the association...
        self.assertIn(
            self.doc.id, set(documents_attached_to(v2).values_list('id', flat=True)),
            "Link must follow the part type forward to its new version.",
        )
        # ...and the old version keeps its link (copy, not move — history kept).
        self.assertIn(
            self.doc.id, set(documents_attached_to(self.part_type).values_list('id', flat=True)),
            "Old version must retain its link for history.",
        )


class DocumentLinkPermissionTests(TenantTestCase):
    """P1.1 (C) — attach/detach gate on dedicated DocumentLink CRUD perms."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, Documents

        # The doc is primary-attached to user_a's OWN order, so a relationship-
        # scoped user with view_documents can retrieve it via get_object — which
        # isolates the attach/detach perm gate from document visibility.
        self.order = self.create_for_tenant(
            Orders, self.tenant_a, name="PERM-ORDER", customer=self.user_a,
        )
        self.order_ct = ContentType.objects.get_for_model(Orders)
        self.doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="p.pdf", file="parts_docs/a/p.pdf", classification="PUBLIC",
            content_type=self.order_ct, object_id=str(self.order.pk),
        )
        self.other_order = self.create_for_tenant(
            Orders, self.tenant_a, name="OTHER", customer=self.user_a,
        )
        self.body = {'content_type': self.order_ct.pk, 'object_id': str(self.other_order.pk)}

    def _attach(self):
        return self.client.post(
            f"/api/Documents/{self.doc.id}/attach/", self.body, format="json",
        )

    def test_attach_forbidden_without_documentlink_perm(self):
        # Can see the doc (view_documents + owns the order) but lacks
        # add_documentlink — attach must be refused.
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_documents'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self._attach()
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_attach_and_detach_with_documentlink_perms(self):
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['view_documents', 'add_documentlink', 'delete_documentlink'],
        )
        self.authenticate_as(self.user_a, self.tenant_a)

        attach = self._attach()
        self.assertEqual(attach.status_code, 200, attach.content)
        self.assertEqual(self.doc.links.filter(archived=False).count(), 1)

        detach = self.client.post(
            f"/api/Documents/{self.doc.id}/detach/", self.body, format="json",
        )
        self.assertEqual(detach.status_code, 200, detach.content)
        self.assertEqual(self.doc.links.filter(archived=False).count(), 0)
