from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardHPManager:
    """Conservative healing and revival-buff management for long runs."""

    def __init__(self, card: "Card1201") -> None:
        self.card = card

    @staticmethod
    def _hp_ratio(status) -> float:
        try:
            current = float(status["当前生命值"])
            maximum = float(status["最大生命值"])
            return current / maximum if maximum > 0 else 1.0
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return 1.0

    def Check_DefaultStatus(self, context: Context):
        layer_mod = self.card.layers % 10
        should_check = self.card.layers >= 80 or layer_mod in (1, 5, 9)
        if not should_check:
            return True

        status = fightUtils.checkGumballsStatusV2(context)
        ratio = self._hp_ratio(status)
        logger.debug(f"卡牌幻境当前生命比例：{ratio:.1%}")
        if ratio < 0.7:
            for magic_type, magic_name in [
                ("水", "治疗术"),
                ("光", "神恩术"),
                ("水", "痊愈术"),
            ]:
                if fightUtils.cast_magic(magic_type, magic_name, context):
                    status = fightUtils.checkGumballsStatusV2(context)
                    ratio = self._hp_ratio(status)
                    if ratio >= 0.8:
                        break

        if self.card.layers >= 51 and not fightUtils.checkBuffStatus(
            "神圣重生", context
        ):
            fightUtils.cast_magic("光", "神圣重生", context)
        context.run_task("Fight_ReturnMainWindow")
        return True
