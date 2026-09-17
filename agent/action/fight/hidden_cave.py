from __future__ import annotations

import json
import math
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
_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
_REFERENCE_CANDIDATES = (
    _PACKAGE_ROOT / "resource" / "base" / "image" / "fight" / "HiddenCave",
    _PACKAGE_ROOT
    / "assets"
    / "resource"
    / "base"
    / "image"
    / "fight"
    / "HiddenCave",
)
REFERENCE_DIR = next(
    (path for path in _REFERENCE_CANDIDATES if path.exists()),
    _REFERENCE_CANDIDATES[0],
)
SIGNATURE_SIZE = (48, 36)

# 参考图整屏匹配阈值：48x36 灰度签名的 RMSE，越小越像
REFERENCE_MAX_DISTANCE = 8.0
# 真钥匙的边缘最锐利，用于挑选源格子
SOURCE_MIN_MARGIN = 1.4
SOURCE_MIN_VARIANCE = 50.0
# 未收录布局时的结构比对门槛。实测 10 张标注截图里，猜错的布局分别是
# score=0.563/margin=1.28 和 score=0.529/margin=1.10：得分门槛挡住前者，
# 领先幅度门槛挡住后者。宁可拒绝交给人工，也不要把钥匙拖到错误的剪影上。
STRUCTURE_MIN_SCORE = 0.65
STRUCTURE_MIN_MARGIN = 1.15

# 扫描窗口 / 定位窗口半径（基于 720x1280）
ANALYSIS_RADIUS = (135, 135)
PIECE_RADIUS = (105, 90)

# ---- 颜色分割识别（基于 2026-09-17 真机截图标定）----
# 真钥匙的水晶部分是蓝青色（实测 H≈105-107），剪影是高饱和红色。
# 面板纵向范围：y<350 是洞顶灯排（呈蓝色，必须排除），y>860 是底部 UI。
PANEL_TOP = 350
PANEL_BOTTOM = 860
KEY_BLUE_HUE = (95, 118)
KEY_BLUE_MIN_SAT = 40
KEY_BLUE_MIN_VAL = 80
SIL_RED_MAX_HUE = 8
SIL_RED_MIN_HUE = 172
SIL_RED_MIN_SAT = 90
SIL_RED_MIN_VAL = 70
KEY_BLOB_MIN_AREA = 250
SIL_BLOB_MIN_AREA = 1000
KEY_SPRITE_WINDOW = 90
# 形状对齐判定：剪影可能接近对称（实测 0.806 vs 0.748, gap 仅 0.058），
# 静态判定无法区分姿态时不再拒绝，而是按 IoU 降序逐个候选尝试——拖过去
# 后用截图校验是否真的重合，没重合就换下一个。TARGET_MIN_IOU 只是兜底
# 门槛：最高 IoU 都低于它说明颜色识别本身不可靠（如背景误判），才放弃。
TARGET_MIN_IOU = 0.50

# 拖拽参数
# 卷轴悬吊在绳上，快速拖动会像钟摆一样旋转，导致与剪影姿态不符而开门失败。
# 实测（2026-09-17 真机）：单段 600ms 快拖会转偏；分 3 段慢拖 + 截图校验微调可开门。
DRAG_SEGMENTS = 3
DRAG_SEGMENT_MS = 450
DRAG_SETTLE = 0.15
DRAG_MAX_STEPS = 14
ALIGN_WINDOW = 100
ALIGN_MAX_ATTEMPTS = 3
ALIGN_MIN_IOU = 0.55
# 判定"完全重合"还需同时满足：最优平移残差不超过该像素数（720 基准）。
# 实测 2026-09-17 13:46：IoU=0.552 刚过门槛但卷轴明显偏在剪影一角
# （残差几十像素），只看 IoU 会误判为已合拢。
ALIGN_MAX_RESIDUAL = 8
# 微调滑动的最小距离：低于触摸 slop 的滑动会被系统当作点击丢弃
# （实测 adb/MaaFW 注入 ~25px 均可能失效）。距离不足时把起点沿反方向
# 外扩到该长度，终点保持不变。
ALIGN_MIN_SWIPE = 34

