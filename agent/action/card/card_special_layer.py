from typing import TYPE_CHECKING

from maa.context import Context

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardSpecialLayerManager:
    """卡牌幻境特殊层管理器：后续补充特殊层进入、处理和离开逻辑。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def handle_special_layer_event(self, context: Context):
        return True
