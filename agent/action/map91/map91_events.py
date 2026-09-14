from typing import TYPE_CHECKING
import time

from maa.context import Context

from utils import logger
from action.fight import fightUtils

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91EventDispatcher:
    """91-1201 普通层搜刮事件分派器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    @classmethod
    def reset_runtime_state(cls) -> None:
        """Reset any class-level caches once map-specific events are added."""

    def handle_events(self, context: Context, image=None) -> bool:
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if self.handle_vending_shop_event(context, image):
            return True
        return False

    def handle_vending_shop_event(self, context: Context, image=None) -> bool:
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        reco = context.run_recognition("Map91_VendingShop", image)
        if not reco or not reco.hit:
            return False

        logger.info(f"91-1201 第{self.map91.layers}层：识别到售货机，开始购买一轮商品")
        box = reco.best_result.box
        context.tasker.controller.post_click(
            box[0] + box[2] // 2,
            box[1] + box[3] // 2,
        ).wait()
        time.sleep(0.8)

        product_points = [
            (173, 584),
            (343, 584),
            (513, 584),
            (173, 804),
            (343, 804),
            (513, 804),
        ]
        for index, (x, y) in enumerate(product_points, start=1):
            if context.tasker.stopping:
                return True
            logger.info(f"91-1201 售货机：尝试购买第{index}个商品")
            context.tasker.controller.post_click(x, y).wait()
            time.sleep(0.35)
            image_after_click = context.tasker.controller.post_screencap().wait().get()
            if not fightUtils.click_text_by_priority(
                context,
                ["确认购买"],
                expected=["确认购买"],
                roi=[120, 650, 500, 330],
                image=image_after_click,
                desc="售货机确认购买",
            ):
                logger.info(f"91-1201 售货机：第{index}个商品未出现确认购买，跳过")
            time.sleep(0.4)

        if not context.run_task("BackText_500ms"):
            fightUtils.click_text_by_priority(
                context,
                ["返回"],
                expected=["返回"],
                roi=[480, 1130, 220, 120],
                desc="售货机返回",
            )
        time.sleep(0.5)
        context.run_task("Fight_ReturnMainWindow")
        logger.info("91-1201 售货机：一轮商品处理完成")
        return True
