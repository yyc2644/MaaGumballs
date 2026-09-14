from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger


BASE_WIDTH = 720
BASE_HEIGHT = 1280
CAVE_ROI = (62, 490, 590, 370)
SLOT_ANCHORS = {
    "TL": (190, 625),
    "TR": (530, 625),
    "BL": (160, 835),
    "BR": (460, 835),
}
REFERENCE_MAX_DISTANCE = 8.0
REFERENCE_DIR = (
    Path(__file__).resolve().parents[3]
    / "assets"
    / "resource"
    / "base"
    / "image"
    / "fight"
    / "HiddenCave"
)


@dataclass(frozen=True)
class HiddenCaveSolution:
    source: str
    target: str
    source_point: tuple[int, int]
    target_point: tuple[int, int]
    confidence: float
    mode: str
    reference: str | None = None
    distance: float | None = None


class HiddenCaveSolver:
    """Recognize the four-slot key-and-shadow puzzle on a 720x1280 screen."""

    def __init__(self, reference_dir: Path = REFERENCE_DIR):
        self.reference_dir = Path(reference_dir)

    @staticmethod
    def _scale_point(
        point: tuple[int, int], image_shape: tuple[int, ...]
    ) -> tuple[int, int]:
        height, width = image_shape[:2]
        return (
            round(point[0] * width / BASE_WIDTH),
            round(point[1] * height / BASE_HEIGHT),
        )

    @staticmethod
    def _signature(image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        x, y, w, h = CAVE_ROI
        x1 = round(x * width / BASE_WIDTH)
        y1 = round(y * height / BASE_HEIGHT)
        x2 = round((x + w) * width / BASE_WIDTH)
        y2 = round((y + h) * height / BASE_HEIGHT)
        gray = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (48, 36), interpolation=cv2.INTER_AREA).astype(
            np.float32
        )

    def _load_references(self):
        index_path = self.reference_dir / "references.json"
        if not index_path.exists():
            return []
        index = json.loads(index_path.read_text(encoding="utf-8"))
        references = []
        for item in index:
            signature = cv2.imread(
                str(self.reference_dir / item["file"]), cv2.IMREAD_GRAYSCALE
            )
            if signature is None:
                logger.warning(f"洞穴拼图参考特征缺失: {item['file']}")
                continue
            references.append((item, signature.astype(np.float32)))
        return references

    def _locate_piece(self, image: np.ndarray, slot: str) -> tuple[int, int]:
        height, width = image.shape[:2]
        anchor_x, anchor_y = self._scale_point(SLOT_ANCHORS[slot], image.shape)
        half_w = round(105 * width / BASE_WIDTH)
        half_h = round(90 * height / BASE_HEIGHT)
        x1, x2 = max(0, anchor_x - half_w), min(width, anchor_x + half_w)
        y1, y2 = max(0, anchor_y - half_h), min(height, anchor_y + half_h)
        patch = image[y1:y2, x1:x2]

        high = patch.max(axis=2).astype(np.int16)
        low = patch.min(axis=2).astype(np.int16)
        luma = patch.mean(axis=2)
        mask = (((high - low) > 30) & (luma > 38)).astype(np.uint8) * 255
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8)
        )
        count, _, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
        choices = []
        local_anchor = (anchor_x - x1, anchor_y - y1)
        for component in range(1, count):
            area = int(stats[component, cv2.CC_STAT_AREA])
            if area < 45:
                continue
            cx, cy = centers[component]
            distance = np.hypot(cx - local_anchor[0], cy - local_anchor[1])
            choices.append((area - distance * 1.5, cx, cy))
        if not choices:
            return anchor_x, anchor_y
        _, cx, cy = max(choices)
        return round(x1 + cx), round(y1 + cy)

    def detect_source(self, image: np.ndarray) -> tuple[str, float]:
        """The real key has much sharper edges than the three translucent shadows."""
        sharpness = {}
        height, width = image.shape[:2]
        for slot, anchor in SLOT_ANCHORS.items():
            x, y = self._scale_point(anchor, image.shape)
            half_w = round(100 * width / BASE_WIDTH)
            half_h = round(85 * height / BASE_HEIGHT)
            patch = image[y - half_h : y + half_h, x - half_w : x + half_w]
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            sharpness[slot] = float(cv2.Laplacian(gray, cv2.CV_32F).var())
        ranked = sorted(sharpness, key=sharpness.get, reverse=True)
        margin = sharpness[ranked[0]] / max(1.0, sharpness[ranked[1]])
        return ranked[0], margin

    def analyze(self, image: np.ndarray) -> HiddenCaveSolution | None:
        if image is None or image.size == 0:
            return None
        source, source_margin = self.detect_source(image)
        current = self._signature(image)
        matches = []
        for item, reference in self._load_references():
            distance = float(np.sqrt(np.mean((current - reference) ** 2)))
            matches.append((distance, item))
        if not matches:
            logger.warning("洞穴拼图没有可用的参考特征")
            return None

        distance, item = min(matches, key=lambda pair: pair[0])
        expected_source = item["source"]
        if distance > REFERENCE_MAX_DISTANCE or source != expected_source:
            logger.warning(
                "洞穴拼图未达到自动拖动条件: "
                f"source={source}, source_margin={source_margin:.2f}, "
                f"reference={item['name']}, distance={distance:.2f}"
            )
            return None

        target = item["target"]
        confidence = max(0.0, 1.0 - distance / REFERENCE_MAX_DISTANCE)
        return HiddenCaveSolution(
            source=source,
            target=target,
            source_point=self._locate_piece(image, source),
            target_point=self._locate_piece(image, target),
            confidence=confidence,
            mode="reference",
            reference=item["name"],
            distance=distance,
        )


@AgentServer.custom_action("SolveHiddenCavePuzzle")
class SolveHiddenCavePuzzle(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        image = context.tasker.controller.post_screencap().wait().get()
        solution = HiddenCaveSolver().analyze(image)
        if solution is None:
            return CustomAction.RunResult(success=False)

        logger.info(
            "洞穴拼图开始拖动: "
            f"{solution.source}{solution.source_point} -> "
            f"{solution.target}{solution.target_point}, "
            f"reference={solution.reference}, distance={solution.distance:.2f}"
        )
        context.tasker.controller.post_swipe(
            solution.source_point[0],
            solution.source_point[1],
            solution.target_point[0],
            solution.target_point[1],
            650,
        ).wait()
        time.sleep(1)
        return CustomAction.RunResult(success=True)
