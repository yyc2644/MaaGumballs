import time
from typing import TYPE_CHECKING

from maa.context import Context

from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.card1201 import Card1201


class CardEventDispatcher:
    """Resolve one visible Card event and let the outer loop re-scan the floor."""

    SAFE_CHOICES = [
        "交流",
        "放过",
        "探索洞穴",
        "探索",
        "砍伐",
        "砸碎",
        "紧逼",
        "拓印符号",
        "手牌上限",
        "抽牌冷却",
        "抽牌数量",
        "翻找",
        "查看",
        "刻上名字",
        "离开",
    ]

    ROUND_TABLE_TOPICS = [
        "所有魔法效果",
        "全部魔法效果",
        "伤害类魔法效果",
        "电系魔法效果",
        "电系魔法",
        "气系魔法效果",
        "气系魔法",
        "静电场",
        "闪电术",
        "召唤物攻击",
        "召唤物生命",
        "召唤物",
    ]

    def __init__(self, card: "Card1201") -> None:
        self.card = card
        self.handled_shop_layers: set[int] = set()

    def _handle_skill_shop(self, context: Context, image) -> bool:
        if self.card.layers in self.handled_shop_layers:
            return False
        detail = context.run_recognition("Fight_SkillShop", image)
        if not detail or not detail.hit:
            return False

        # Card floors may expose several SHOP buildings. Open at most one per
        # visit, identify it after opening, and never let an optional shop block
        # combat/downstairs indefinitely.
        self.handled_shop_layers.add(self.card.layers)
        box = detail.best_result.box
        context.tasker.controller.post_click(
            box[0] + box[2] // 2,
            box[1] + box[3] // 2,
        ).wait()
        time.sleep(0.8)

        title = context.run_recognition(
            "Card_Shop_Title",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "Card_Shop_Title": {
                    "recognition": "OCR",
                    "expected": [
                        "卷轴商店",
                        "卡牌商店",
                        "宝物商店",
                        "商店",
                    ],
                    "roi": [120, 250, 480, 260],
                }
            },
        )
        title_text = ""
        if title and title.hit and title.best_result:
            title_text = fightUtils.normalize_ocr_text(title.best_result.text)
        logger.info(
            f"卡牌幻境第{self.card.layers}层商店："
            + (title_text or "标题未识别，安全跳过")
        )

        if "卷轴" in title_text:
            targets = [
                "石肤术",
                "地震术",
                "静电场",
                "毁灭之刃",
                "瓦解射线",
                "失明术",
                "治疗术",
                "寒冰护盾",
                "死亡波纹",
            ]
            items = context.run_recognition(
                "Card_ScrollShop_Items",
                context.tasker.controller.post_screencap().wait().get(),
                pipeline_override={
                    "Card_ScrollShop_Items": {
                        "recognition": "TemplateMatch",
                        "template": [
                            f"items/scroll/{name}.png" for name in targets
                        ],
                        "roi": [65, 334, 610, 686],
                        "threshold": 0.8,
                    }
                },
            )
            if items and items.hit:
                for result in items.filtered_results:
                    box = result.box
                    context.tasker.controller.post_click(
                        box[0] + box[2] // 2,
                        box[1] + box[3] // 2,
                    ).wait()
                    time.sleep(0.4)
                    context.run_task("ConfirmButton_500ms")

        context.run_task("Fight_ReturnMainWindow")
        return True

    def _handle_round_table(self, context: Context) -> bool:
        return bool(
            fightUtils.handle_arthur_round_table_event(
                context,
                topic_priorities=self.ROUND_TABLE_TOPICS,
                type_priorities=["宗教类", "宗教", "内政类", "内政", "军事类", "军事"],
            )
        )

    def _handle_safe_choice(self, context: Context, image) -> bool:
        priorities = list(self.SAFE_CHOICES)
        if self.card.state.maybe_has_meditation:
            priorities.insert(0, "战斗")
        selected = fightUtils.click_text_by_priority(
            context,
            priorities,
            expected=priorities,
            roi=[35, 430, 650, 720],
            image=image,
            desc="卡牌幻境事件选项",
            return_text=True,
        )
        if not selected:
            return False

        selected = fightUtils.normalize_ocr_text(selected)
        if "交流" in selected:
            self.card.state.maybe_has_meditation = True
        logger.info(f"卡牌幻境已选择安全事件分支：{selected}")
        time.sleep(1)
        return True

    def handle_events(self, context: Context, image=None):
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if self.card.run_dragon_wish_script(context):
            return True
        if self._handle_skill_shop(context, image):
            return True
        if self._handle_round_table(context):
            return True
        return self._handle_safe_choice(context, image)
