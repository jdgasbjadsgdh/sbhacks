"""Deferred early-reentry behavior with synthetic connection lifecycles."""
import unittest
from loading_probe_logic import LoadingControl
from test_loading_port import context


class RushReentryTests(unittest.TestCase):
    def held(self, zone='sc_boss'):
        p = LoadingControl()
        self.assertTrue(p.arm(context(), 'rush'))
        self.assertTrue(p.suppress(context(zone=zone), 11))
        p.frame(context(zone=zone))
        self.assertEqual(p.pending['action'], 'rush_retry')
        return p

    def test_any_boss_and_early_recovery(self):
        for zone in ('sc_boss', 'forest_boss', 'ice_boss', 'cave_boss', 'jungle_boss', 'hulk_boss', 'dino_boss', 'temple_boss'):
            p = self.held(zone)
            self.assertIsNone(p.take_action(context(), 999, True))
            self.assertEqual(p.take_action(context(), 123, True), 'reconnect')
            self.assertEqual(p.state, 'waiting')
            c = context(socket=10)
            self.assertTrue(p.suppress(c, 22))
            p.frame(c)
            self.assertIsNone(p.pending)
            self.assertTrue(p.preview(c))
            self.assertEqual(p.take_action(c, 123, True), 'asset')
            self.assertTrue(p.suppress(c, 11))
            p.frame(c)
            self.assertIsNone(p.pending)

    def test_fallback_does_not_loop(self):
        p = self.held()
        self.assertEqual(p.take_action(context(), 123, True), 'reconnect')
        for sock in range(10, 14):
            c = context(socket=sock)
            self.assertTrue(p.suppress(c, 11))
            p.frame(c)
            self.assertIsNone(p.pending)

    def test_manual_finish_cancel_and_stale_callbacks(self):
        for cancel in (False, True):
            p = self.held()
            if cancel:
                p.cancel(context())
            else:
                self.assertTrue(p.finish(context()))
            self.assertEqual(p.pending['action'], 'reconnect')
            self.assertEqual(p.take_action(context(), 123, True), 'reconnect')
            self.assertTrue(p.suppress(context(), 11))
            self.assertFalse(p.suppress(context(socket=10), 11))
        for c in (context(2), context(socket=10), context(player=True), context(state=4), None):
            p = self.held()
            self.assertIsNone(p.take_action(c, 123, True))
        p = self.held()
        self.assertIsNone(p.take_action(context(), 123, False))


if __name__ == '__main__':
    unittest.main()
