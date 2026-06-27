from typing import TYPE_CHECKING

from maa.context import Context

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardTitleManager:
    """卡牌幻境称号管理器：后续补充自动点称号策略。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def Check_DefaultTitle(self, context: Context):
        return True
