import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.fight.hidden_cave import HiddenCaveSolver


SOURCE_IMAGES = Path(r"D:\codex\模拟器滑动")


class HiddenCaveSolverTests(unittest.TestCase):
    def setUp(self):
        self.solver = HiddenCaveSolver()

    def test_scale_point(self):
        self.assertEqual(self.solver._scale_point((160, 835), (2560, 1440, 3)), (320, 1670))

    @unittest.skipUnless(SOURCE_IMAGES.exists(), "local puzzle fixtures not available")
    def test_reference_screenshots(self):
        cases = {
            "string1.png": ("BL", "TR"),
            "string2.png": ("BL", "BR"),
            "string3.png": ("BL", "TL"),
            "string4.png": ("TL", "BL"),
            "string5.png": ("BR", "TL"),
            "string6.png": ("BL", "BR"),
            "-4841755502577331410.png": ("BR", "TL"),
            "-7546423012262589274.png": ("TR", "TL"),
            "4182957333929987320.png": ("TR", "BR"),
            "3888280520142719788.png": ("BR", "TL"),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                data = cv2.imdecode(
                    np.fromfile(SOURCE_IMAGES / filename, dtype=np.uint8),
                    cv2.IMREAD_COLOR,
                )
                solution = self.solver.analyze(data)
                self.assertIsNotNone(solution)
                self.assertEqual((solution.source, solution.target), expected)

    def test_empty_image_is_rejected(self):
        self.assertIsNone(self.solver.analyze(None))

    def test_packaged_reference_is_used(self):
        item, signature = self.solver._load_references()[0]
        with (
            patch.object(
                self.solver, "detect_source", return_value=(item["source"], 4.0)
            ),
            patch.object(self.solver, "_signature", return_value=signature),
            patch.object(self.solver, "_locate_piece", return_value=(100, 200)),
        ):
            solution = self.solver.analyze(np.zeros((1280, 720, 3), dtype=np.uint8))

        self.assertIsNotNone(solution)
        self.assertEqual(solution.source, item["source"])
        self.assertEqual(solution.target, item["target"])
        self.assertEqual(solution.distance, 0.0)

    def test_unknown_screen_is_rejected(self):
        image = np.zeros((1280, 720, 3), dtype=np.uint8)
        self.assertIsNone(self.solver.analyze(image))


if __name__ == "__main__":
    unittest.main()
