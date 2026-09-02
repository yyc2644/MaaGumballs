from typing import TYPE_CHECKING

from maa.context import Context
from utils import logger, send_message

from action.fight import fightProcessor
from action.fight import fightUtils

import time

DOWNSTAIR_LAYER_CHANGE_MAX_ATTEMPTS = 5
DOWNSTAIR_LAYER_CHANGE_SLEEP_SECONDS = 1
KEYHOLE_POLL_SECONDS = 3

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101


class FightDownstairManager:
    """通用下楼处理器：负责点击门、洞穴等待与层数变化确认"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars
        self.processor = fightProcessor.FightProcessor()

    def _wait_until_layer_changed(self, context: Context, old_layer: int):
        attempts = 0
        current_layer = old_layer

        if old_layer <= 0:
            logger.warning("下楼前层数无效，不能据此判断层数变化")
            return False, current_layer, attempts

        with fightUtils.timing_section("post.downstair.wait_change_total"):
            for _ in range(DOWNSTAIR_LAYER_CHANGE_MAX_ATTEMPTS):
                attempts += 1
                with fightUtils.timing_section("post.downstair.wait_change_iter"):
                    with fightUtils.timing_section("post.downstair.layer_after"):
                        current_layer = fightUtils.handle_currentlayer_event(context)
                if current_layer > 0 and old_layer != current_layer:
                    return True, current_layer, attempts
                with fightUtils.timing_section("post.downstair.wait_change_sleep"):
                    time.sleep(DOWNSTAIR_LAYER_CHANGE_SLEEP_SECONDS)

        return False, current_layer, attempts

    def _click_door_target(self, context: Context, target: tuple[int, int] | None):
        if target is None:
            return False

        context.tasker.controller.post_click(target[0], target[1]).wait()
        return True

    def _save_status_before_keyhole_notice(self, context: Context):
        logger.info("检测到神秘洞穴, 先暂离保存并返回迷宫")
        context.run_task("Save_Status")
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 300}}
            },
        )

        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            logger.info("暂离返回后已检测到开门, 继续下楼")
            context.run_task("Fight_OpenedDoor")
            return True
        return False

    def handle_downstair_event(self, context: Context):
        downstair_result = "door_not_detected"
        downstair_branch = "cached_processor_door"
        current_layer = -1
        wait_attempts = 0

        temp_layer = fightUtils.handle_currentlayer_event(context)
        if temp_layer <= 0:
            cached_layer = int(getattr(self.mars, "layers", -1))
            if cached_layer > 0:
                logger.warning(
                    f"下楼前OCR层数失败，使用状态机缓存层数{cached_layer}"
                )
                temp_layer = cached_layer
            else:
                logger.error("下楼前无法获得有效层数，本轮不点击楼梯")
                return False

        door_target = self.processor.get_last_door_click_target(temp_layer)
        clicked_door = self._click_door_target(context, door_target)
        if clicked_door:
            downstair_result = "processor_click_sent"

        changed, current_layer, wait_attempts = self._wait_until_layer_changed(
            context, temp_layer
        )
        if changed:
            downstair_result = "changed_confirmed"
            logger.info(
                f"[downstair_result] result={downstair_result} old_layer={temp_layer} new_layer={current_layer} attempts={wait_attempts} branch={downstair_branch}"
            )
            return True

        downstair_branch = "fallback_recognition"
        img = context.tasker.controller.post_screencap().wait().get()
        opened_door_hit = context.run_recognition("Fight_OpenedDoor", img).hit
        if opened_door_hit:
            context.run_task("Fight_OpenedDoor")
            downstair_result = "fallback_opened_door"
        else:
            key_hole_hit = context.run_recognition("FindKeyHole", img).hit
            if key_hole_hit:
                downstair_result = "keyhole_manual_wait"
                logger.warning("检查到神秘的洞穴捏，请冒险者大人检查！！")
                if self._save_status_before_keyhole_notice(context):
                    downstair_result = "keyhole_save_status_opened_door"
                else:
                    logger.info("暂离返回后仍需人工处理神秘洞穴, 开始发送外部通知")
                    fightUtils.send_alert("洞穴警告", "发现神秘洞穴，请及时处理！")
                    send_message("洞穴警告", "发现神秘洞穴，请及时处理！")

                    with fightUtils.timing_section("post.downstair.keyhole_wait_total"):
                        while not context.run_recognition(
                            "Fight_OpenedDoor",
                            context.tasker.controller.post_screencap().wait().get(),
                        ).hit:
                            if context.tasker.stopping:
                                logger.info("检测到停止任务, 开始退出agent")
                                logger.info(
                                    f"[downstair_result] result=stopped_during_keyhole_wait old_layer={temp_layer} new_layer={current_layer} attempts={wait_attempts} branch={downstair_branch}"
                                )
                                return False
                            time.sleep(KEYHOLE_POLL_SECONDS)

                    logger.info("冒险者大人已找到钥匙捏，继续探索")
                    context.run_task("Fight_OpenedDoor")

        changed, current_layer, wait_attempts = self._wait_until_layer_changed(
            context, temp_layer
        )
        if changed:
            downstair_result = "changed_confirmed"
            logger.info(
                f"[downstair_result] result={downstair_result} old_layer={temp_layer} new_layer={current_layer} attempts={wait_attempts} branch={downstair_branch}"
            )
            return True

        logger.info("点击楼梯后层数未改变，本轮返回失败并重新识别")
        downstair_result = "no_change_retry"
        logger.debug(
            f"[downstair_result] result={downstair_result} old_layer={temp_layer} new_layer={current_layer} attempts={wait_attempts} branch={downstair_branch}"
        )
        return False
