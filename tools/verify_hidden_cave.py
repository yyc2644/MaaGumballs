"""Offline check for the hidden-cave solver (神秘洞穴拼图).

Runs :class:`action.fight.hidden_cave.HiddenCaveSolver` against labelled
screenshots and reports which layouts it solves, refuses, or gets wrong.  The
labels mirror ``puzzle_solver.py``'s REFERENCE_MAP and the packaged
``assets/resource/base/image/fight/HiddenCave/references.json``.

Examples:

    python tools/verify_hidden_cave.py
    python tools/verify_hidden_cave.py --fixtures "D:\\codex\\模拟器滑动"
    python tools/verify_hidden_cave.py --no-references --annotate debug/cave
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = PROJECT_ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from action.fight.hidden_cave import (  # noqa: E402
    BASE_HEIGHT,
    BASE_WIDTH,
    SLOT_ANCHORS,
    HiddenCaveSolver,
)


DEFAULT_FIXTURES = Path(r"D:\codex\模拟器滑动")
LABELS = {
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
    "3888280520142719788 (1).png": ("BR", "TL"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Check the hidden-cave solver offline")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="folder holding the labelled 720x1280 screenshots",
    )
    parser.add_argument(
        "--no-references",
        action="store_true",
        help="ignore the packaged reference table and exercise the vision fallback",
    )
    parser.add_argument(
        "--annotate",
        type=Path,
        default=None,
        help="write marked-up copies (source green, target orange) into this folder",
    )
    return parser.parse_args()


def load(path: Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def annotate(image: np.ndarray, solution, output: Path) -> None:
    marked = image.copy()
    for point, colour, tag in (
        (solution.source_point, (0, 255, 0), solution.source),
        (solution.target_point, (0, 128, 255), solution.target),
    ):
        cv2.circle(marked, point, 36, colour, 5)
        cv2.putText(
            marked,
            tag,
            (point[0] - 20, point[1] - 46),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            colour,
            2,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), marked)


def anchor_gap(point, slot: str, shape) -> float:
    height, width = shape[:2]
    anchor = (
        SLOT_ANCHORS[slot][0] * width / BASE_WIDTH,
        SLOT_ANCHORS[slot][1] * height / BASE_HEIGHT,
    )
    return float(np.hypot(point[0] - anchor[0], point[1] - anchor[1]))


def main() -> int:
    args = parse_args()
    solver = (
        HiddenCaveSolver(reference_dir=Path("__missing_reference_dir__"))
        if args.no_references
        else HiddenCaveSolver()
    )
    mode = "vision" if args.no_references else "reference+vision"

    accepted = refused = wrong = skipped = 0
    for name, (expected_source, expected_target) in LABELS.items():
        path = args.fixtures / name
        if not path.exists():
            skipped += 1
            continue
        image = load(path)
        if image is None:
            print(f"{name}: 无法读取")
            skipped += 1
            continue
        solution = solver.analyze(image)
        if solution is None:
            refused += 1
            print(f"{name}: 拒绝 (期望 {expected_source}->{expected_target})")
            continue
        accepted += 1
        ok = (solution.source, solution.target) == (expected_source, expected_target)
        wrong += 0 if ok else 1
        print(
            f"{name}: {solution.source}->{solution.target} {'OK' if ok else 'XX'} "
            f"期望 {expected_source}->{expected_target} mode={solution.mode} "
            f"conf={solution.confidence:.2f} "
            f"源距锚点={anchor_gap(solution.source_point, solution.source, image.shape):.0f} "
            f"目标距锚点={anchor_gap(solution.target_point, solution.target, image.shape):.0f}"
        )
        if args.annotate is not None:
            annotate(image, solution, args.annotate / f"{name}.debug.png")

    print(
        f"\n模式={mode} 接受={accepted} 拒绝={refused} 错误={wrong} 缺少={skipped}"
    )
    if accepted == 0 and skipped == 0:
        print("没有任何布局通过识别，检查截图目录")
        return 1
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
