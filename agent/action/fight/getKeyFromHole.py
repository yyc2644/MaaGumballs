from __future__ import annotations

import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from action.fight.hidden_cave import (
    HiddenCaveSolver,
    drag_key_to_target,
)
from utils import logger


# 识别重试：刚进洞时可能还在播动画
ANALYZE_ATTEMPTS = 4
ANALYZE_INTERVAL = 1.0
# 拖拽结束后等待画面稳定
DRAG_SETTLE = 0.6
# 总轮数：每轮"识别 → 拖第一个候选 → 校验重合"，失败则 OCR 点"返回"
# 重新进洞再来一轮；3 轮都不达标就返回失败，交由人工处理
TOTAL_ROUNDS = 3


@AgentServer.custom_action("GetKeyFromHole_Test")
class GetKeyFromHole_Test(CustomAction):
    """神秘洞穴取钥匙：进洞 → 识别真卷轴与剪影 → 拖拽 → 确定。

    识别逻辑在 :class:`action.fight.hidden_cave.HiddenCaveSolver`。拖拽后的
    刚体残差达标时，通过 OCR 识别并点击“确定”，随后把成功结果交回主流程。
    """

    def _solve(self, context: Context):
        self._last_image = None
        solver = HiddenCaveSolver()
        for attempt in range(1, ANALYZE_ATTEMPTS + 1):
            image = context.tasker.controller.post_screencap().wait().get()
            solution = solver.analyze(image)
            if solution is not None:
                # 拖拽校验需要识别时的参考截图（剪影掩码取自该帧）
                self._last_image = image
                return solution
            logger.warning(f"洞穴拼图第{attempt}次识别失败，稍后重试")
            time.sleep(ANALYZE_INTERVAL)
        return None

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 总流程：识别 → 拖第一个候选 → 重合验证。失败（含程序卡住）时
        # OCR 找"返回"点击退出，重新进洞识别后再试一轮；共 3 轮。
        for attempt in range(1, TOTAL_ROUNDS + 1):
            if attempt > 1:
                logger.warning(f"第{attempt - 1}轮失败，OCR 点返回后重新进洞重试")
                backed = context.run_task("BackText")
                logger.info(f"卡住恢复-OCR点击返回: {bool(backed and backed.status.succeeded)}")
                time.sleep(1.0)

            # 1. 点开洞穴入口；调试入口允许模拟器已经停在洞穴界面
            entry = context.run_task("FindKeyHole")
            logger.info(f"洞穴入口识别: {bool(entry and entry.status.succeeded)}")

            # 2. 识别真卷轴与目标剪影
            solution = self._solve(context)
            if solution is None:
                logger.warning("洞穴拼图无法可靠识别，准备恢复流程重试")
                continue

            # 3. 分段慢拖 + 刚体残差校验，必要时自动微调
            aligned, residual = drag_key_to_target(
                context, solution, self._last_image
            )
            logger.info(
                f"洞穴取钥匙拖拽: {solution.source}{solution.source_point} -> "
                f"{solution.target}{solution.target_point} "
                f"mode={solution.mode} confidence={solution.confidence:.2f} "
                f"重合={'达标' if aligned else '未达标'} 最优残差={residual:.0f}px"
            )
            time.sleep(DRAG_SETTLE)

            # 4. 重合达标后 OCR 点击“确定”，成功后交回主流程继续开门下楼
            if aligned:
                confirmed = context.run_task("ClickConfirmForKey")
                if confirmed and confirmed.status.succeeded:
                    logger.info("重合验证通过，OCR 已点击确定，返回主流程")
                    return CustomAction.RunResult(success=True)
                logger.warning("重合验证通过，但 OCR 未识别到确定按钮，准备重试")
                continue
            logger.warning("重合验证未达标（已自动微调仍不足），准备返回重试")

        logger.warning(
            f"共尝试 {TOTAL_ROUNDS} 轮仍未重合达标，放弃自动取钥匙，请人工处理"
        )
        return CustomAction.RunResult(success=False)
