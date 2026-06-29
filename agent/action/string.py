import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

MAX_RETRY_ATTEMPTS = 1  # 定义最大重试次数,自动尝试一次,失败就摇人

import time
import subprocess
import cv2
import numpy as np

from skimage.metrics import structural_similarity as ssim




MAX_RETRY_ATTEMPTS = 1 #自动识别一次,失败就摇人
SIMILARITY_THRESHOLD = 0.95


@AgentServer.custom_action("AutoMatchDrag")
class AutoMatchDrag(CustomAction):
    """
    自动识别相同小图并拖拽的自定义动作
    """

    _retry_count: int
    _matched: bool
    _blocks: list
    _pair: tuple | None

    def __init__(self):
        super().__init__()
        self.resetParam()
        logger.debug("AutoMatchDrag 实例已创建并初始化。")

    def resetParam(self):
        """
        重置运行状态
        """
        self._retry_count = 0
        self._matched = False
        self._blocks = []
        self._pair = None

    # ======================
    # ADB 工具
    # ======================

    def _adb_screenshot(self):
        proc = subprocess.Popen(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE
        )
        img_bytes = proc.stdout.read()
        return cv2.imdecode(
            np.frombuffer(img_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

    def _adb_drag(self, x1, y1, x2, y2, duration=200):
        subprocess.call([
            "adb", "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration)
        ])

    # ======================
    # 图像识别逻辑
    # ======================

    def _find_blocks(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, th = cv2.threshold(
            blur, 200, 255, cv2.THRESH_BINARY_INV
        )

        contours, _ = cv2.findContours(
            th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        blocks = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if 100 < w < 200 and 100 < h < 200:
                blocks.append((x, y, w, h))

        return blocks

    def _find_same_pair(self, img, blocks):
        patches = []

        for x, y, w, h in blocks:
            patch = img[y:y+h, x:x+w]
            patch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            patch = cv2.resize(patch, (100, 100))
            patches.append(patch)

        max_score = 0
        pair = None

        for i in range(len(patches)):
            for j in range(i + 1, len(patches)):
                score, _ = ssim(patches[i], patches[j], full=True)
                if score > max_score:
                    max_score = score
                    pair = (i, j)

        return pair, max_score

    # ======================
    # 主入口
    # ======================

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        self.resetParam()
        logger.info("AutoMatchDrag 自定义动作开始执行。")

        while self._retry_count < MAX_RETRY_ATTEMPTS:
            if context.tasker.stopping:
                logger.info("检测到停止请求，AutoMatchDrag 终止。")
                return CustomAction.RunResult(success=False)

            self._retry_count += 1
            logger.info(f"第 {self._retry_count}/{MAX_RETRY_ATTEMPTS} 次识别尝试")

            img = self._adb_screenshot()
            if img is None:
                logger.warning("截图失败，重试。")
                time.sleep(0.5)
                continue

            self._blocks = self._find_blocks(img)
            if len(self._blocks) < 4:
                logger.warning(
                    f"识别到的候选块不足（{len(self._blocks)}），重试。"
                )
                time.sleep(0.5)
                continue

            self._pair, score = self._find_same_pair(img, self._blocks)

            if not self._pair or score < SIMILARITY_THRESHOLD:
                logger.warning(
                    f"未找到足够相似的图片，相似度={score:.3f}"
                )
                time.sleep(0.5)
                continue

            logger.info(
                f"成功匹配到相同图片 {self._pair}，相似度={score:.3f}"
            )

            # 执行拖拽
            i, j = self._pair
            xi, yi, wi, hi = self._blocks[i]
            xj, yj, wj, hj = self._blocks[j]

            sx, sy = xi + wi // 2, yi + hi // 2
            tx, ty = xj + wj // 2, yj + hj // 2

            self._adb_drag(sx, sy, tx, ty)
            self._matched = True
            break

        if not self._matched:
            logger.error(
                f"达到最大重试次数 ({MAX_RETRY_ATTEMPTS})，未能完成匹配拖拽。"
            )
            return CustomAction.RunResult(success=False)

        logger.info("AutoMatchDrag 任务执行完成。")
        return CustomAction.RunResult(success=True)
