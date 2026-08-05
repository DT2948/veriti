import unittest

from benchmarking.statistics import grouped_summary, percentile, summarize_samples


class StatisticsTests(unittest.TestCase):
    def test_percentiles_and_even_odd_medians(self):
        self.assertIsNone(percentile([], 95))
        self.assertEqual(percentile([7], 95), 7.0)
        self.assertEqual(summarize_samples([{"duration_ms": n, "success": True} for n in [1, 2, 3]])["median_ms"], 2.0)
        self.assertEqual(summarize_samples([{"duration_ms": n, "success": True} for n in [1, 2, 3, 4]])["median_ms"], 2.5)
        self.assertAlmostEqual(percentile([1, 2, 3, 4, 5], 95), 4.8)

    def test_rates_and_grouping(self):
        summary = summarize_samples([
            {"duration_ms": 1, "success": True},
            {"duration_ms": 2, "success": False},
            {"duration_ms": 3, "success": True},
        ])
        self.assertAlmostEqual(summary["success_rate"], 2 / 3)
        self.assertAlmostEqual(summary["failure_rate"], 1 / 3)
        groups = grouped_summary(
            [{"group": "a", "duration_ms": 1}, {"group": "a", "duration_ms": 3}],
            ("group",),
        )
        self.assertEqual(groups["a"]["median_ms"], 2.0)


if __name__ == "__main__":
    unittest.main()
