from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownHPManager:
    """
    探索中的保守治疗与复活状态维护。
    策略1:血量低于20%,放4次石榴,再吃20个卷轴
    策略2:2次大地后,需要长时间压血,此时不回复生命值,依靠冰盾拖回合
    """

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    @staticmethod
    def _hp_ratio(status) -> float:
        try:
            current = float(status["当前生命值"])
            maximum = float(status["最大生命值"])
            return current / maximum if maximum > 0 else 1.0
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return 1.0

    def check_default_status(self, context: Context):
        if self.sleeptown.layers < 80 and self.sleeptown.layers % 10 not in (1, 5, 9):
            return True

        status = fightUtils.checkGumballsStatusV2(context)
        ratio = self._hp_ratio(status)
        logger.debug(f"沉眠小镇当前生命比例：{ratio:.1%}")
        if ratio < 0.7:
            for magic_type, magic_name in (
                ("水", "治疗术"),
                ("光", "神恩术"),
                ("水", "痊愈术"),
            ):
                if fightUtils.cast_magic(magic_type, magic_name, context):
                    break
        context.run_task("Fight_ReturnMainWindow")
        return True
