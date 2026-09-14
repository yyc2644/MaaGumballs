from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91TitleManager:
    """91-1201 称号路线处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def check_default_title(self, context: Context) -> bool:
        del context
        logger.debug(f"91-1201 第{self.map91.layers}层：暂无专用称号路线")
        return True
