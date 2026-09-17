#!/usr/bin/env python3
"""离线验证“隐秘的洞穴”钥匙是否拖到正确剪影位置。

支持两种运行方式：

1. 比较指定的移动前、移动后截图：
   python tools/verify_hidden_cave_move.py --before before.png --after after.png

2. 按文件名时间顺序，将文件夹中的图片两两配对并验证：
   python tools/verify_hidden_cave_move.py --folder "C:\\Screenshots" --rounds 3

本脚本只读取图片，不连接模拟器，也不会执行点击或拖拽。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


BASE_WIDTH = 720
BASE_HEIGHT = 1280

# 720x1280 截图中四个槽位的分析区域：(x1, y1, x2, y2)
BASE_SLOT_BOXES = {
    "TL": (90, 390, 330, 590),
    "TR": (390, 390, 650, 590),
    "BL": (80, 590, 330, 820),
    "BR": (380, 590, 650, 820),
}

# 由 5 组实际截图得到的保守阈值。
MIN_BLUE_PRESENCE = 0.008
MIN_BLUE_DELTA = 0.012
MIN_RED_DELTA = 0.030
MIN_CHANGED_RATIO = 0.040
MAX_STABLE_RATIO = 0.020
PIXEL_DIFF_THRESHOLD = 40


@dataclass(frozen=True)
class SlotFeatures:
    blue_ratio: float
    red_ratio: float
    sharpness: float


@dataclass(frozen=True)
class SlotChange:
    before: SlotFeatures
    after: SlotFeatures
    changed_pixels: int
    changed_ratio: float


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    source: str
    target: str
    checks: dict[str, bool]
    changes: dict[str, SlotChange]


def read_image(path: Path) -> np.ndarray:
    """兼容 Windows 中文路径读取 BGR 图片。"""
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片：{path}")
    return image


def scaled_boxes(image: np.ndarray) -> dict[str, tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    return {
        name: (
            round(x1 * width / BASE_WIDTH),
            round(y1 * height / BASE_HEIGHT),
            round(x2 * width / BASE_WIDTH),
            round(y2 * height / BASE_HEIGHT),
        )
        for name, (x1, y1, x2, y2) in BASE_SLOT_BOXES.items()
    }


def slot_features(image: np.ndarray, box: tuple[int, int, int, int]) -> SlotFeatures:
    x1, y1, x2, y2 = box
    patch = image[y1:y2, x1:x2]
    if patch.size == 0:
        raise ValueError(f"无效槽位区域：{box}")

    # 转为 int16，避免 uint8 在 +10、+20 时溢出。
    b, g, r = [channel.astype(np.int16) for channel in cv2.split(patch)]
    brightness = (b + g + r) / 3.0

    blue_mask = (b > r + 10) & (b > g + 5) & (brightness > 45)
    red_mask = (r > g + 20) & (r > b + 15) & (r > 55)

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    return SlotFeatures(
        blue_ratio=float(blue_mask.mean()),
        red_ratio=float(red_mask.mean()),
        sharpness=sharpness,
    )


def verify_move(before: np.ndarray, after: np.ndarray) -> VerificationResult:
    if before.shape != after.shape:
        raise ValueError(f"前后截图尺寸不同：{before.shape} != {after.shape}")

    boxes = scaled_boxes(before)
    before_features = {
        name: slot_features(before, box) for name, box in boxes.items()
    }
    after_features = {
        name: slot_features(after, box) for name, box in boxes.items()
    }

    # 初始图中蓝白实体最多的位置是源；完成图中蓝白实体最多的位置是目标。
    source = max(before_features, key=lambda name: before_features[name].blue_ratio)
    target = max(after_features, key=lambda name: after_features[name].blue_ratio)

    pixel_difference = np.max(
        np.abs(before.astype(np.int16) - after.astype(np.int16)), axis=2
    )
    changes = {}
    for name, (x1, y1, x2, y2) in boxes.items():
        changed_pixels = int(
            np.count_nonzero(
                pixel_difference[y1:y2, x1:x2] > PIXEL_DIFF_THRESHOLD
            )
        )
        area = max(1, (x2 - x1) * (y2 - y1))
        changes[name] = SlotChange(
            before=before_features[name],
            after=after_features[name],
            changed_pixels=changed_pixels,
            changed_ratio=changed_pixels / area,
        )

    src = changes[source]
    dst = changes[target]
    other_slots = [name for name in boxes if name not in (source, target)]
    checks = {
        "source_and_target_differ": source != target,
        "source_key_present_before": src.before.blue_ratio >= MIN_BLUE_PRESENCE,
        "source_key_removed": (
            src.before.blue_ratio - src.after.blue_ratio >= MIN_BLUE_DELTA
        ),
        "target_key_present_after": dst.after.blue_ratio >= MIN_BLUE_PRESENCE,
        "target_key_added": (
            dst.after.blue_ratio - dst.before.blue_ratio >= MIN_BLUE_DELTA
        ),
        "source_red_overlay_removed": (
            src.before.red_ratio - src.after.red_ratio >= MIN_RED_DELTA
        ),
        "target_red_overlay_reduced": (
            dst.before.red_ratio - dst.after.red_ratio >= MIN_RED_DELTA
        ),
        "source_region_changed": src.changed_ratio >= MIN_CHANGED_RATIO,
        "target_region_changed": dst.changed_ratio >= MIN_CHANGED_RATIO,
        "other_regions_stable": all(
            changes[name].changed_ratio <= MAX_STABLE_RATIO for name in other_slots
        ),
    }
    return VerificationResult(
        passed=all(checks.values()),
        source=source,
        target=target,
        checks=checks,
        changes=changes,
    )


def print_result(
    result: VerificationResult,
    round_number: int,
    before_path: Path,
    after_path: Path,
) -> None:
    print(f"\n第 {round_number} 轮：{'PASS' if result.passed else 'FAIL'}")
    print(f"  初始图：{before_path.name}")
    print(f"  完成图：{after_path.name}")
    print(f"  检测移动：{result.source} -> {result.target}")
    for name, change in result.changes.items():
        print(
            f"  {name}: blue {change.before.blue_ratio:.4f} -> "
            f"{change.after.blue_ratio:.4f}, red {change.before.red_ratio:.4f} -> "
            f"{change.after.red_ratio:.4f}, changed={change.changed_pixels} "
            f"({change.changed_ratio:.3%})"
        )
    failed = [name for name, passed in result.checks.items() if not passed]
    print("  判据：" + ("全部通过" if not failed else "未通过 " + ", ".join(failed)))


def image_pairs(args: argparse.Namespace) -> list[tuple[Path, Path]]:
    if args.before or args.after:
        if not args.before or not args.after:
            raise ValueError("--before 和 --after 必须同时提供")
        return [(args.before, args.after)]

    files = sorted(
        path
        for path in args.folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if len(files) < 2:
        raise ValueError(f"文件夹中没有足够的截图：{args.folder}")
    if len(files) % 2:
        print(f"警告：共有 {len(files)} 张图片，最后一张不会参与配对", file=sys.stderr)
    pairs = list(zip(files[0::2], files[1::2]))
    return pairs[: args.rounds] if args.rounds else pairs


def main() -> int:
    parser = argparse.ArgumentParser(description="离线验证洞穴钥匙拖拽是否到位")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--folder", type=Path, help="按文件名排序并两两配对的截图文件夹")
    mode.add_argument("--before", type=Path, help="移动前截图")
    parser.add_argument("--after", type=Path, help="移动后截图（与 --before 一起使用）")
    parser.add_argument("--rounds", type=int, help="文件夹模式最多验证多少轮")
    parser.add_argument("--json", action="store_true", help="额外输出 JSON 结果")
    args = parser.parse_args()

    try:
        pairs = image_pairs(args)
        results = []
        for index, (before_path, after_path) in enumerate(pairs, start=1):
            result = verify_move(read_image(before_path), read_image(after_path))
            print_result(result, index, before_path, after_path)
            results.append(
                {
                    "round": index,
                    "before": str(before_path),
                    "after": str(after_path),
                    **asdict(result),
                }
            )
        passed_count = sum(item["passed"] for item in results)
        print(f"\n汇总：{passed_count}/{len(results)} 轮通过")
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if passed_count == len(results) else 1
    except (OSError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
