"""Unit tests for erlang_c.py — run with:  python -m unittest test_erlang_c.py"""

import math
import unittest

from erlang_c import (asa, erlang_b, erlang_c, occupancy, required_agents,
                      service_level, staffing_table, traffic_intensity)


class TestErlangC(unittest.TestCase):
    # Reference case: 100 calls / 30 min, AHT 180 s -> 10 Erlangs
    A = traffic_intensity(100, 180, 1800)

    def test_traffic_intensity(self):
        self.assertAlmostEqual(self.A, 10.0)

    def test_erlang_b_known_value(self):
        # Erlang B(10 servers, 10 Erlangs) = 0.2146 (standard table value)
        self.assertAlmostEqual(erlang_b(10, 10.0), 0.2146, places=4)

    def test_erlang_c_bounds(self):
        self.assertEqual(erlang_c(10, 10.0), 1.0)          # unstable queue
        self.assertTrue(0 < erlang_c(14, 10.0) < 1)

    def test_more_agents_improves_service(self):
        sls = [service_level(n, self.A, 180, 20) for n in range(11, 20)]
        asas = [asa(n, self.A, 180) for n in range(11, 20)]
        self.assertEqual(sls, sorted(sls))
        self.assertEqual(asas, sorted(asas, reverse=True))

    def test_understaffed(self):
        self.assertEqual(service_level(9, self.A, 180, 20), 0.0)
        self.assertTrue(math.isinf(asa(10, self.A, 180)))

    def test_required_agents_80_20(self):
        r = required_agents(100, 180, 1800, target_sl=0.80, threshold=20)
        self.assertEqual(r["agents"], 14)
        self.assertGreaterEqual(r["service_level"], 0.80)
        # one fewer agent must miss the target
        self.assertLess(service_level(13, self.A, 180, 20), 0.80)

    def test_shrinkage(self):
        r = required_agents(100, 180, 1800, target_sl=0.80, threshold=20, shrinkage=0.30)
        self.assertEqual(r["scheduled_fte"], math.ceil(14 / 0.70))  # 20

    def test_occupancy_cap_adds_agents(self):
        base = required_agents(100, 180, 1800, 0.80, 20)["agents"]
        capped = required_agents(100, 180, 1800, 0.80, 20, max_occupancy=0.65)["agents"]
        self.assertGreaterEqual(capped, base)
        self.assertLessEqual(occupancy(capped, self.A), 0.65)

    def test_asa_target(self):
        r = required_agents(100, 180, 1800, 0.80, 20, target_asa=5)
        self.assertLessEqual(r["asa_seconds"], 5)

    def test_zero_calls(self):
        r = required_agents(0, 180, 1800)
        self.assertEqual(r["agents"], 0)
        self.assertEqual(r["scheduled_fte"], 0)

    def test_staffing_table(self):
        rows = staffing_table(100, 180, 1800, 20, extra=5)
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["agents"], 11)


if __name__ == "__main__":
    unittest.main()
