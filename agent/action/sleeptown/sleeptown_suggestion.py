import time
from typing import Final

from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger


SUGGESTION_ANCHOR_NODE: Final = "Sleeptown_Suggestion_Anchor"
SUGGESTION_BACK_NODE: Final = "Sleeptown_Suggestion_Back"
SUGGESTION_REFERENCE_ANCHOR: Final = (360, 690)
SUGGESTION_NODE_OFFSETS: Final = {
    "B1": (-132, -264),
    "B2": (-132, -179),
    "B3": (-239, -147),
    "B4": (-101, -128),
    "B5": (-85, -58),
    "B6": (-210, -41),
    "B7": (-152, -41),
    "B8": (-286, 0),
    "P1": (136, -264),
    "P2": (135, -179),
    "P3": (243, -147),
    "P4": (104, -128),
    "P5": (87, -58),
    "P6": (156, -41),
    "P7": (214, -41),
    "P8": (289, 0),
    "G1": (0, 92),
    "G2": (-51, 144),
    "G3": (50, 144),
    "G4": (-80, 194),
    "G5": (79, 194),
    "G6": (-153, 239),
    "G7": (152, 239),
    "G8": (0, 275),
}


class SleeptownSuggestionPathValidation(CustomAction):
    """验证心理暗示页面的锚点相对坐标点击方式。"""

    validation_sequence: Final = ("B5", "B4", "B2", "B1")

    @staticmethod
    def _locate_anchor(context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        result = context.run_recognition(SUGGESTION_ANCHOR_NODE, image)
        if not result.hit:
            logger.error("心理暗示验证失败：未识别到中央螺旋锚点")
            return None

        box = result.box
        anchor = (box.x + box.w // 2, box.y + box.h // 2)
        logger.info(
            f"心理暗示锚点：box=({box.x},{box.y},{box.w},{box.h})，"
            f"center={anchor}"
        )
        return anchor

    @staticmethod
    def _is_suggestion_page(context: Context) -> bool:
        image = context.tasker.controller.post_screencap().wait().get()
        return bool(context.run_recognition(SUGGESTION_ANCHOR_NODE, image).hit)

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        logger.info(
            "开始验证心理暗示相对坐标流程："
            + " -> 返回 -> ".join(self.validation_sequence)
            + " -> 返回"
        )

        for node_name in self.validation_sequence:
            if context.tasker.stopping:
                logger.warning("心理暗示验证被停止")
                return CustomAction.RunResult(success=False)

            anchor = self._locate_anchor(context)
            if anchor is None:
                return CustomAction.RunResult(success=False)

            dx, dy = SUGGESTION_NODE_OFFSETS[node_name]
            click_x = anchor[0] + dx
            click_y = anchor[1] + dy
            logger.info(
                f"点击 {node_name}：anchor={anchor}，offset=({dx},{dy})，"
                f"target=({click_x},{click_y})"
            )
            context.tasker.controller.post_click(click_x, click_y).wait()
            time.sleep(1.5)

            if self._is_suggestion_page(context):
                logger.error(f"点击 {node_name} 后仍停留在心理暗示总览，停止验证")
                return CustomAction.RunResult(success=False)

            logger.info(f"{node_name} 详情页已打开，执行 MAA 返回节点")
            if not context.run_task(SUGGESTION_BACK_NODE):
                logger.error(f"{node_name} 详情页返回失败")
                return CustomAction.RunResult(success=False)
            time.sleep(1.0)

            if not self._is_suggestion_page(context):
                logger.error(f"{node_name} 返回后未重新识别到心理暗示锚点")
                return CustomAction.RunResult(success=False)

        logger.info("心理暗示 B5/B4/B2/B1 相对坐标流程验证完成")
        return CustomAction.RunResult(success=True)
