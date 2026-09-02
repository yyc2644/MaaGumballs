from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardSettlementManager:
    """Mark settlement only after the configured floor is cleared."""

    def __init__(self, card: "Card1201") -> None:
        self.card = card

    def handle_before_leave_maze_event(self, context: Context):
        if self.card.layers < self.card.config.target_leave_layer:
            return False
        logger.info(
            f"卡牌幻境已清理目标{self.card.config.target_leave_layer}层，准备结算"
        )
        context.run_task("Fight_ReturnMainWindow")
        context.run_task("Screenshot")
        self.card.isLeaveMaze = True
        return True
