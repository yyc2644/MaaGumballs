from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91BossHandler:
    """91-1201 Boss 层处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def handle_boss_event(self, context: Context) -> bool:
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_CheckBossStatus", image).hit:
            return True

        logger.info(f"91-1201 第{self.map91.layers}层：暂无专用 Boss 策略，沿用普通清层")
        return bool(self.map91.clear_current_layer(context))
