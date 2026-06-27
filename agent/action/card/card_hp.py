from typing import TYPE_CHECKING

from maa.context import Context

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardHPManager:
    """卡牌幻境血量管理器：后续补充治疗、护盾、复活等策略。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def Check_DefaultStatus(self, context: Context):
        return True
