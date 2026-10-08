"""Scheduling a reman core to its resolved rebuild scope, not the nominal route.

Before this, the solver booked every operation on a core's nominal route. A core under
rebuild already knows better — `reman.scope` resolves which operations its rebuild
needs — so the plan reserved capacity for work `skip_out_of_scope` would mark SKIPPED
at runtime, inflating reman load and makespan.

The subtlety worth testing is precedence. A scoped-out operation sits BETWEEN two kept
ones, so dropping it along with its edges would leave the survivors unordered and free
to float to time zero. The route bridges across dropped nodes instead.

These are pure-graph tests: no ORM, matching `routing.py` itself.
"""
from dataclasses import dataclass
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from Tracker.services.scheduling.routing import resolve_route


@dataclass(frozen=True)
class _Node:
    step_id: object
    is_terminal: bool = False
    order: int = 0


@dataclass(frozen=True)
class _Edge:
    from_step_id: object
    to_step_id: object
    edge_type: str = "DEFAULT"


def _line(*names, terminal_last=True):
    """A simple A→B→C… chain, optionally ending in a terminal node."""
    nodes, edges = [], []
    for i, nm in enumerate(names):
        last = i == len(names) - 1
        nodes.append(_Node(nm, is_terminal=bool(terminal_last and last), order=i + 1))
        if i:
            edges.append(_Edge(names[i - 1], nm))
    return nodes, edges


class ScopedRouteTests(SimpleTestCase):
    def test_without_a_scope_the_route_is_unchanged(self):
        """The regression guard: every ordinary part must schedule exactly as before."""
        nodes, edges = _line("A", "B", "C", "Z")
        self.assertEqual(resolve_route("A", nodes, edges),
                         (["A", "B", "C"], [("A", "B"), ("B", "C")]))

    def test_a_scope_drops_the_operations_it_excludes(self):
        nodes, edges = _line("A", "B", "C", "Z")
        route, _ = resolve_route("A", nodes, edges, keep_step_ids={"A", "C"})
        self.assertEqual(route, ["A", "C"])

    def test_precedence_bridges_across_a_dropped_operation(self):
        """A→B→C with B scoped out must still order A before C."""
        nodes, edges = _line("A", "B", "C", "Z")
        _, prec = resolve_route("A", nodes, edges, keep_step_ids={"A", "C"})
        self.assertEqual(prec, [("A", "C")])

    def test_precedence_bridges_across_several_consecutive_dropped_operations(self):
        nodes, edges = _line("A", "B", "C", "D", "Z")
        route, prec = resolve_route("A", nodes, edges, keep_step_ids={"A", "D"})
        self.assertEqual(route, ["A", "D"])
        self.assertEqual(prec, [("A", "D")])

    def test_the_current_step_is_kept_even_when_the_scope_omits_it(self):
        """The unit is physically at that step; the plan cannot pretend otherwise."""
        nodes, edges = _line("A", "B", "C", "Z")
        route, _ = resolve_route("A", nodes, edges, keep_step_ids={"C"})
        self.assertEqual(route, ["A", "C"])

    def test_a_scope_covering_everything_matches_the_nominal_route(self):
        nodes, edges = _line("A", "B", "C", "Z")
        self.assertEqual(resolve_route("A", nodes, edges, keep_step_ids={"A", "B", "C"}),
                         resolve_route("A", nodes, edges))

    def test_an_empty_scope_leaves_only_the_current_step(self):
        nodes, edges = _line("A", "B", "C", "Z")
        route, prec = resolve_route("A", nodes, edges, keep_step_ids=set())
        self.assertEqual((route, prec), (["A"], []))

    def test_scope_ids_as_strings_match_a_uuid_graph(self):
        """`reman.scope` returns `step_id` as a str while the graph carries UUIDs.

        Compared directly the sets barely intersect and the route silently collapses to
        the current step — an under-booked plan that looks like a successful solve. This
        is the same string-vs-UUID trap as the bulk part actions.
        """
        a, b, c, z = uuid4(), uuid4(), uuid4(), uuid4()
        nodes, edges = _line(a, b, c, z)
        route, prec = resolve_route(a, nodes, edges, keep_step_ids={str(a), str(c)})
        self.assertEqual(route, [a, c], "string scope ids must match UUID graph nodes")
        self.assertEqual(prec, [(a, c)])

    def test_uuid_scope_ids_also_match(self):
        a, b, c, z = uuid4(), uuid4(), uuid4(), uuid4()
        nodes, edges = _line(a, b, c, z)
        route, _ = resolve_route(a, nodes, edges, keep_step_ids={a, c})
        self.assertEqual(route, [a, c])

    def test_scope_applies_to_the_linear_fallback_too(self):
        """A process with no DEFAULT edges is ordered by ProcessStep.order."""
        nodes, _ = _line("A", "B", "C", "Z")
        route, prec = resolve_route("A", nodes, [], keep_step_ids={"A", "C"})
        self.assertEqual(route, ["A", "C"])
        self.assertEqual(prec, [("A", "C")])

    def test_a_merge_keeps_both_predecessors_when_both_are_in_scope(self):
        """Convergence must survive scoping: M waits for BOTH branches.

        A diamond, because precedence only covers steps this unit actually reaches —
        a sibling predecessor that is not forward-reachable from the current step
        belongs to another unit's path and is correctly absent.
        """
        nodes = [_Node("S", order=1), _Node("L", order=2), _Node("R", order=3),
                 _Node("M", order=4), _Node("Z", is_terminal=True, order=5)]
        edges = [_Edge("S", "L"), _Edge("S", "R"),
                 _Edge("L", "M"), _Edge("R", "M"), _Edge("M", "Z")]
        _, prec = resolve_route("S", nodes, edges, keep_step_ids={"S", "L", "R", "M"})
        self.assertIn(("L", "M"), prec)
        self.assertIn(("R", "M"), prec)

    def test_a_merge_bridges_when_one_branch_is_scoped_out(self):
        """With the left branch dropped, M must still wait for S via that path."""
        nodes = [_Node("S", order=1), _Node("L", order=2), _Node("R", order=3),
                 _Node("M", order=4), _Node("Z", is_terminal=True, order=5)]
        edges = [_Edge("S", "L"), _Edge("S", "R"),
                 _Edge("L", "M"), _Edge("R", "M"), _Edge("M", "Z")]
        route, prec = resolve_route("S", nodes, edges, keep_step_ids={"S", "R", "M"})
        self.assertNotIn("L", route)
        self.assertIn(("R", "M"), prec)
        self.assertIn(("S", "M"), prec, "the dropped branch still orders S before M")

    def test_bridging_does_not_duplicate_an_edge(self):
        nodes, edges = _line("A", "B", "C", "Z")
        _, prec = resolve_route("A", nodes, edges, keep_step_ids={"A", "B", "C"})
        self.assertEqual(len(prec), len(set(prec)))
