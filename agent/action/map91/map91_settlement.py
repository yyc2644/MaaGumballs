from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91SettlementManager:
    """91-1201 结算处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def handle_before_leave_maze_event(self, context: Context) -> bool:
        del context
        if self.map91.layers < self.map91.config.target_leave_layer:
            return True
        logger.info(f"91-1201 已到达目标{self.map91.config.target_leave_layer}层，准备结算")
        self.map91.is_leave_maze = True
        return True
