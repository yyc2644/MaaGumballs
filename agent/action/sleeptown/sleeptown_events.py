from typing import TYPE_CHECKING

from maa.context import Context

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownEventDispatcher:
    """沉眠小镇地图事件分发器。

    预留梦境交易商、沉睡者之床、月亮秋千和清醒药剂处理入口。
    """

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    def handle_dream_trader(self, context: Context, image) -> bool:
        return False

    def handle_sleeper_bed(self, context: Context, image) -> bool:
        return False

    def handle_moon_swing(self, context: Context, image) -> bool:
        return False

    def handle_events(self, context: Context, image=None) -> bool:
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        handlers = (
            self.handle_dream_trader,
            self.handle_sleeper_bed,
            self.handle_moon_swing,
        )
        return any(handler(context, image) for handler in handlers)