SPRITE_DIFF_THRESHOLD = 30
SPRITE_MIN_AREA = 250


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
    # 剪影中心按 IoU 降序排列，拖拽校验不重合时依次回退尝试
    candidates: tuple[tuple[int, int], ...] = ()


def sprite_mask(patch: np.ndarray, scale: float = 1.0) -> np.ndarray | None:
    """Locally-contrasty blob nearest the window centre: the slot sprite."""
    if patch is None or patch.size == 0:
        return None
    sigma = max(3.0, 9.0 * scale)
    background = cv2.GaussianBlur(patch, (0, 0), sigma)
    diff = np.max(
        np.abs(patch.astype(np.int16) - background.astype(np.int16)), axis=2
    )
    mask = (diff > SPRITE_DIFF_THRESHOLD).astype(np.uint8) * 255
    kernel = _odd(max(3, round(7 * scale)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))

    height, width = mask.shape
    count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
    best = None
    min_area = SPRITE_MIN_AREA * scale * scale
    for component in range(1, count):
        area = int(stats[component, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        cx, cy = centers[component]
        distance = float(np.hypot(cx - width / 2, cy - height / 2))
        score = area - distance * 3.0
        if best is None or score > best[0]:
            best = (score, component)
    if best is None:
        return None
    return (labels == best[1]).astype(np.uint8) * 255


def _odd(value: int) -> int:
    return value if value % 2 else value + 1


def sharpness(patch: np.ndarray) -> float:
    if patch is None or patch.size == 0:
        return 0.0
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_32F).var())


def gradient_map(patch: np.ndarray, scale: float = 1.0) -> np.ndarray:
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    kernel = _odd(max(1, round(3 * scale)))
    if kernel > 1:
        gray = cv2.GaussianBlur(gray, (kernel, kernel), 0)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


