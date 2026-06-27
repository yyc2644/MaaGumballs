from typing import TYPE_CHECKING

from maa.context import Context
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardEventDispatcher:
    """卡牌幻境事件分发器：后续统一处理商店、奖励、尸体等事件。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def handle_events(self, context: Context):
        logger.debug("卡牌幻境执行旧脚本转换后的事件搜刮")
        self.card.run_arthur_round_table_script(context)
        self.card.run_guide_building_choice_script(context)
        self.card.run_loot_all_script(context)
        self.card.run_dragon_wish_script(context)
        return True
