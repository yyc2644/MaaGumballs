from typing import TYPE_CHECKING

from maa.context import Context

from utils import logger

if TYPE_CHECKING:
    from action.fight.map91 import Map91


class Map91HPManager:
    """91-1201 血量与生存状态处理器。"""

    def __init__(self, map91: "Map91") -> None:
        self.map91 = map91

    def check_default_status(self, context: Context) -> bool:
        del context
        logger.debug(f"91-1201 第{self.map91.layers}层：暂无专用生存检查")
        return True
