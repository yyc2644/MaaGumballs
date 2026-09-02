from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardTitleManager:
    """Card title route recovered from the older Card branch."""

    def __init__(self, card: "Card1201") -> None:
        self.card = card
        self.initial_done = False
        self.plane_done = False
        self.enchanter_done = False
        self.dragon_done = False

    def _return(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")

    def Check_DefaultTitle(self, context: Context):
        layer = self.card.layers
        if layer <= 3 and not self.initial_done:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 3, context)
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            self.initial_done = True
            self._return(context)
            return True

        if layer >= 39 and not self.plane_done:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面法师", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            self.plane_done = True
            self._return(context)
            return True

        if layer >= 63 and not self.enchanter_done:
            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "锻造师", 1, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 1, context)
            fightUtils.title_learn("冒险", 5, "大附魔师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            self.enchanter_done = True
            self._return(context)
            return True

        if layer >= 69 and not self.dragon_done:
            has_dragon_title = self.card.state.has_dragon_power or fightUtils.title_check(
                "巨龙", context
            )
            if not has_dragon_title:
                logger.debug("尚未获得巨龙系称号，稍后楼层继续检查")
                self._return(context)
                return False
            fightUtils.title_learn("巨龙", 1, "亚龙血统", 2, context)
            fightUtils.title_learn("巨龙", 2, "初级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 3, "中级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 4, "高级龙族血统", 1, context)
            self.dragon_done = True
            self._return(context)
            return True
        return False
