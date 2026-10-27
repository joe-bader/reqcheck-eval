import unittest

from eval import thresholds as T


class TestThresholdMetrics(unittest.TestCase):
    def test_average_precision(self):
        self.assertEqual(T.average_precision([(0.9, True), (0.8, True), (0.1, False)]), 1.0)  # perfect ranking
        self.assertEqual(T.average_precision([(0.9, False), (0.8, True)]), 0.5)  # gold item ranked second
        self.assertIsNone(T.average_precision([(0.9, False)]))  # nothing to find

    def test_brier(self):
        self.assertEqual(T.brier([(1, True), (0, False)]), 0.0)
        self.assertEqual(T.brier([(0.5, True), (0.5, False)]), 0.25)

    def test_predicted_threshold_is_inclusive(self):
        probs = [{"req_id": "A", "AMB": 0.5, "UNT": 0.49, "GAP": 0.9}]
        self.assertEqual(T.predicted(probs, 0.5), {("A", "AMB"), ("A", "GAP")})


if __name__ == "__main__":
    unittest.main()
