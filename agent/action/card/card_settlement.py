from typing import TYPE_CHECKING

from maa.context import Context
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardSettlementManager:
    """卡牌幻境结算管理器：后续补充出图前的卡牌幻境专属结算。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def handle_before_leave_maze_event(self, context: Context):
        logger.info("触发卡牌幻境结算事件")
        context.run_task("Fight_ReturnMainWindow")
        self.card.isLeaveMaze = True
        return True
