"""Unit tests for the pure route resolver (no DB / no solver).

Covers: linear fallback, DEFAULT-only walk (rework/scrap excluded), merge diamonds,
current-step anchoring, off-graph/unstarted parts, terminal handling, cycle guard.
"""
from django.test import SimpleTestCase

from Tracker.services.scheduling.data import EdgeData, StepNode
from Tracker.services.scheduling.routing import resolve_route


def _n(sid, order, terminal=False):
    return StepNode(step_id=sid, is_terminal=terminal,
                    requires_first_piece_inspection=False, order=order)


def _e(a, b, kind='DEFAULT'):
    return EdgeData(from_step_id=a, to_step_id=b, edge_type=kind)


class RouteResolverTests(SimpleTestCase):
    def test_linear_fallback_no_edges(self):
        nodes = [_n('a', 1), _n('b', 2), _n('c', 3)]
        route, prec = resolve_route('a', nodes, [])
        self.assertEqual(route, ['a', 'b', 'c'])
        self.assertEqual(prec, [('a', 'b'), ('b', 'c')])

    def test_fallback_starts_from_current_step(self):
        # A part on step b only schedules b, c — not the completed a.
        nodes = [_n('a', 1), _n('b', 2), _n('c', 3)]
        route, prec = resolve_route('b', nodes, [])
        self.assertEqual(route, ['b', 'c'])
        self.assertEqual(prec, [('b', 'c')])

    def test_fallback_drops_terminal_node(self):
        nodes = [_n('a', 1), _n('b', 2), _n('done', 3, terminal=True)]
        route, _ = resolve_route('a', nodes, [])
        self.assertEqual(route, ['a', 'b'])

    def test_default_walk_excludes_rework_and_scrap(self):
        # a -DEFAULT-> b -DEFAULT-> done; b -ALTERNATE-> rework; b -ALTERNATE-> scrap.
        nodes = [_n('a', 1), _n('b', 2), _n('rework', 3),
                 _n('scrap', 4, terminal=True), _n('done', 5, terminal=True)]
        edges = [_e('a', 'b'), _e('b', 'done'),
                 _e('b', 'rework', 'ALTERNATE'), _e('b', 'scrap', 'ALTERNATE')]
        route, prec = resolve_route('a', nodes, edges)
        self.assertEqual(set(route), {'a', 'b'}, "only the nominal (DEFAULT) spine")
        self.assertNotIn('rework', route)
        self.assertNotIn('scrap', route)
        self.assertIn(('a', 'b'), prec)

    def test_merge_diamond_keeps_both_predecessors(self):
        # a -> b, a -> c, b -> d, c -> d (all DEFAULT). d must wait on both b and c.
        nodes = [_n('a', 1), _n('b', 2), _n('c', 3), _n('d', 4)]
        edges = [_e('a', 'b'), _e('a', 'c'), _e('b', 'd'), _e('c', 'd')]
        route, prec = resolve_route('a', nodes, edges)
        self.assertEqual(set(route), {'a', 'b', 'c', 'd'})
        self.assertIn(('b', 'd'), prec)
        self.assertIn(('c', 'd'), prec)

    def test_unstarted_part_starts_from_lowest_order(self):
        nodes = [_n('a', 1), _n('b', 2)]
        route, _ = resolve_route(None, nodes, [])
        self.assertEqual(route, ['a', 'b'])

    def test_off_graph_current_step_falls_back_to_entry(self):
        nodes = [_n('a', 1), _n('b', 2)]
        route, _ = resolve_route('ghost', nodes, [])
        self.assertEqual(route, ['a', 'b'])

    def test_cycle_guard_terminates(self):
        # A stray DEFAULT back-edge b -> a must not loop forever.
        nodes = [_n('a', 1), _n('b', 2)]
        edges = [_e('a', 'b'), _e('b', 'a')]
        route, _ = resolve_route('a', nodes, edges)
        self.assertEqual(set(route), {'a', 'b'})

    def test_empty_graph(self):
        self.assertEqual(resolve_route('a', [], []), ([], []))
