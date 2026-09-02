from typing import TYPE_CHECKING

from maa.context import Context

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownSpecialLayerManager:
    """梦境入口、梦境内部流程和离开梦境的统一入口。"""

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    def handle_special_layer_event(self, context: Context, image=None):
        # 地图模板补齐后，在这里接入进入梦境、梦境清层和离开梦境任务。
        return False
