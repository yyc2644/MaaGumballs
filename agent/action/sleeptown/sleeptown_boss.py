from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


BOSS_POS = (360, 800)


class SleeptownBossHandler:
    """沉眠小镇 Boss 层处理器。"""

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown

    @staticmethod
    def _wait_for_animation(context: Context, milliseconds: int = 300) -> None:
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {
                    "pre_wait_freezes": {"time": milliseconds}
                }
            },
        )

    @staticmethod
    def _is_boss_defeated(context: Context) -> bool:
        image = context.tasker.controller.post_screencap().wait().get()
        return bool(context.run_recognition("Fight_CheckBossStatus", image).hit)

    def _normal_attack(self, context: Context) -> bool:
        """平 A 一次，并返回本次攻击后 Boss 是否已经死亡。"""
        context.tasker.controller.post_click(*BOSS_POS).wait()
        self._wait_for_animation(context)
        return self._is_boss_defeated(context)

    def _handle_floor_30(self, context: Context) -> bool:
        logger.info("沉眠小镇30层 Boss：持续平 A")
        for _ in range(40):
            if self._normal_attack(context):
                return True
        logger.warning("沉眠小镇30层 Boss：40次平 A 后仍未识别到下楼门")
        return False

    def _handle_floor_40(self, context: Context) -> bool:
        logger.info("沉眠小镇40层 Boss：静电场、瓦解射线、冰锥术、平 A 三次循环")
        for _ in range(15):
            if not fightUtils.cast_magic("气", "静电场", context):
                return False
            if not fightUtils.cast_magic("气", "瓦解射线", context, BOSS_POS):
                return False
            if not fightUtils.cast_magic("水", "冰锥术", context, BOSS_POS):
                return False

            for _ in range(3):
                if self._normal_attack(context):
                    return True

        logger.warning("沉眠小镇40层 Boss：15轮循环后仍未识别到下楼门")
        return False

    def _handle_floor_50_placeholder(self, context: Context) -> bool:
        """50层 Boss 策略占位，补齐截图/录屏后再启用。

        伪代码：
        while boss_alive:
            hp = read_current_hp_ratio()
            if hp <= near_death_threshold:
                normal_attack_boss_until_dead()
                break
            if can_cast_blessing():
                cast_blessing()
            elif has_configured_consumable():
                use_configured_consumable()
            else:
                stop_and_alert_user()
            wait_for_boss_attack_and_refresh_hp()

        待确认参数：濒死血量阈值、可用道具名称/优先级、Boss攻击结算时机，
        以及祝福术无法施放时的界面表现。未确认前必须返回 False，不能用平 A
        兜底，以免不可逆地结束 Boss 战。
        """
        del context
        logger.warning(
            "沉眠小镇50层 Boss 策略尚未启用：等待血量阈值、道具和回合截图/录屏"
        )
        return False

    def handle_boss_event(self, context: Context) -> bool:
        if self._is_boss_defeated(context):
            return True

        layer = self.sleeptown.layers
        if layer == 30:
            return self._handle_floor_30(context)
        if layer == 40:
            return self._handle_floor_40(context)
        if layer == 50:
            return self._handle_floor_50_placeholder(context)

        logger.info(f"沉眠小镇第{layer}层：暂无专用 Boss 策略，沿用普通清层")
        return bool(self.sleeptown.clear_current_layer(context))
