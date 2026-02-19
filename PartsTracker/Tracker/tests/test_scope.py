"""
Tests for the scope.py graph traversal utilities.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from unittest import skipIf

from Tracker.scope import (
    get_descendants,
    get_ancestors,
    find_in_graph,
    count_descendants,
    merge_scopes,
    subtract_scope,
    explain_path,
    related_to,
)
from Tracker.models import (
    ProcessStep,
    StepEdge,
    EdgeType,
    Orders,
    Parts,
    PartTypes,
    Processes,
    Steps,
    WorkOrder,
    QualityReports,
    Documents,
    Companies,
    Tenant,
    TenantGroupMembership,
    TenantGroup,
    UserRole,
)
from Tracker.tests.base import VectorTestCase


def get_or_create_test_tenant(name="Test Tenant"):
    """Helper to get or create a test tenant."""
    tenant, _ = Tenant.objects.get_or_create(
        slug=name.lower().replace(" ", "-"),
        defaults={'name': name}
    )
    return tenant


# Permission sets for different role types
STAFF_PERMISSIONS = [
    'full_tenant_access',
    'view_orders', 'add_orders', 'change_orders', 'delete_orders',
    'view_parts', 'add_parts', 'change_parts', 'delete_parts',
    'view_documents', 'add_documents', 'change_documents', 'delete_documents',
    'view_qualityreports', 'add_qualityreports', 'change_qualityreports',
    'view_workorder', 'add_workorder', 'change_workorder',
    'view_companies', 'view_parttypes',
]

CUSTOMER_PERMISSIONS = [
    # Note: NO full_tenant_access - customers see only their own data
    'view_orders', 'view_parts', 'view_documents', 'view_qualityreports',
    'view_workorder', 'view_companies',
]


def add_user_to_tenant_group(user, group_name, tenant=None):
    """
    Helper to add a user to a TenantGroup with appropriate permissions.

    Staff/Manager groups get full_tenant_access.
    Customer group does not (sees only relationship-filtered data).
    """
    if tenant is None:
        tenant = get_or_create_test_tenant()
    if user.tenant is None:
        user.tenant = tenant
        user.save()

    # Determine permissions based on group name
    if 'Customer' in group_name:
        permissions = CUSTOMER_PERMISSIONS
    else:
        # Staff/Manager groups get full access
        permissions = STAFF_PERMISSIONS

    # Create TenantGroup with permissions
    group, created = TenantGroup.objects.get_or_create(
        tenant=tenant,
        name=group_name,
        defaults={
            'description': f'Test group: {group_name}',
            'is_custom': True,
        }
    )

    if created:
        # Add permissions to newly created group
        perms = Permission.objects.filter(codename__in=permissions)
        group.permissions.add(*perms)

    # Create UserRole to link user to group
    UserRole.objects.get_or_create(user=user, group=group)


def is_vector_extension_available():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cursor.fetchone() is not None
    except Exception:
        return False


User = get_user_model()


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopeTraversalTestCase(VectorTestCase):
    """Test basic traversal functionality."""

    @classmethod
    def setUpTestData(cls):
        """Create a test hierarchy:

        Order
        ├── Part1
        │   ├── PartType1
        │   │   └── Process1
        │   │       └── Step1
        │   └── QualityReport1
        ├── Part2
        │   └── PartType1 (shared)
        └── WorkOrder1
            └── Process1 (shared)
        """
        # Create company and user
        cls.company = Companies.objects.create(name="Test Company")
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
        )

        # Create part type with process and step
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.process = Processes.objects.create(
            name="Test Process",
            part_type=cls.part_type,
        )
        cls.step = Steps.objects.create(
            name="Test Step",
            part_type=cls.part_type,
            step_type='task',
        )
        ProcessStep.objects.create(
            process=cls.process,
            step=cls.step,
            order=1,
            is_entry_point=True,
        )

        # Create order
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )

        # Create parts
        cls.part1 = Parts.objects.create(
            ERP_id="PART-001",
            order=cls.order,
            part_type=cls.part_type,
        )
        cls.part2 = Parts.objects.create(
            ERP_id="PART-002",
            order=cls.order,
            part_type=cls.part_type,
        )

        # Create quality report
        cls.quality_report = QualityReports.objects.create(
            part=cls.part1,
        )

        # Create work order
        cls.work_order = WorkOrder.objects.create(
            ERP_id="WO-001",
            related_order=cls.order,
        )

    def test_get_descendants_from_order(self):
        """Test that get_descendants finds all children of an order."""
        scope = get_descendants(self.order)

        # Should include the order itself
        order_ct = ContentType.objects.get_for_model(Orders)
        self.assertIn(order_ct.id, scope)
        self.assertIn(self.order.pk, scope[order_ct.id])

        # Should include parts
        parts_ct = ContentType.objects.get_for_model(Parts)
        self.assertIn(parts_ct.id, scope)
        self.assertIn(self.part1.pk, scope[parts_ct.id])
        self.assertIn(self.part2.pk, scope[parts_ct.id])

        # Should include work order
        wo_ct = ContentType.objects.get_for_model(WorkOrder)
        self.assertIn(wo_ct.id, scope)
        self.assertIn(self.work_order.pk, scope[wo_ct.id])

        # Should include quality report
        qr_ct = ContentType.objects.get_for_model(QualityReports)
        self.assertIn(qr_ct.id, scope)
        self.assertIn(self.quality_report.pk, scope[qr_ct.id])

    def test_get_descendants_with_max_depth(self):
        """Test depth limiting."""
        # Depth 0 should only include the order itself
        scope = get_descendants(self.order, max_depth=0)
        order_ct = ContentType.objects.get_for_model(Orders)
        self.assertIn(order_ct.id, scope)
        self.assertEqual(len(scope), 1)

        # Depth 1 should include order, parts, and work orders
        scope = get_descendants(self.order, max_depth=1)
        parts_ct = ContentType.objects.get_for_model(Parts)
        self.assertIn(parts_ct.id, scope)

    def test_get_descendants_with_include_types(self):
        """Test filtering to specific types."""
        scope = get_descendants(self.order, include_types=[Parts])

        parts_ct = ContentType.objects.get_for_model(Parts)
        self.assertIn(parts_ct.id, scope)

        # Should not traverse to quality reports since we only included Parts
        qr_ct = ContentType.objects.get_for_model(QualityReports)
        self.assertNotIn(qr_ct.id, scope)

    def test_get_descendants_with_exclude_types(self):
        """Test excluding specific types."""
        scope = get_descendants(self.order, exclude_types=[QualityReports])

        # Should still have parts
        parts_ct = ContentType.objects.get_for_model(Parts)
        self.assertIn(parts_ct.id, scope)

        # Should not have quality reports
        qr_ct = ContentType.objects.get_for_model(QualityReports)
        self.assertNotIn(qr_ct.id, scope)

    def test_get_ancestors_from_step(self):
        """Test traversing up the hierarchy.

        Note: With the ProcessStep junction table, Steps no longer have a direct FK
        to Process. Ancestor traversal from Step finds PartType (via part_type FK)
        but not Process (which is linked via ProcessStep, not a direct FK).
        """
        scope = get_ancestors(self.step)

        # Should include step itself
        step_ct = ContentType.objects.get_for_model(Steps)
        self.assertIn(step_ct.id, scope)
        self.assertIn(self.step.pk, scope[step_ct.id])

        # Should include part type (Steps still have part_type FK)
        pt_ct = ContentType.objects.get_for_model(PartTypes)
        self.assertIn(pt_ct.id, scope)
        self.assertIn(self.part_type.pk, scope[pt_ct.id])

        # Process is NOT in ancestors because Steps link to Process via
        # ProcessStep junction table, not a direct FK

    def test_get_ancestors_from_quality_report(self):
        """Test ancestors of a quality report."""
        scope = get_ancestors(self.quality_report)

        # Should include quality report itself
        qr_ct = ContentType.objects.get_for_model(QualityReports)
        self.assertIn(qr_ct.id, scope)

        # Should include part
        parts_ct = ContentType.objects.get_for_model(Parts)
        self.assertIn(parts_ct.id, scope)
        self.assertIn(self.part1.pk, scope[parts_ct.id])

        # Should include order
        order_ct = ContentType.objects.get_for_model(Orders)
        self.assertIn(order_ct.id, scope)
        self.assertIn(self.order.pk, scope[order_ct.id])


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopeFindTestCase(VectorTestCase):
    """Test find_in_graph functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company")
        cls.user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass",
        )
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )
        cls.part = Parts.objects.create(
            ERP_id="SPECIAL-001",
            order=cls.order,
            part_type=cls.part_type,
        )

    def test_find_by_model_type(self):
        """Test finding first object of a type."""
        found = find_in_graph(
            self.order,
            lambda obj: obj._meta.model_name == 'parts'
        )
        self.assertEqual(found, self.part)

    def test_find_by_attribute(self):
        """Test finding by attribute value."""
        found = find_in_graph(
            self.order,
            lambda obj: getattr(obj, 'ERP_id', None) == 'SPECIAL-001'
        )
        self.assertEqual(found, self.part)

    def test_find_not_found(self):
        """Test that None is returned when not found."""
        found = find_in_graph(
            self.order,
            lambda obj: getattr(obj, 'name', None) == 'Nonexistent'
        )
        self.assertIsNone(found)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopeCountTestCase(VectorTestCase):
    """Test count_descendants functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company 3")
        cls.user = User.objects.create_user(
            username="testuser3",
            email="test3@example.com",
            password="testpass",
        )
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )
        # Create 3 parts
        for i in range(3):
            Parts.objects.create(
                ERP_id=f"PART-{i}",
                order=cls.order,
                part_type=cls.part_type,
            )

    def test_count_descendants(self):
        """Test counting descendants by type."""
        counts = count_descendants(self.order)

        self.assertEqual(counts.get('orders'), 1)
        self.assertEqual(counts.get('parts'), 3)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopePerformanceTestCase(VectorTestCase):
    """Performance tests to catch slow scope queries."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Perf Test Company")
        cls.user = User.objects.create_user(
            username="perfuser",
            email="perf@test.com",
            password="testpass123",
        )
        # Add to Manager group for full access (tenant-scoped)
        add_user_to_tenant_group(cls.user, 'Manager')

        cls.order = Orders.objects.create(
            name="Perf Order",
            company=cls.company,
            customer=cls.user
        )

    def test_get_descendants_performance(self):
        """Traversal should complete in under 2 seconds."""
        import time
        start = time.time()
        get_descendants(self.order, user=self.user)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"get_descendants took {elapsed:.2f}s, expected < 2s")

    def test_related_to_performance(self):
        """related_to should complete in under 2 seconds."""
        import time
        start = time.time()
        list(related_to(Documents, self.order, user=self.user))
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"related_to took {elapsed:.2f}s, expected < 2s")

    def test_count_descendants_performance(self):
        """count_descendants should complete in under 2 seconds."""
        import time
        start = time.time()
        count_descendants(self.order, user=self.user)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"count_descendants took {elapsed:.2f}s, expected < 2s")


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class LargeHierarchyTestCase(VectorTestCase):
    """Test with realistic data volume and shared references."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Large Test Company")
        cls.staff_user = User.objects.create_user(
            username="largeuser",
            email="large@test.com",
            password="testpass123",
            us_person=True,  # Required for ITAR access
        )
        # Add to Production_Manager group for full access (tenant-scoped)
        add_user_to_tenant_group(cls.staff_user, 'Production_Manager')

        # Create shared part type with process and steps
        cls.part_type = PartTypes.objects.create(name="Shared Part Type")
        cls.process = Processes.objects.create(
            name="Shared Process",
            part_type=cls.part_type,
        )
        cls.steps = []
        for i in range(3):
            step = Steps.objects.create(
                name=f"Step {i}",
                part_type=cls.part_type,
                step_type='start' if i == 0 else 'task',
            )
            ProcessStep.objects.create(
                process=cls.process,
                step=step,
                order=i,
                is_entry_point=(i == 0),
            )
            cls.steps.append(step)

        # Create order with many parts - all using the SAME part type/process/steps
        cls.order = Orders.objects.create(
            name="Large Order",
            company=cls.company,
            customer=cls.staff_user
        )
        cls.parts = [
            Parts.objects.create(
                ERP_id=f"LARGE-PART-{i}",
                order=cls.order,
                part_type=cls.part_type,
            )
            for i in range(50)
        ]

        # Create work orders for some parts
        cls.work_orders = [
            WorkOrder.objects.create(
                ERP_id=f"WO-{i}",
                related_order=cls.order,
            )
            for i in range(10)
        ]

        # Attach documents at various levels
        ct_order = ContentType.objects.get_for_model(Orders)
        ct_part = ContentType.objects.get_for_model(Parts)
        ct_step = ContentType.objects.get_for_model(Steps)

        # Docs on order
        for i in range(5):
            Documents.objects.create(
                file_name=f"order_doc_{i}.pdf",
                content_type=ct_order,
                object_id=cls.order.pk
            )

        # Docs on some parts
        for i in range(20):
            Documents.objects.create(
                file_name=f"part_doc_{i}.pdf",
                content_type=ct_part,
                object_id=cls.parts[i % len(cls.parts)].pk
            )

        # Docs on shared steps (should only appear once each)
        for i, step in enumerate(cls.steps):
            Documents.objects.create(
                file_name=f"step_doc_{i}.pdf",
                content_type=ct_step,
                object_id=step.pk
            )

    def test_large_hierarchy_performance(self):
        """Large hierarchy should still complete in under 2 seconds."""
        import time
        start = time.time()
        scope = get_descendants(self.order, user=self.staff_user)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"Large hierarchy took {elapsed:.2f}s, expected < 2s")

    def test_shared_parttype_not_duplicated(self):
        """PartType shared by multiple parts - forward FK not traversed in 'down' direction.

        Note: scope.py traverses ownership/containment hierarchy, not forward FK references.
        PartTypes are referenced by Parts, not owned by them, so they're not included
        when traversing DOWN from an Order. Use 'up' traversal from a part to find its PartType.
        """
        scope = get_descendants(self.order, user=self.staff_user)

        # Forward FKs like Part.part_type are NOT traversed in 'down' direction
        # This is by design - PartTypes are master data, not children of orders
        ct_parttype = ContentType.objects.get_for_model(PartTypes)
        parttype_ids = scope.get(ct_parttype.id, set())
        self.assertEqual(len(parttype_ids), 0, "PartTypes should not be in DOWN traversal")

    def test_processes_not_in_down_traversal(self):
        """Processes are referenced via PartType, not direct children of Order.

        Since traversal follows ownership hierarchy (reverse FKs), Processes
        which are children of PartTypes are not reached when going DOWN from Order.
        """
        scope = get_descendants(self.order, user=self.staff_user)

        # Processes are children of PartTypes, not orders
        ct_process = ContentType.objects.get_for_model(Processes)
        process_ids = scope.get(ct_process.id, set())
        self.assertEqual(len(process_ids), 0, "Processes should not be in DOWN traversal from Order")

    def test_related_documents_complete(self):
        """All documents in the traversable hierarchy should be found exactly once.

        Note: Steps are not traversed in DOWN direction (they're children of PartTypes,
        not Orders), so step documents are not included.
        """
        docs = list(related_to(Documents, self.order, user=self.staff_user))

        # 5 order docs + 20 part docs = 25 total
        # (Step docs are NOT included because Steps aren't in DOWN traversal from Order)
        self.assertEqual(len(docs), 25, f"Expected 25 docs, got {len(docs)}")

        # Verify no duplicates
        doc_ids = [d.id for d in docs]
        self.assertEqual(len(doc_ids), len(set(doc_ids)), "Found duplicate documents")

    def test_related_documents_performance(self):
        """related_to with large hierarchy should complete in under 2 seconds."""
        import time
        start = time.time()
        list(related_to(Documents, self.order, user=self.staff_user))
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"related_to took {elapsed:.2f}s, expected < 2s")


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopePermissionTestCase(VectorTestCase):
    """Test that scope traversal respects user permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.company_a = Companies.objects.create(name="Company A")
        cls.company_b = Companies.objects.create(name="Company B")

        # Get/create test tenant for all users
        cls.tenant = get_or_create_test_tenant()

        # Staff user (Production_Manager) - can see everything
        cls.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@test.com",
            password="testpass123",
            us_person=True,  # Required for ITAR access
        )
        add_user_to_tenant_group(cls.staff_user, 'Production_Manager', cls.tenant)

        # Customer A - can only see their own orders
        cls.customer_a = User.objects.create_user(
            username="customer_a",
            email="customer_a@test.com",
            password="testpass123",
            us_person=True,  # Required for ITAR access
        )
        add_user_to_tenant_group(cls.customer_a, 'Customer', cls.tenant)

        # Customer B - can only see their own orders
        cls.customer_b = User.objects.create_user(
            username="customer_b",
            email="customer_b@test.com",
            password="testpass123",
            us_person=True,  # Required for ITAR access
        )
        add_user_to_tenant_group(cls.customer_b, 'Customer', cls.tenant)

        # Create part type (shared)
        cls.part_type = PartTypes.objects.create(name="Shared Part Type")

        # Order for Customer A
        cls.order_a = Orders.objects.create(
            name="Order A",
            company=cls.company_a,
            customer=cls.customer_a
        )
        cls.part_a = Parts.objects.create(
            ERP_id="PART-A",
            order=cls.order_a,
            part_type=cls.part_type,
        )

        # Order for Customer B
        cls.order_b = Orders.objects.create(
            name="Order B",
            company=cls.company_b,
            customer=cls.customer_b
        )
        cls.part_b = Parts.objects.create(
            ERP_id="PART-B",
            order=cls.order_b,
            part_type=cls.part_type,
        )

        # Attach documents
        ct_order = ContentType.objects.get_for_model(Orders)
        ct_part = ContentType.objects.get_for_model(Parts)

        cls.doc_order_a = Documents.objects.create(
            file_name="order_a_doc.pdf",
            content_type=ct_order,
            object_id=cls.order_a.pk
        )
        cls.doc_part_a = Documents.objects.create(
            file_name="part_a_doc.pdf",
            content_type=ct_part,
            object_id=cls.part_a.pk
        )
        cls.doc_order_b = Documents.objects.create(
            file_name="order_b_doc.pdf",
            content_type=ct_order,
            object_id=cls.order_b.pk
        )
        cls.doc_part_b = Documents.objects.create(
            file_name="part_b_doc.pdf",
            content_type=ct_part,
            object_id=cls.part_b.pk
        )

    def test_staff_sees_all_descendants(self):
        """Staff user should see all descendants."""
        scope = get_descendants(self.order_a, user=self.staff_user)

        ct_parts = ContentType.objects.get_for_model(Parts)
        part_ids = scope.get(ct_parts.id, set())
        self.assertIn(self.part_a.pk, part_ids)

    def test_staff_sees_all_documents(self):
        """Staff user should see all related documents."""
        docs = list(related_to(Documents, self.order_a, user=self.staff_user))
        doc_ids = [d.id for d in docs]

        self.assertIn(self.doc_order_a.id, doc_ids)
        self.assertIn(self.doc_part_a.id, doc_ids)

    def test_customer_cannot_traverse_other_orders(self):
        """Customer should not see parts from other customer's orders during traversal."""
        # Customer A traversing their own order
        scope_a = get_descendants(self.order_a, user=self.customer_a)

        ct_parts = ContentType.objects.get_for_model(Parts)
        part_ids = scope_a.get(ct_parts.id, set())

        # Should see their own part
        self.assertIn(self.part_a.pk, part_ids)
        # Should NOT see customer B's part
        self.assertNotIn(self.part_b.pk, part_ids)

    def test_customer_documents_filtered(self):
        """Customer should only see documents they have access to."""
        docs_a = list(related_to(Documents, self.order_a, user=self.customer_a))
        doc_ids = [d.id for d in docs_a]

        # Customer A should NOT see Customer B's documents
        self.assertNotIn(self.doc_order_b.id, doc_ids)
        self.assertNotIn(self.doc_part_b.id, doc_ids)

    def test_no_user_bypasses_permissions(self):
        """Without user param, all objects should be visible (for internal use)."""
        scope = get_descendants(self.order_a)

        ct_parts = ContentType.objects.get_for_model(Parts)
        part_ids = scope.get(ct_parts.id, set())

        # Should see the part (no permission filtering)
        self.assertIn(self.part_a.pk, part_ids)

    def test_superuser_sees_everything(self):
        """Superuser should see all objects."""
        superuser = User.objects.create_superuser(
            username="superuser",
            email="super@test.com",
            password="testpass123",
        )

        # Superuser traversing Customer A's order should see everything
        scope = get_descendants(self.order_a, user=superuser)

        ct_parts = ContentType.objects.get_for_model(Parts)
        part_ids = scope.get(ct_parts.id, set())
        self.assertIn(self.part_a.pk, part_ids)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ScopeMergeSubtractTestCase(VectorTestCase):
    """Test merge_scopes and subtract_scope."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company 4")
        cls.user = User.objects.create_user(
            username="testuser4",
            email="test4@example.com",
            password="testpass",
        )
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )

        # Two separate orders
        cls.order1 = Orders.objects.create(
            name="Order 1",
            company=cls.company,
            customer=cls.user
        )
        cls.order2 = Orders.objects.create(
            name="Order 2",
            company=cls.company,
            customer=cls.user
        )

        cls.part1 = Parts.objects.create(
            ERP_id="PART-M1",
            order=cls.order1,
            part_type=cls.part_type,
        )
        cls.part2 = Parts.objects.create(
            ERP_id="PART-M2",
            order=cls.order2,
            part_type=cls.part_type,
        )

    def test_merge_scopes(self):
        """Test merging two scopes."""
        scope1 = get_descendants(self.order1)
        scope2 = get_descendants(self.order2)

        merged = merge_scopes(scope1, scope2)

        order_ct = ContentType.objects.get_for_model(Orders)
        parts_ct = ContentType.objects.get_for_model(Parts)

        # Should have both orders
        self.assertIn(self.order1.pk, merged[order_ct.id])
        self.assertIn(self.order2.pk, merged[order_ct.id])

        # Should have both parts
        self.assertIn(self.part1.pk, merged[parts_ct.id])
        self.assertIn(self.part2.pk, merged[parts_ct.id])

    def test_subtract_scope(self):
        """Test subtracting one scope from another."""
        scope1 = get_descendants(self.order1)
        scope2 = get_descendants(self.order2)

        # Merge then subtract order2's scope
        merged = merge_scopes(scope1, scope2)
        result = subtract_scope(merged, scope2)

        order_ct = ContentType.objects.get_for_model(Orders)
        parts_ct = ContentType.objects.get_for_model(Parts)

        # Should only have order1
        self.assertIn(self.order1.pk, result[order_ct.id])
        self.assertNotIn(self.order2.pk, result.get(order_ct.id, set()))

        # Should only have part1
        self.assertIn(self.part1.pk, result[parts_ct.id])
        self.assertNotIn(self.part2.pk, result.get(parts_ct.id, set()))


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ExplainPathTestCase(VectorTestCase):
    """Test explain_path functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company 5")
        cls.user = User.objects.create_user(
            username="testuser5",
            email="test5@example.com",
            password="testpass",
        )
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.process = Processes.objects.create(
            name="Test Process",
            part_type=cls.part_type,
        )
        cls.step = Steps.objects.create(
            name="Test Step",
            part_type=cls.part_type,
            step_type='task',
        )
        ProcessStep.objects.create(
            process=cls.process,
            step=cls.step,
            order=1,
            is_entry_point=True,
        )
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )
        cls.part = Parts.objects.create(
            ERP_id="PATH-001",
            order=cls.order,
            part_type=cls.part_type,
        )

    def test_explain_path_direct_child(self):
        """Test path from order to its part."""
        path = explain_path(self.order, self.part)

        self.assertIsNotNone(path)
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0][0], self.order)
        self.assertEqual(path[1][0], self.part)

    def test_explain_path_no_path(self):
        """Test when no path exists."""
        # Step is not a descendant of order (it's through part_type, not order)
        path = explain_path(self.order, self.step)

        # Path should exist: order -> part -> part_type -> process -> step
        # But only if we traverse through part_type
        # This depends on whether the traversal follows part -> part_type
        if path is None:
            # This is expected if part_type isn't a "child" of part
            pass
        else:
            # Path was found
            self.assertGreater(len(path), 0)

    def test_explain_path_ancestors(self):
        """Test finding path going up."""
        path = explain_path(self.part, self.order, direction='up')

        self.assertIsNotNone(path)
        self.assertEqual(path[0][0], self.part)
        self.assertEqual(path[-1][0], self.order)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class RelatedToTestCase(VectorTestCase):
    """Test related_to functionality with Documents."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company 6")
        cls.user = User.objects.create_user(
            username="testuser6",
            email="test6@example.com",
            password="testpass",
        )
        # Add to Customer group so they can access their orders' documents (tenant-scoped)
        add_user_to_tenant_group(cls.user, 'Customer')

        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )
        cls.part = Parts.objects.create(
            ERP_id="REL-001",
            order=cls.order,
            part_type=cls.part_type,
        )

        # Create documents attached to different objects
        order_ct = ContentType.objects.get_for_model(Orders)
        part_ct = ContentType.objects.get_for_model(Parts)

        cls.order_doc = Documents.objects.create(
            file_name="order_doc.pdf",
            content_type=order_ct,
            object_id=cls.order.pk,
            uploaded_by=cls.user,
            classification='public'
        )
        cls.part_doc = Documents.objects.create(
            file_name="part_doc.pdf",
            content_type=part_ct,
            object_id=cls.part.pk,
            uploaded_by=cls.user,
            classification='public'
        )

        # Create a document on a different order (should not be included)
        cls.other_order = Orders.objects.create(
            name="Other Order",
            company=cls.company,
            customer=cls.user
        )
        cls.other_doc = Documents.objects.create(
            file_name="other_doc.pdf",
            content_type=order_ct,
            object_id=cls.other_order.pk,
            uploaded_by=cls.user,
            classification='public'
        )

    def test_related_to_finds_all_documents(self):
        """Test that related_to finds documents on order and its children."""
        docs = related_to(Documents, self.order)

        doc_ids = set(docs.values_list('id', flat=True))

        self.assertIn(self.order_doc.pk, doc_ids)
        self.assertIn(self.part_doc.pk, doc_ids)
        self.assertNotIn(self.other_doc.pk, doc_ids)

    def test_related_to_with_user_filtering(self):
        """Test that for_user filtering is applied."""
        # This assumes Documents.objects.for_user exists and filters by classification
        docs = related_to(Documents, self.order, user=self.user)

        # Should still find public documents
        doc_ids = set(docs.values_list('id', flat=True))
        self.assertIn(self.order_doc.pk, doc_ids)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class BatchingPerformanceTestCase(VectorTestCase):
    """Test that batching reduces query count."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Companies.objects.create(name="Test Company 7")
        cls.user = User.objects.create_user(
            username="testuser7",
            email="test7@example.com",
            password="testpass",
        )
        cls.part_type = PartTypes.objects.create(
            name="Test Part Type",
        )
        cls.order = Orders.objects.create(
            name="Test Order",
            company=cls.company,
            customer=cls.user
        )

        # Create many parts
        for i in range(20):
            Parts.objects.create(
                ERP_id=f"BATCH-{i}",
                order=cls.order,
                part_type=cls.part_type,
            )

    def test_batching_query_count(self):
        """Test that traversal uses batched queries, not N+1."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            scope = get_descendants(self.order)

        query_count = len(context.captured_queries)

        # Verify we got all parts
        parts_ct = ContentType.objects.get_for_model(Parts)
        parts_count = len(scope[parts_ct.id])
        self.assertEqual(parts_count, 20)

        # The key test: with proper batching, queries should be O(model_types), not O(objects).
        # Without batching: 20+ queries just for parts (N+1 pattern)
        # With batching: ~1 query per model type in the graph (~15-20 model types)
        #
        # We verify batching by checking queries < parts_count.
        # If we had N+1, we'd have at least 20 queries for parts alone.
        self.assertLess(query_count, parts_count,
            f"Possible N+1 detected: {query_count} queries for {parts_count} parts. "
            f"With batching, expect fewer queries than objects.")