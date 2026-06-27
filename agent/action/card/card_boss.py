from typing import TYPE_CHECKING

from maa.context import Context
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardBossHandler:
    """卡牌幻境 Boss 处理器：后续在这里补充 Boss 层策略。"""

    def __init__(self, card: "Card1201") -> None:
        self.card: "Card1201" = card

    def handle_boss_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True

        logger.info("卡牌幻境 Boss 层使用旧按键精灵脚本转换流程")
        return self.card.run_boss_layer_script(context)
