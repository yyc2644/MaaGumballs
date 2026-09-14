from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91SpecialLayerManager:
    """91-1201 特殊层处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def handle_special_layer_event(self, context: Context, image=None) -> bool:
        del context, image
        logger.debug(f"91-1201 第{self.map91.layers}层：暂无特殊层事件")
        return False
