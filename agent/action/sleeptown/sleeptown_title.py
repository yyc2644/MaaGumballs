from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownTitleManager:
    """
    沉眠小镇称号路线：
    1.第一次到49,把位面相关的都点了
    2.第二次到49,优先点出恶魔系4级称号,战斗系大剑师,冒险系武器大师
    3.第三次到49,查缺补漏,恶魔系5级称号点满,其他三系基础称号点满
    4.吃完退退退,且到达50层时,点出最终称号
    """

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown
        self.magic_route_checked = False
        self.demon_route_checked = False
        self.third_visit_titles_checked = False

    @timing_decorator
    def check_default_title(self, context: Context):
        if self.sleeptown.layers < 49:
            return False

        handled = False
        if not self.magic_route_checked:
            self.ensure_plane_prophet_titles(context)
            self.magic_route_checked = True
            handled = True

        visit_count = self.sleeptown.state.floor49_visit_count
        if visit_count >= 2 and not self.demon_route_checked:
            self.ensure_demon_titles(context)
            self.demon_route_checked = True
            handled = True

        if visit_count >= 3 and not self.third_visit_titles_checked:
            self.ensure_third_visit_titles(context)
            self.third_visit_titles_checked = True
            handled = True

        if handled:
            context.run_task("Fight_ReturnMainWindow")
        return handled

    def ensure_plane_prophet_titles(self, context: Context) -> bool:
        logger.info(
            f"沉眠小镇第{self.sleeptown.layers}层：确认位面先知称号路线"
        )
        # This is intentionally the same route and expected levels used by
        # Mars. The title helpers are safe to call when a title is already
        # learned: the pipeline only clicks learnable entries.
        fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
        fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
        fightUtils.title_learn("魔法", 3, "咒术师", 2, context)
        fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
        fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
        fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
        fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
        fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
        fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
        return True

    def ensure_demon_titles(self, context: Context) -> bool:
        logger.info("点了恶魔")
        fightUtils.title_learn("恶魔", 1, "堕落者", 1, context)
        fightUtils.title_learn("恶魔", 2, "下位恶魔", 1, context)
        fightUtils.title_learn("恶魔", 3, "中位恶魔", 1, context)
        fightUtils.title_learn("恶魔", 4, "上位恶魔", 3, context)
        fightUtils.title_learn("恶魔", 5, "恶魔大领主", 1, context)
        fightUtils.title_learn_branch("恶魔", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("恶魔", 5, "攻击强化", 3, context, repeatable=True)
        fightUtils.title_learn_branch("恶魔", 5, "生命强化", 3, context)
        return True

    def ensure_third_visit_titles(self, context: Context) -> bool:
        """Third visit to floor 49: finish Great Sword Master and Weapon Master."""
        logger.info("沉眠小镇第三次到达49层：确认战斗系与冒险系称号")

        # Match the Mars route through tier 4 and finish Great Sword Master.
        fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
        fightUtils.title_learn("战斗", 2, "战士", 3, context)
        fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
        fightUtils.title_learn("战斗", 4, "大剑师", 3, context)

        # Mars reaches Weapon Master through the Rune Master branch. Ensure
        # the prerequisite route before raising Weapon Master to level 3.
        fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
        fightUtils.title_learn("冒险", 2, "勘探家", 2, context)
        fightUtils.title_learn("冒险", 3, "锻造师", 3, context)
        fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
        return True
    
    def final_titles(self,context: Context) -> bool:
        logger.info("沉眠小镇最终称号点出")
        fightUtils.title_learn("战斗", 5, "剑圣", 1, context)
        fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
        fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
        fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
        return True
