import json
import os
import tempfile
import unittest

from eval import score as S

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "fake_labels.json")


class TestPRF(unittest.TestCase):
    def test_hand_computed(self):
        p, r, f1 = S.prf(tp=2, fp=2, fn=1)
        self.assertAlmostEqual(p, 0.5)
        self.assertAlmostEqual(r, 2 / 3)
        self.assertAlmostEqual(f1, 4 / 7)  # 2*0.5*(2/3)/(0.5+2/3)

    def test_empty_denominators_are_none(self):
        self.assertEqual(S.prf(0, 0, 0), (None, None, None))
        self.assertEqual(S.prf(0, 0, 3), (None, 0.0, 0.0))  # flagged nothing, missed 3: F1 is 0, not n/a
        self.assertEqual(S.prf(0, 3, 0), (0.0, None, 0.0))  # flagged 3, none real, nothing to find

    def test_zero_tp_gives_zero_f1(self):
        self.assertEqual(S.prf(0, 2, 2), (0.0, 0.0, 0.0))


class TestScore(unittest.TestCase):
    def setUp(self):
        self.truth = S.load_truth(FIX)  # gold: T-1 AMB, T-2 UNT+GAP, T-4 GAP

    def test_perfect(self):
        pred = {("T-1", "AMB"), ("T-2", "UNT"), ("T-2", "GAP"), ("T-4", "GAP")}
        m = S.score(self.truth, pred)
        self.assertEqual((m["overall"]["fp"], m["overall"]["fn"]), (0, 0))
        self.assertEqual(m["overall"]["f1"], 1.0)

    def test_mixed_overall_and_per_category(self):
        pred = {("T-1", "AMB"),   # TP
                ("T-1", "UNT"),   # FP: right req, wrong category earns nothing
                ("T-2", "GAP"),   # TP
                ("T-3", "AMB")}   # FP: req is clean
        m = S.score(self.truth, pred)
        self.assertEqual((m["overall"]["tp"], m["overall"]["fp"], m["overall"]["fn"]), (2, 2, 2))
        self.assertEqual((m["AMB"]["tp"], m["AMB"]["fp"], m["AMB"]["fn"]), (1, 1, 0))
        self.assertEqual((m["UNT"]["tp"], m["UNT"]["fp"], m["UNT"]["fn"]), (0, 1, 1))
        self.assertEqual((m["GAP"]["tp"], m["GAP"]["fp"], m["GAP"]["fn"]), (1, 0, 1))

    def test_no_findings(self):
        m = S.score(self.truth, set())
        self.assertEqual(m["overall"]["recall"], 0.0)
        self.assertIsNone(m["overall"]["precision"])
        self.assertEqual(m["overall"]["f1"], 0.0)

    def test_unknown_req_id_is_fp_and_reported(self):
        m = S.score(self.truth, {("T-99", "AMB")})
        self.assertEqual(m["overall"]["fp"], 1)
        self.assertEqual(m["unknown_req_ids"], [("T-99", "AMB")])

    def test_duplicate_findings_collapse(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"findings": [{"req_id": "T-1", "category": "AMB"},
                                    {"req_id": "T-1", "category": "AMB", "evidence": "other"}]}, f)
        try:
            self.assertEqual(S.load_predictions(f.name), {("T-1", "AMB")})
        finally:
            os.unlink(f.name)


class TestLoadTruth(unittest.TestCase):
    def _write(self, reqs):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"requirements": reqs}, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_null_labels_refused(self):
        with self.assertRaises(S.LabelError):
            S.load_truth(self._write([{"req_id": "A", "labels": None}]))

    def test_bad_category_refused(self):
        with self.assertRaises(S.LabelError):
            S.load_truth(self._write([{"req_id": "A", "labels": [{"category": "XYZ"}]}]))

    def test_non_list_labels_refused(self):
        with self.assertRaises(S.LabelError):
            S.load_truth(self._write([{"req_id": "A", "labels": "AMB"}]))

    def test_duplicate_id_refused(self):
        with self.assertRaises(S.LabelError):
            S.load_truth(self._write([{"req_id": "A", "labels": []}, {"req_id": "A", "labels": []}]))

    def test_empty_list_is_clean(self):
        self.assertEqual(S.load_truth(self._write([{"req_id": "A", "labels": []}])), {"A": set()})


if __name__ == "__main__":
    unittest.main()
