from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91EarthGateManager:
    """91-1201 大地之门处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def handle_earth_gate_event(self, context: Context) -> bool:
        state = self.map91.state
        if (
            self.map91.layers < 49
            or self.map91.layers % 10 != 9
            or state.earth_gate_checked_layer == self.map91.layers
        ):
            return False

        current_layer = self.map91.layers
        state.earth_gate_checked_layer = current_layer
        context.run_task("Fight_ReturnMainWindow")
        if not fightUtils.check_magic("土", "大地之门", context):
            logger.info(f"91-1201 第{current_layer}层未检测到大地之门")
            context.run_task("Fight_ReturnMainWindow")
            return False

        logger.info(f"91-1201 第{current_layer}层检测到大地之门，暂不自动施放")
        context.run_task("Fight_ReturnMainWindow")
        return False