class HiddenCaveSolver:
    """Recognize the key-and-shadow puzzle on the "隐秘的洞穴" screen.

    真钥匙的水晶呈蓝青色，三个剪影为高饱和红色半透明精灵——这是与洞穴
    岩石背景最稳定的区别特征。识别流程：

    1. HSV 颜色分割（限制在洞穴面板范围内，排除洞顶灯排与底部 UI）；
    2. 最大的蓝色连通域即真钥匙水晶，以其为中心提取完整钥匙精灵掩码；
    3. 红色连通域即剪影候选，把钥匙精灵掩码按质心对齐到每个剪影算 IoU；
    4. 同姿态剪影 IoU 显著领先（实测 0.83 vs 0.57/0.50），不满足
       ``TARGET_MIN_IOU``/``TARGET_MIN_MARGIN`` 就拒绝出手，交给人工处理。
    """

    def __init__(self, reference_dir: Path = REFERENCE_DIR):
        self.reference_dir = Path(reference_dir)
        self._references: list[tuple[dict, np.ndarray]] | None = None

    # ------------------------------------------------------------------ 基础
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
    def _scale_factor(image_shape: tuple[int, ...]) -> float:
        return image_shape[1] / BASE_WIDTH

    @staticmethod
    def _cave_box(image_shape: tuple[int, ...]) -> tuple[int, int, int, int]:
        height, width = image_shape[:2]
        x, y, w, h = CAVE_ROI
        return (
            round(x * width / BASE_WIDTH),
            round(y * height / BASE_HEIGHT),
            round((x + w) * width / BASE_WIDTH),
            round((y + h) * height / BASE_HEIGHT),
        )

    def _signature(self, image: np.ndarray) -> np.ndarray:
        x1, y1, x2, y2 = self._cave_box(image.shape)
        gray = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, SIGNATURE_SIZE, interpolation=cv2.INTER_AREA).astype(
            np.float32
        )

    # ------------------------------------------------------------ 颜色分割
    @staticmethod
    def _panel_range(image_shape: tuple[int, ...]) -> tuple[int, int]:
        height = image_shape[0]
        return (
            round(PANEL_TOP / BASE_HEIGHT * height),
            round(PANEL_BOTTOM / BASE_HEIGHT * height),
        )

    @staticmethod
    def _color_masks(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """返回 (蓝色真钥匙掩码, 红色剪影掩码)，均已限制在洞穴面板内。"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        blue = (
            (hue >= KEY_BLUE_HUE[0])
            & (hue <= KEY_BLUE_HUE[1])
            & (sat > KEY_BLUE_MIN_SAT)
            & (val > KEY_BLUE_MIN_VAL)
        )
        red = (
            (hue <= SIL_RED_MAX_HUE) | (hue >= SIL_RED_MIN_HUE)
        ) & (sat > SIL_RED_MIN_SAT) & (val > SIL_RED_MIN_VAL)
        top, bottom = HiddenCaveSolver._panel_range(image.shape)
        blue[:top, :] = False
        blue[bottom:, :] = False
        red[:top, :] = False
        red[bottom:, :] = False
        return blue.astype(np.uint8) * 255, red.astype(np.uint8) * 255

    @staticmethod
    def _blobs(
        mask: np.ndarray, min_area: float, denoise_first: bool
    ) -> list[dict]:
        if denoise_first:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
        blobs: list[dict] = []
        for i in range(1, count):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < min_area:
                continue
            box = tuple(int(stats[i, k]) for k in range(4))
            blobs.append(
                {
                    "mask": (labels == i).astype(np.uint8) * 255,
                    "box": box,
                    "center": (
                        round(float(centers[i][0])),
                        round(float(centers[i][1])),
                    ),
                    "area": area,
                }
            )
        return blobs

    def _key_anchor(
        self, image: np.ndarray, scale: float
    ) -> tuple[int, int] | None:
        """当前截图中卷轴宝石的中心——拖拽/微调的按下锚点。

        自由悬挂时宝石是蓝色；被面板吸附后整体被剪影红罩染成粉白色
        （实测蓝像素为 0），因此蓝色找不到时回退粉色宝石检测。
        按下点必须落在卷轴本体上，否则拖拽会按空。
        """
        blue_mask, _ = self._color_masks(image)
        blobs = self._blobs(
            blue_mask, KEY_BLOB_MIN_AREA * scale * scale, denoise_first=False
        )
        if blobs:
            return max(blobs, key=lambda blob: blob["area"])["center"]
        return self._pink_gem_center(image, scale)

    def _pink_gem_center(
        self, image: np.ndarray, scale: float
    ) -> tuple[int, int] | None:
        """已放置卷轴的粉白宝石中心（红罩染色后的水晶，高V中S）。

        面板四角装饰也是高亮橙色，但离剪影很远；宝石必然紧贴某个
        剪影（实测距离 ~40px），据此过滤。
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        height, width = image.shape[:2]
        mask = (
            (hsv[:, :, 1] > 60) & (hsv[:, :, 1] < 160) & (hsv[:, :, 2] > 170)
        ).astype(np.uint8) * 255
        # 只看面板内部：边框岩浆装饰高亮但紧贴左右边缘
        x1 = round(90 * width / BASE_WIDTH)
        x2 = round(630 * width / BASE_WIDTH)
        y1 = round(PANEL_TOP * height / BASE_HEIGHT)
        y2 = round(PANEL_BOTTOM * height / BASE_HEIGHT)
        cropped = np.zeros_like(mask)
        cropped[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
        blobs = self._blobs(cropped, 250 * scale * scale, denoise_first=True)
        if not blobs:
            return None
        _, red_mask = self._color_masks(image)
        sils = self._blobs(
            red_mask, SIL_BLOB_MIN_AREA * scale * scale, denoise_first=True
        )
        sil_centers = [blob["center"] for blob in sils]
        max_dist = 100 * scale
        for blob in sorted(blobs, key=lambda b: b["area"], reverse=True):
            center = blob["center"]
            if sil_centers and min(
                math.hypot(center[0] - sx, center[1] - sy)
                for sx, sy in sil_centers
            ) <= max_dist:
                return center
        return None

    def _key_sprite(
        self, image: np.ndarray, blue_center: tuple[int, int], scale: float
    ) -> tuple[np.ndarray | None, tuple[int, int]]:
        """以蓝色水晶为中心提取完整钥匙精灵掩码（局部前景分割）。

        返回 ``(掩码, 窗口左上角世界坐标)``；提取失败时掩码为 ``None``。
        """
        win = round(KEY_SPRITE_WINDOW * scale)
        height, width = image.shape[:2]
        cx, cy = blue_center
        x1, y1 = max(0, cx - win), max(0, cy - win)
        x2, y2 = min(width, cx + win), min(height, cy + win)
        return sprite_mask(image[y1:y2, x1:x2], scale), (x1, y1)

    # ------------------------------------------------------------ 形状比对
    @staticmethod
    def _aligned_iou(key_sprite: np.ndarray, sil_mask: np.ndarray) -> float:
        """把钥匙精灵质心平移对齐到剪影质心后计算 IoU。

        三个剪影是同一精灵的旋转/镜像版本，只有同姿态的那个在质心对齐后
        能与钥匙轮廓重合，因此 IoU 天然区分姿态，无需滑窗搜索。
        """
        key_ys, key_xs = np.nonzero(key_sprite)
        sil_ys, sil_xs = np.nonzero(sil_mask)
        if len(key_xs) == 0 or len(sil_xs) == 0:
            return 0.0
        key_cx, key_cy = float(key_xs.mean()), float(key_ys.mean())
        sil_cx, sil_cy = float(sil_xs.mean()), float(sil_ys.mean())
        # 把剪影放在三倍大画布中央，钥匙平移过去，避免越界截断
        height, width = sil_mask.shape
        canvas = np.zeros((height * 3, width * 3), np.uint8)
        canvas[height : height * 2, width : width * 2] = sil_mask
        dx = int(round(width + sil_cx - key_cx))
        dy = int(round(height + sil_cy - key_cy))
        xs = key_xs + dx
        ys = key_ys + dy
        valid = (
            (ys >= 0)
            & (ys < canvas.shape[0])
            & (xs >= 0)
            & (xs < canvas.shape[1])
        )
        aligned = np.zeros_like(canvas)
        aligned[ys[valid], xs[valid]] = 255
        inter = float(((aligned > 0) & (canvas > 0)).sum())
        union = float(((aligned > 0) | (canvas > 0)).sum())
        return inter / union if union else 0.0

    # ------------------------------------------------------------ 参考图
    def _load_references(self) -> list[tuple[dict, np.ndarray]]:
        if self._references is not None:
            return self._references
        references: list[tuple[dict, np.ndarray]] = []
        index_path = self.reference_dir / "references.json"
        if not index_path.exists():
            self._references = references
            return references
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for item in index:
            signature = cv2.imread(
                str(self.reference_dir / item["file"]), cv2.IMREAD_GRAYSCALE
            )
            if signature is None:
                logger.warning(f"洞穴拼图参考特征缺失: {item['file']}")
                continue
            references.append((item, signature.astype(np.float32)))
        self._references = references
        return references

    def _reference_solution(
        self, image: np.ndarray, detected_source: str
    ) -> tuple[str, float, str, float] | None:
        """Return ``(target, confidence, name, distance)`` for a known layout."""
        current = self._signature(image)
        matches = []
        for item, reference in self._load_references():
            distance = float(np.sqrt(np.mean((current - reference) ** 2)))
            matches.append((distance, item))
        if not matches:
            logger.warning("洞穴拼图没有可用的参考特征")
            return None
        distance, item = min(matches, key=lambda pair: pair[0])
        if distance > REFERENCE_MAX_DISTANCE:
            logger.info(
                f"洞穴拼图未命中参考图: 最近={item['name']} distance={distance:.2f} "
                f"(阈值 {REFERENCE_MAX_DISTANCE})"
            )
            return None
        if item["source"] != detected_source:
            logger.warning(
                f"洞穴拼图参考图与实测格子不一致: 参考={item['name']} "
                f"记录格子={item['source']} 实测格子={detected_source}"
            )
            return None
        confidence = max(0.0, 1.0 - distance / REFERENCE_MAX_DISTANCE)
        return item["target"], confidence, item["name"], distance

    def save_reference(
        self, image: np.ndarray, name: str, source: str, target: str
    ) -> Path:
        """Teach an unseen layout, mirroring ``puzzle_solver.py --teach``."""
        if source not in SLOT_ANCHORS or target not in SLOT_ANCHORS:
            raise ValueError(f"未知格子: {source} -> {target}")
        self.reference_dir.mkdir(parents=True, exist_ok=True)
        path = self.reference_dir / f"{name}.png"
        if not cv2.imwrite(str(path), self._signature(image).astype(np.uint8)):
            raise OSError(f"写入参考特征失败: {path}")
        index_path = self.reference_dir / "references.json"
        index = (
            json.loads(index_path.read_text(encoding="utf-8"))
            if index_path.exists()
            else []
        )
        index = [item for item in index if item.get("name") != name]
        index.append(
            {"name": name, "file": path.name, "source": source, "target": target}
        )
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
        )
        self._references = None
        logger.info(f"洞穴拼图已记录新布局: {name} {source}->{target}")
        return path

    # ------------------------------------------------------------ 主流程
    def analyze(self, image: np.ndarray) -> HiddenCaveSolution | None:
        if image is None or getattr(image, "size", 0) == 0 or image.ndim != 3:
            return None
        height, width = image.shape[:2]
        if width < BASE_WIDTH * 0.5 or height < BASE_HEIGHT * 0.5:
            logger.warning(f"洞穴拼图截图尺寸异常: {width}x{height}")
            return None

        scale = self._scale_factor(image.shape)
        area_scale = scale * scale
        blue_mask, red_mask = self._color_masks(image)

        # 1. 蓝色最大连通域 = 真钥匙水晶；第二大的面积占比过高说明区分不可靠。
        # 卷轴被面板吸附后整体染成粉色（蓝像素为 0），此时按已放置状态继续。
        blue_blobs = self._blobs(
            blue_mask, KEY_BLOB_MIN_AREA * area_scale, denoise_first=False
        )
        blue_blobs.sort(key=lambda blob: blob["area"], reverse=True)
        docked = False
        if blue_blobs:
            key_blob = blue_blobs[0]
            if len(blue_blobs) > 1 and blue_blobs[1]["area"] > 0.4 * key_blob["area"]:
                logger.warning(
                    f"洞穴拼图蓝色区域不唯一，无法判定真钥匙: "
                    f"{[(b['center'], b['area']) for b in blue_blobs[:3]]}"
                )
                return None
        else:
            pink_center = self._pink_gem_center(image, scale)
            if pink_center is None:
                logger.warning(
                    "洞穴拼图未找到蓝色真钥匙，也未找到已放置的粉宝石"
                )
                return None
            docked = True
            key_blob = {"center": pink_center}
            logger.info(f"卷轴已放置（宝石呈粉色）: {pink_center}")

        # 2. 红色连通域 = 剪影候选
        red_blobs = self._blobs(
            red_mask, SIL_BLOB_MIN_AREA * area_scale, denoise_first=True
        )
        if len(red_blobs) < 2:
            logger.warning(f"洞穴拼图红色剪影数量不足: {len(red_blobs)}")
            return None
        red_blobs.sort(key=lambda blob: blob["area"], reverse=True)
        red_blobs = red_blobs[:3]

        # 3. 提取完整钥匙精灵，与每个剪影做质心对齐 IoU
        key_sprite, sprite_origin = self._key_sprite(image, key_blob["center"], scale)
        if key_sprite is None:
            logger.warning("洞穴拼图无法提取真钥匙精灵，放弃自动拖动")
            return None
        margin_px = round(16 * scale)
        if docked:
            # 已放置状态：整把卷轴被红罩染色，与半透明剪影的 IoU 对比
            # 不可靠（实测仅 ~0.39），跳过外形门槛。最近剪影就是当前
            # 放置点，作为首选候选；是否需要微调交给拖拽校验判断。
            ordered = sorted(
                red_blobs,
                key=lambda b: (b["center"][0] - key_blob["center"][0]) ** 2
                + (b["center"][1] - key_blob["center"][1]) ** 2,
            )
            best = ordered[0]
            best_iou = 0.0
            iou_gap = 0.0
            candidates = tuple(b["center"] for b in ordered)
            confidence = 0.3
        else:
            scored: list[tuple[float, dict]] = []
            for blob in red_blobs:
                bx, by, bw, bh = blob["box"]
                x1 = max(0, bx - margin_px)
                y1 = max(0, by - margin_px)
                x2 = min(width, bx + bw + margin_px)
                y2 = min(height, by + bh + margin_px)
                scored.append(
                    (self._aligned_iou(key_sprite, blob["mask"][y1:y2, x1:x2]), blob)
                )
            scored.sort(key=lambda pair: pair[0], reverse=True)
            best_iou, best = scored[0]
            second_iou = scored[1][0]
            iou_gap = best_iou - second_iou
            if best_iou < TARGET_MIN_IOU:
                logger.warning(
                    f"洞穴拼图剪影与钥匙形状差异过大，颜色识别不可信: "
                    f"best={best['center']} IoU={best_iou:.3f} "
                    f"second={scored[1][1]['center']} IoU={second_iou:.3f}"
                )
                return None
            # 剪影接近对称时静态判定不可靠，交给拖拽后的重合校验来淘汰：
            # 按 IoU 降序逐个候选尝试，拖完校验不重合就换下一个。
            candidates = tuple(blob["center"] for _, blob in scored)
            # 置信度只看最高 IoU（候选淘汰交给拖拽后的重合校验）
            iou_part = (best_iou - TARGET_MIN_IOU) / (0.95 - TARGET_MIN_IOU)
            confidence = round(min(1.0, max(0.0, iou_part)), 3)

        # 4. 拖拽点：抓钥匙精灵质心，放到剪影质心
        key_ys, key_xs = np.nonzero(key_sprite)
        source_point = (
            round(sprite_origin[0] + float(key_xs.mean())),
            round(sprite_origin[1] + float(key_ys.mean())),
        )
        target_point = best["center"]
        solution = HiddenCaveSolution(
            source=f"钥匙{source_point}",
            target=f"剪影{target_point}",
            source_point=source_point,
            target_point=target_point,
            confidence=confidence,
            mode="docked" if docked else "color-iou",
            candidates=candidates,
        )
        logger.info(
            f"洞穴拼图识别{'(已放置)' if docked else ''}: {solution.source} -> "
            f"{solution.target} IoU={best_iou:.3f} gap={iou_gap:.3f} "
            f"candidates={candidates} confidence={confidence}"
        )
        return solution


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
            f"mode={solution.mode}, reference={solution.reference}, "
            f"confidence={solution.confidence:.2f}"
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


def _overlap_shift(
    key_sprite: np.ndarray,
    sil_mask: np.ndarray,
    search: int = 90,
    coarse: int = 4,
) -> tuple[float, tuple[int, int]]:
    """小范围滑窗平移钥匙掩码，找与剪影掩码重合度（IoU）最高的偏移量。

    拖拽后卷轴可能与剪影存在少量平移残差，直接算 IoU 会偏低；该函数返回
    ``(最优 IoU, 使卷轴完全重合还需平移的 (dx, dy))``。
    """
    key_ys, key_xs = np.nonzero(key_sprite)
    sil_ys, sil_xs = np.nonzero(sil_mask)
    if len(key_xs) == 0 or len(sil_xs) == 0:
        return 0.0, (0, 0)
    height, width = sil_mask.shape
    # 剪影放三倍画布中央；钥匙初始按两质心重合摆放，再在附近搜索最优平移
    canvas = np.zeros((height * 3, width * 3), np.uint8)
    canvas[height : height * 2, width : width * 2] = sil_mask
    base_dx = int(round(width + float(sil_xs.mean()) - width / 2))
    base_dy = int(round(height + float(sil_ys.mean()) - height / 2))

    def score(dx: int, dy: int) -> float:
        xs = key_xs + base_dx + dx
        ys = key_ys + base_dy + dy
        valid = (
            (ys >= 0)
            & (ys < canvas.shape[0])
            & (xs >= 0)
            & (xs < canvas.shape[1])
        )
        if valid.sum() < 0.5 * len(key_xs):
            return 0.0
        aligned = np.zeros_like(canvas)
        aligned[ys[valid], xs[valid]] = 255
        inter = float(((aligned > 0) & (canvas > 0)).sum())
        union = float(((aligned > 0) | (canvas > 0)).sum())
        return inter / union if union else 0.0

    best_iou = 0.0
    best_shift = (0, 0)
    for dy in range(-search, search + 1, coarse):
        for dx in range(-search, search + 1, coarse):
            value = score(dx, dy)
            if value > best_iou:
                best_iou = value
                best_shift = (dx, dy)
    for dy in range(best_shift[1] - coarse, best_shift[1] + coarse + 1):
        for dx in range(best_shift[0] - coarse, best_shift[0] + coarse + 1):
            value = score(dx, dy)
            if value > best_iou:
                best_iou = value
                best_shift = (dx, dy)
    return best_iou, best_shift


def drag_key_to_target(
    context: Context,
    solution: HiddenCaveSolution,
    reference_image: np.ndarray,
) -> tuple[bool, float]:
    """把卷轴拖向 IoU 最高的剪影，并用截图反馈校验是否真的重合。

    卷轴悬吊在绳上，快速拖动会像钟摆一样旋转，落点姿态与剪影不符时点
    确定也开不了门。策略（2026-09-17 定稿）：**只认识别阶段给出的第一个
    候选**（IoU 最高的剪影），拖过去校验不重合就立即返回失败，由调用方
    重新进洞识别再试，不做候选间回退。

    实测有效的做法：

    1. 分 ``DRAG_SEGMENTS`` 段慢速拖拽，减少旋转；
    2. 拖完截图提取卷轴精灵掩码，与目标剪影掩码滑窗对齐算 IoU；
    3. IoU 未达标时按最优平移量做微调拖拽，重复至多 ``ALIGN_MAX_ATTEMPTS``
       次，仍不达标则返回失败。

    注意：Agent 进程内 ``post_touch_up`` 会原生崩溃（agent 侧 maafw 与
    MFA 内置运行库版本不一致），因此全程使用 ``post_swipe``。

    Returns:
        ``(是否对齐达标, 过程中最优残差 px)``
    """
    controller = context.tasker.controller
    scale = reference_image.shape[1] / BASE_WIDTH
    solver = HiddenCaveSolver()
    target = solution.target_point

    # 卷轴叠上剪影后被游戏锁定，拖不动且手势会穿透弹窗（真机实测会把
    # 弹窗拖关）。已吸附状态无法微调，直接返回失败，由调用方走
    # "OCR 点返回 → 重新进洞"的恢复流程。
    # 判据：蓝色水晶消失 + 粉宝石出现。只看粉色会误报——剪影自带的
    # 红色印章图案同样命中粉色条件（真机回归：cave_now2 帧误报）；
    # 不能用 _key_anchor 判蓝——它自身会回退粉色，永远非 None。
    blue_mask, _ = solver._color_masks(reference_image)
    has_blue = bool(
        solver._blobs(blue_mask, KEY_BLOB_MIN_AREA * scale * scale, denoise_first=False)
    )
    if not has_blue and solver._pink_gem_center(reference_image, scale) is not None:
        logger.warning(
            "洞穴拖拽校验失败: 卷轴已被吸附锁定，无法微调，本轮返回失败"
        )
        return False, 0.0

    # 卷轴是刚体：识别帧里"精灵质心 - 水晶锚点"的偏移恒定。之后每步用
    # "当前水晶位置 + 偏移"直接推算卷轴位置，与剪影中心的残差即微调量。
    # 之前用 sprite_mask 在水晶附近窗口提取"卷轴掩码"再算 IoU/shift，窗口
    # 混入相邻剪影或面板边框时掩码被污染，shift 指向错误方向（真机诊断：
    # 指令向左 34px 实际只下移 15px，卷轴被一路赶进面板角落越调越远）。
    gem0 = solver._key_anchor(reference_image, scale)
    if gem0 is None:
        logger.warning("洞穴拖拽校验失败: 参考帧定位不到卷轴水晶锚点")
        return False, 0.0
    offset = (
        solution.source_point[0] - gem0[0],
        solution.source_point[1] - gem0[1],
    )

    def _clamp_panel(point: tuple[int, int]) -> tuple[int, int]:
        """面板内部可停留区域，防止把卷轴拖到边界上被钳制卡住。"""
        x = min(max(point[0], round(110 * scale)), round(610 * scale))
        y = min(max(point[1], round(370 * scale)), round(850 * scale))
        return x, y

    # 水晶锚点必须落在卷轴本体上（按在剪影/空白处会按空）。
    fresh = controller.post_screencap().wait().get()
    if fresh is not None and getattr(fresh, "size", 0) > 0:
        anchor = solver._key_anchor(fresh, scale)
        if anchor is not None:
            current = anchor
        else:
            current = solution.source_point
    else:
        current = solution.source_point

    # 分段慢拖：把"卷轴质心"送到剪影中心，即水晶拖到 target-offset。
    # 直接把水晶拖到剪影中心会留下 offset 大小的先天残差，全靠微调兜底。
    drag_end = _clamp_panel(
        (target[0] - offset[0], target[1] - offset[1])
    )
    start = current
    px, py = start
    for i in range(1, DRAG_SEGMENTS + 1):
        fx = round(start[0] + (drag_end[0] - start[0]) * i / DRAG_SEGMENTS)
        fy = round(start[1] + (drag_end[1] - start[1]) * i / DRAG_SEGMENTS)
        controller.post_swipe(px, py, fx, fy, DRAG_SEGMENT_MS).wait()
        px, py = fx, fy
        time.sleep(DRAG_SETTLE)
    time.sleep(DRAG_SETTLE * 5)

    # 截图校验 + 微调：每步重新截图、重新定位水晶、重算刚体残差
    ok = False
    best_residual = float("inf")
    for attempt in range(ALIGN_MAX_ATTEMPTS):
        image = controller.post_screencap().wait().get()
        if image is None or getattr(image, "size", 0) == 0:
            logger.warning(f"洞穴对齐校验: 截图失败 (第{attempt + 1}次)")
            break
        anchor = solver._key_anchor(image, scale)
        if anchor is None:
            logger.warning(
                f"洞穴对齐校验: 定位不到卷轴水晶锚点 (第{attempt + 1}次)"
            )
            break
        center = (anchor[0] + offset[0], anchor[1] + offset[1])
        residual_vec = (target[0] - center[0], target[1] - center[1])
        residual = math.hypot(*residual_vec)
        best_residual = min(best_residual, residual)
        if residual <= ALIGN_MAX_RESIDUAL * scale:
            ok = True
            break
        # 微调：按下点在水晶上，卷轴 1:1 跟随手指位移，因此滑动向量
        # 必须恰好等于残差向量。不要外扩起点凑滑动长度——外扩多少就
        # 过冲多少（真机实测 22px 残差被外扩成 34px 位移，来回振荡）。
        shift_x, shift_y = round(residual_vec[0]), round(residual_vec[1])
        end_x = _clamp_panel((anchor[0] + shift_x, anchor[1] + shift_y))
        logger.info(
            f"洞穴对齐微调: {target} 残差={residual:.0f}px "
            f"锚点{anchor} 推算中心{center} -> swipe{anchor}->{end_x}"
        )
        controller.post_swipe(anchor[0], anchor[1], end_x[0], end_x[1], 700).wait()
        time.sleep(DRAG_SETTLE * 5)

    if ok:
        logger.info(
            f"洞穴拖拽对齐结束: {target} 重合达标 残差={best_residual:.0f}px"
        )
        return True, best_residual

    # 第一个候选没重合：不做候选回退，直接返回失败，交由调用方重新进洞识别
    logger.warning(
        f"洞穴拖拽对齐结束: 目标{target} 微调{ALIGN_MAX_ATTEMPTS}次仍未重合 "
        f"最优残差={best_residual:.0f}px，本轮返回失败"
    )
    return False, best_residual
