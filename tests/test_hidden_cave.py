import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.fight.hidden_cave import BASE_HEIGHT, BASE_WIDTH, HiddenCaveSolver, _overlap_shift


class HiddenCaveSolverTests(unittest.TestCase):
    def setUp(self):
        self.solver = HiddenCaveSolver()

    def test_empty_and_flat_images_are_rejected(self):
        self.assertIsNone(self.solver.analyze(None))
        self.assertIsNone(self.solver.analyze(np.zeros((BASE_HEIGHT, BASE_WIDTH, 3), np.uint8)))

    def test_packaged_references_are_available(self):
        references = self.solver._load_references()
        self.assertEqual(len(references), 10)
        self.assertTrue(all(signature.size for _, signature in references))

    def test_save_reference_round_trip(self):
        image = np.zeros((BASE_HEIGHT, BASE_WIDTH, 3), np.uint8)
        image[:, :, 1] = np.linspace(0, 255, BASE_WIDTH, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            solver = HiddenCaveSolver(Path(tmp))
            self.assertTrue(solver.save_reference(image, "layout-x", "BL", "TR").exists())
            matched = HiddenCaveSolver(Path(tmp))._reference_solution(image, "BL")
            self.assertIsNotNone(matched)
            self.assertEqual(matched[0], "TR")

    def test_overlap_shift_finds_translated_shape(self):
        key = np.zeros((80, 80), np.uint8)
        shadow = np.zeros_like(key)
        key[20:40, 25:45] = 255
        shadow[26:46, 18:38] = 255
        iou, shift = _overlap_shift(key, shadow, search=20, coarse=2)
        self.assertGreater(iou, 0.95)
        self.assertLessEqual(max(abs(shift[0]), abs(shift[1])), 20)


if __name__ == "__main__":
    unittest.main()
