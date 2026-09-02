import time
from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.sleeptown1201 import Sleeptown1201


class SleeptownPeriodicManager:
    """Handle the recurring preparation for floors ending in 9."""

    CONSUMABLES = (
        ("佛手", "fight/Sleeptown/Item/佛手.png"),
        ("宝钱", "fight/Sleeptown/Item/宝钱.png"),
        ("柿子", "fight/Sleeptown/Item/柿子.png"),
    )

    COUNTED_ITEMS = (
        ("退退退", "fight/Sleeptown/Item/退退退.png"),
        ("吃瓜群众", "fight/Sleeptown/Item/吃瓜群众.png"),
    )

    NOBLE_SET = (
        ("腰带", 1, "贵族丝带"),
        ("戒指", 2, "礼仪戒指"),
        ("披风", 3, "天鹅绒斗篷"),
    )

    def __init__(self, sleeptown: "Sleeptown1201") -> None:
        self.sleeptown = sleeptown
        self.count_alert_sent = False

    @staticmethod
    def is_periodic_layer(layer: int) -> bool:
        """The requested schedule is 9, 19, 29, 39, ..."""
        return layer >= 9 and layer % 10 == 9

    def handle_pre_layer(self, context: Context) -> bool:
        periodic_layer = self.is_periodic_layer(self.sleeptown.layers)
        should_check_counts = (
            self.sleeptown.layers >= 49 and not self.count_alert_sent
        )
        if not periodic_layer and not should_check_counts:
            return False

        if periodic_layer:
            logger.info(f"沉眠小镇第{self.sleeptown.layers}层：执行尾数9层检查")
            self.check_activity_talent(context)

        context.run_task("Fight_ReturnMainWindow")
        opened = context.run_task("Bag_Open")
        if not getattr(opened, "nodes", None):
            logger.warning("沉眠小镇尾数9层检查：背包打开失败")
            context.run_task("Fight_ReturnMainWindow")
            return False

        try:
            if periodic_layer:
                self.consume_periodic_items(context)
                self.equip_noble_set(context)
            if should_check_counts:
                self.check_target_item_counts(context)
        finally:
            context.run_task("Fight_ReturnMainWindow")
        return True

    def check_activity_talent(self, context: Context) -> bool:
        """TODO: fill in the concrete 活动天赋 choices after they are specified."""
        del context
        logger.info("沉眠小镇活动天赋检查：策略内容待补充，当前跳过")
        return True

    def _return_to_first_bag_page(self, context: Context) -> None:
        # A hard limit prevents a bad recognition result from creating an
        # infinite loop while still covering the observed six-page backpack.
        for _ in range(20):
            image = context.tasker.controller.post_screencap().wait().get()
            previous = context.run_recognition("Bag_ToPrevPage", image)
            if not previous.hit:
                return
            x, y, width, height = previous.best_result.box
            context.tasker.controller.post_click(
                x + width // 2,
                y + height // 2,
            ).wait()
            time.sleep(0.5)
        logger.warning("沉眠小镇背包回到第一页超过20次，停止翻页")

    def _find_and_use_all(
        self,
        context: Context,
        item_name: str,
        template: str,
    ) -> bool:
        found = self._find_item(context, item_name, template)
        if found is None:
            return False

        detail, _ = found
        x, y, width, height = detail.best_result.box
        context.tasker.controller.post_click(
            x + width // 2,
            y + height // 2,
        ).wait()
        time.sleep(0.8)

        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Bag_LoadAllItem", image).hit:
            context.run_task("Bag_LoadAllItem")
        elif context.run_recognition("Bag_LoadItem", image).hit:
            context.run_task("Bag_LoadItem")
        else:
            logger.warning(f"已找到{item_name}，但未识别到使用按钮")
            return False
        logger.info(f"沉眠小镇已使用全部物品：{item_name}")
        return True

    def use_one_item(
        self,
        context: Context,
        item_name: str,
        template: str,
    ) -> bool:
        """在背包中查找并只使用一件指定物品。"""
        context.run_task("Fight_ReturnMainWindow")
        opened = context.run_task("Bag_Open")
        if not getattr(opened, "nodes", None):
            logger.warning(f"使用{item_name}失败：背包打开失败")
            context.run_task("Fight_ReturnMainWindow")
            return False

        try:
            found = self._find_item(context, item_name, template)
            if found is None:
                return False

            detail, _ = found
            x, y, width, height = detail.best_result.box
            context.tasker.controller.post_click(
                x + width // 2,
                y + height // 2,
            ).wait()
            time.sleep(0.8)

            image = context.tasker.controller.post_screencap().wait().get()
            single_button = context.run_recognition("Bag_LoadItem", image)
            if single_button.hit:
                context.run_task("Bag_LoadItem")
            else:
                # 堆叠物品界面的 Bag_LoadAllItem 节点以“使用一次”按钮为
                # 识别锚点，再向左偏移点击“全部使用”。这里直接点击识别框，
                # 从而确保只消耗一件。
                use_once = context.run_recognition("Bag_LoadAllItem", image)
                if not use_once.hit:
                    logger.warning(f"已找到{item_name}，但未识别到单件使用按钮")
                    return False
                bx, by, bw, bh = use_once.best_result.box
                context.tasker.controller.post_click(
                    bx + bw // 2,
                    by + bh // 2,
                ).wait()

            logger.info(f"沉眠小镇已使用一件物品：{item_name}")
            return True
        finally:
            context.run_task("Fight_ReturnMainWindow")

    def _find_item(self, context: Context, item_name: str, template: str):
        self._return_to_first_bag_page(context)

        for _ in range(20):
            image = context.tasker.controller.post_screencap().wait().get()
            detail = context.run_recognition(
                "Bag_FindItem",
                image,
                pipeline_override={
                    "Bag_FindItem": {
                        "template": template,
                        "threshold": 0.9,
                        "action": "DoNothing",
                    }
                },
            )
            if detail.hit:
                logger.info(f"沉眠小镇背包已找到：{item_name}")
                return detail, image

            if context.run_recognition("Bag_ToNextPage", image).hit:
                context.run_task("Bag_ToNextPage")
                time.sleep(0.5)
                continue

            logger.info(f"沉眠小镇背包未找到：{item_name}")
            return None

        logger.warning(f"沉眠小镇查找{item_name}超过20页，停止翻页")
        return None

    def _read_item_count(
        self,
        context: Context,
        item_name: str,
        template: str,
    ) -> int:
        found = self._find_item(context, item_name, template)
        if found is None:
            return 0

        detail, image = found
        x, y, width, _ = detail.best_result.box
        # The reusable item template excludes the dynamic top-right badge.
        # Its count sits immediately above and to the right of the 60x60
        # match. This ROI covers one-to-three digit counts without including
        # the neighboring cell.
        roi = [max(0, x + width - 10), max(0, y - 24), 44, 32]
        count_detail = context.run_recognition(
            "Sleeptown_ItemCount",
            image,
            pipeline_override={"Sleeptown_ItemCount": {"roi": roi}},
        )
        if count_detail.hit:
            results = getattr(count_detail, "filtered_results", None) or []
            if not results and getattr(count_detail, "best_result", None):
                results = [count_detail.best_result]
            for result in results:
                count = fightUtils.extract_num(getattr(result, "text", ""))
                if count > 0:
                    return count

        # A single item has no numeric badge in the backpack UI.
        logger.info(f"{item_name}未显示数量角标，按单件处理")
        return 1

    @staticmethod
    def _count_alert_text(counts: dict[str, int]) -> str:
        lines = []
        for item_name in ("退退退", "吃瓜群众"):
            count = counts[item_name]
            status = "已达标" if count >= 3 else "不足3个"
            lines.append(f"{item_name}：{count}（{status}）")
        return "\n".join(lines)

    def check_target_item_counts(self, context: Context) -> dict[str, int]:
        counts = {
            item_name: self._read_item_count(context, item_name, template)
            for item_name, template in self.COUNTED_ITEMS
        }
        message = self._count_alert_text(counts)
        logger.info(f"沉眠小镇49层道具数量检查：\n{message}")
        fightUtils.send_alert("沉眠小镇49层道具检查", message)
        self.count_alert_sent = True
        return counts

    def consume_periodic_items(self, context: Context) -> None:
        for item_name, template in self.CONSUMABLES:
            self._find_and_use_all(context, item_name, template)

    def equip_noble_set(self, context: Context) -> None:
        for slot, level, equipment_name in self.NOBLE_SET:
            if fightUtils.checkEquipment(slot, level, equipment_name, context):
                continue
            if not fightUtils.findEquipment(level, equipment_name, True, context):
                logger.info(f"沉眠小镇背包没有贵族套装部件：{equipment_name}")
