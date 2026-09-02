from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardSpecialLayerManager:
    """Seal-book equipment checks and lightweight special-event upkeep."""

    def __init__(self, card: "Card1201") -> None:
        self.card = card
        self.has_seal_book = False
        self.last_equipment_check_layer = -1

    def ensure_seal_book(self, context: Context):
        if self.has_seal_book:
            return True
        opened = context.run_task("Bag_Open")
        if not opened or not opened.nodes:
            logger.warning("卡牌幻境无法打开背包，暂不检查封印之书")
            context.run_task("Fight_ReturnMainWindow")
            return False
        self.has_seal_book = fightUtils.checkEquipment(
            "宝物", 7, "封印之书", context
        )
        if not self.has_seal_book:
            self.has_seal_book = bool(
                fightUtils.findEquipment(7, "封印之书", True, context)
            )
        logger.info(
            "卡牌幻境封印之书状态："
            + ("已装备" if self.has_seal_book else "尚未获得")
        )
        context.run_task("Fight_ReturnMainWindow")
        return self.has_seal_book

    def handle_special_layer_event(self, context: Context):
        # Re-check at boss preparation floors without reopening the bag every floor.
        if (
            not self.has_seal_book
            and self.card.layers % 10 == 9
            and self.last_equipment_check_layer != self.card.layers
        ):
            self.last_equipment_check_layer = self.card.layers
            self.ensure_seal_book(context)
        return True
