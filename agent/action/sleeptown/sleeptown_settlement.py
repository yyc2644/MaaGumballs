from typing import TYPE_CHECKING

from maa.context import Context
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownSettlementManager:
    """仅在目标层完整清理后标记结算。"""

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    def handle_before_leave_maze_event(self, context: Context):
        if self.sleeptown.layers < self.sleeptown.config.target_leave_layer:
            return False
        logger.info(
            f"沉眠小镇已清理目标{self.sleeptown.config.target_leave_layer}层，准备结算"
        )
        context.run_task("Fight_ReturnMainWindow")
        context.run_task("Screenshot")
        self.sleeptown.is_leave_maze = True
        return True
