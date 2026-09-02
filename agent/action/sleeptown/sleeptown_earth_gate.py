import time
from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownEarthGateManager:
    """沉眠小镇大地之门检测与回层,只在49层回退。"""

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    def should_try(self) -> bool:
        state = self.sleeptown.state
        return (
            self.sleeptown.layers == 49
            # and self.sleeptown.layers % 10 == 9
            and state.earth_gate_checked_layer != self.sleeptown.layers
        )

    def handle_earth_gate_event(self, context: Context):
        if not self.should_try():
            return False

        current_layer = self.sleeptown.layers
        self.sleeptown.state.earth_gate_checked_layer = current_layer
        context.run_task("Fight_ReturnMainWindow")
        if not fightUtils.check_magic("土", "大地之门", context):
            logger.warning("没有找到大地之门")
            return False
        if not fightUtils.check_magic("气", "静电场", context):
            logger.warning("没有找到静电场")
            return False
        fightUtils.cast_magic("气", "静电场", context)
        fightUtils.cast_magic("土", "大地之门", context)
        for _ in range(15):
            time.sleep(1)
            if self.sleeptown.check_current_layers(context) and self.sleeptown.layers != current_layer:
                self.sleeptown.state.preprocessed_layer = -1
                logger.info(f"沉眠小镇大地之门完成：{current_layer}层 -> {self.sleeptown.layers}层")
                return True
        logger.warning("沉眠小镇等待大地之门后层数未变化")
        return False
