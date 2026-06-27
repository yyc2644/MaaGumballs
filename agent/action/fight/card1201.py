from dataclasses import dataclass, field
import json
import time
from enum import Enum

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger, send_message

from action.fight import fightProcessor
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from action.card.card_boss import CardBossHandler
from action.card.card_events import CardEventDispatcher
from action.card.card_hp import CardHPManager
from action.card.card_settlement import CardSettlementManager
from action.card.card_special_layer import CardSpecialLayerManager
from action.card.card_title import CardTitleManager

# 按键精灵旧脚本的录制分辨率。这里把百分比坐标转换成 Maa 常用的 720x1280 坐标系。
LEGACY_SCREEN_WIDTH = 1280
LEGACY_SCREEN_HEIGHT = 2772
TARGET_SCREEN_WIDTH = 720
TARGET_SCREEN_HEIGHT = 1280


class CardImageKey(str, Enum):
    """卡牌幻境图片模板占位枚举。"""

    ENTRY = "入口-卡牌幻境"
    SMALL_CARD_PANEL = "小怪层-卡牌面板"
    SMALL_CONFIRM_1 = "小怪层-居中确认1"
    SMALL_CONFIRM_2 = "小怪层-居中确认2"
    BOSS_CARD_PANEL = "Boss-卡牌面板"
    BOSS_HEART_ENTRY = "Boss-幻境入口"
    FOUR_SYMBOLS_BOOK_MAX = "四象之书满级"
    DOWNSTAIRS = "下楼-楼梯"
    MAGE_EVENT = "事件-法师"
    BULL_EVENT = "事件-蛮牛"
    TREE_EVENT = "事件-树妖"
    EQUIPMENT_SHOP = "事件-装备商店"
    SCROLL_SHOP = "事件-卷轴商店"
    SHOP_CLOSE = "商店-关闭"
    SHOP_CONFIRM = "商店-确认购买"
    DRAGON = "事件-神龙"
    ARTHUR_ROUND_TABLE = "事件-亚瑟王圆桌"
    GUIDE_BUILDING = "事件-攻略建筑选项"
    TEMPORARY_LEAVE_FINISH = "暂离-完成提示"
    UNKNOWN = "未知图片占位"


@dataclass(frozen=True)
class CardImagePlaceholder:
    """需要后续补图的图片模板信息。"""

    key: CardImageKey
    template: str
    area: str | None = None
    similar: int = 90
    note: str = ""


CARD_IMAGE_PLACEHOLDERS: dict[CardImageKey, CardImagePlaceholder] = {
    CardImageKey.ENTRY: CardImagePlaceholder(
        CardImageKey.ENTRY,
        "fight/Card/Card_Entry.png",
        note="大地图卡牌幻境入口；补好后才能从大地图自动进入。",
    ),
    CardImageKey.SMALL_CARD_PANEL: CardImagePlaceholder(
        CardImageKey.SMALL_CARD_PANEL,
        "fight/Card/Card_Small_CardPanel.png",
        "3.2% 26.9% 99.3% 81.6%",
        note="小怪层卡牌/封印书入口。",
    ),
    CardImageKey.SMALL_CONFIRM_1: CardImagePlaceholder(
        CardImageKey.SMALL_CONFIRM_1,
        "fight/Card/Card_Small_Confirm1.png",
        note="小怪层冥想后的居中确认条件1。",
    ),
    CardImageKey.SMALL_CONFIRM_2: CardImagePlaceholder(
        CardImageKey.SMALL_CONFIRM_2,
        "fight/Card/Card_Small_Confirm2.png",
        note="小怪层冥想后的居中确认条件2。",
    ),
    CardImageKey.BOSS_CARD_PANEL: CardImagePlaceholder(
        CardImageKey.BOSS_CARD_PANEL,
        "fight/Card/Card_Boss_CardPanel.png",
        "1.9% 68.5% 42.3% 83.7%",
        note="Boss层卡牌/封印书入口。",
    ),
    CardImageKey.BOSS_HEART_ENTRY: CardImagePlaceholder(
        CardImageKey.BOSS_HEART_ENTRY,
        "fight/Card/Card_Boss_HeartEntry.png",
        "80.5% 52.8% 97.3% 65.3%",
        note="Boss进入龙心/幻境入口。",
    ),
    CardImageKey.FOUR_SYMBOLS_BOOK_MAX: CardImagePlaceholder(
        CardImageKey.FOUR_SYMBOLS_BOOK_MAX,
        "fight/Card/Card_FourSymbolsBook_Max.png",
        "0% 9.4% 100% 81.3%",
        note="四象之书满级状态；满级前禁止使用四象封印。",
    ),
    CardImageKey.DOWNSTAIRS: CardImagePlaceholder(
        CardImageKey.DOWNSTAIRS,
        "fight/Card/Card_Downstairs.png",
        "0.3% 26.2% 98.9% 82.1%",
        93,
        "下楼楼梯。",
    ),
    CardImageKey.MAGE_EVENT: CardImagePlaceholder(
        CardImageKey.MAGE_EVENT,
        "fight/Card/Card_Event_Mage.png",
        "0.3% 28.5% 98.6% 81.2%",
        note="法师事件入口。",
    ),
    CardImageKey.BULL_EVENT: CardImagePlaceholder(
        CardImageKey.BULL_EVENT,
        "fight/Card/Card_Event_Bull.png",
        "0.3% 28.5% 98.6% 81.2%",
        note="蛮牛事件入口。",
    ),
    CardImageKey.TREE_EVENT: CardImagePlaceholder(
        CardImageKey.TREE_EVENT,
        "fight/Card/Card_Event_Tree.png",
        "0.3% 28.5% 98.6% 81.2%",
        94,
        "树妖事件入口。",
    ),
    CardImageKey.EQUIPMENT_SHOP: CardImagePlaceholder(
        CardImageKey.EQUIPMENT_SHOP,
        "fight/Card/Card_Event_EquipmentShop.png",
        "0.9% 27% 97.9% 81.3%",
        note="装备商店入口。",
    ),
    CardImageKey.SCROLL_SHOP: CardImagePlaceholder(
        CardImageKey.SCROLL_SHOP,
        "fight/Card/Card_Event_ScrollShop.png",
        note="卷轴商店入口。",
    ),
    CardImageKey.SHOP_CLOSE: CardImagePlaceholder(
        CardImageKey.SHOP_CLOSE,
        "fight/Card/Card_Shop_Close.png",
        "62.9% 94.4% 96.2% 106.8%",
        note="商店关闭按钮。",
    ),
    CardImageKey.SHOP_CONFIRM: CardImagePlaceholder(
        CardImageKey.SHOP_CONFIRM,
        "fight/Card/Card_Shop_Confirm.png",
        "20.6% 62% 81.5% 71.6%",
        note="商店确认购买弹窗。",
    ),
    CardImageKey.DRAGON: CardImagePlaceholder(
        CardImageKey.DRAGON,
        "fight/Card/Card_Event_Dragon.png",
        "23.9% 20.4% 80.6% 50.8%",
        note="神龙事件；当前优先走通用神龙识别。",
    ),
    CardImageKey.ARTHUR_ROUND_TABLE: CardImagePlaceholder(
        CardImageKey.ARTHUR_ROUND_TABLE,
        "fight/Card/Card_Event_ArthurRoundTable.png",
        note="亚瑟王圆桌会议；当前优先走OCR。",
    ),
    CardImageKey.GUIDE_BUILDING: CardImagePlaceholder(
        CardImageKey.GUIDE_BUILDING,
        "fight/Card/Card_Event_GuideBuilding.png",
        note="攻略建筑/事件选项；当前优先走OCR。",
    ),
    CardImageKey.TEMPORARY_LEAVE_FINISH: CardImagePlaceholder(
        CardImageKey.TEMPORARY_LEAVE_FINISH,
        "fight/Card/Card_TemporaryLeave_Finish.png",
        note="暂离完成提示。",
    ),
}


@dataclass
class CardConfig:
    """卡牌幻境任务配置：来自 interface/pipeline 选项。"""

    # 目标停止或结算楼层。后续有明确策略后再接入界面选项。
    target_leave_layer: int = 1201
    # 结算方式。当前先保留字段，方便后续对齐马尔斯的暂离/自动结算。
    manual_leave: str = "自动结算"
    # 亚瑟王圆桌会议类型优先级：宗教/内政更容易出现魔法增益，军事保底召唤物收益。
    arthur_round_table_type_priorities: list[str] = field(
        default_factory=lambda: ["宗教类", "宗教", "内政类", "内政", "军事类", "军事"]
    )
    # 亚瑟王圆桌会议议题优先级：先全魔法，再电系/气系魔法，最后召唤物相关。
    arthur_round_table_topic_priorities: list[str] = field(
        default_factory=lambda: [
            "所有魔法效果",
            "全部魔法效果",
            "所有伤害类魔法效果",
            "全部伤害类魔法效果",
            "伤害类魔法效果",
            "魔法效果",
            "电系魔法效果",
            "电系魔法",
            "气系魔法效果",
            "气系魔法",
            "静电场",
            "闪电术",
            "召唤物",
            "召唤生物",
            "召唤物攻击",
            "召唤物生命",
        ]
    )
    # 小怪层按攻略优先使用冥想和四象封印。
    small_layer_card_priorities: list[str] = field(
        default_factory=lambda: ["冥想", "四象封印", "四象"]
    )
    # Boss 层先用连斩进幻境，再用冥想补资源。
    boss_layer_card_priorities: list[str] = field(
        default_factory=lambda: ["连斩", "连斩", "冥想"]
    )
    # Boss 心脏阶段：梦魇技能、瓦解龙心、四象封印。
    nightmare_skill_priorities: list[str] = field(
        default_factory=lambda: ["层层恐惧", "恐惧", "梦魇", "抽取", "抽魂"]
    )
    boss_heart_entry_priorities: list[str] = field(
        default_factory=lambda: ["进入", "洞穴", "层层"]
    )
    disintegrate_magic_priorities: list[str] = field(
        default_factory=lambda: ["瓦解射线", "瓦解", "毁灭之刃"]
    )
    # TapTap 攻略中的建筑/事件选项：优先拿绿龙鳞片、冥想、灵木果实和魔力贝壳。
    guide_building_choice_priorities: list[str] = field(
        default_factory=lambda: [
            "战斗",
            "交流",
            "放过",
            "探索",
            "砍伐",
            "砸碎",
            "紧逼",
            "手牌上限",
            "抽牌冷却",
            "抽牌数量",
            "忽略",
        ]
    )
    guide_building_choice_expected: list[str] = field(
        default_factory=lambda: [
            "战斗",
            "交流",
            "放过",
            "探索",
            "砍伐",
            "砸碎",
            "紧逼",
            "手牌上限",
            "抽牌冷却",
            "抽牌数量",
            "忽略",
            "击败",
            "追杀",
            "烧掉",
            "等待",
            "偷窃",
        ]
    )


@dataclass
class CardState:
    """卡牌幻境运行状态：局内流程变化时更新。"""

    # 当前迷宫层数。
    layers: int = 1
    # 是否已经完成出图准备，主循环应退出。
    should_leave_maze: bool = False
    # 是否已经通过神龙获得巨龙之力。
    has_dragon_power: bool = False
    # 是否已经通过神龙获得龙语魔法。
    has_dragon_language: bool = False
    # 法师交流通常用于获得冥想，记录后便于日志判断。
    maybe_has_meditation: bool = False
    # 攻略关键资源：绿龙鳞片、灵木果实、魔力贝壳。
    maybe_has_green_dragon_scale: bool = False
    maybe_has_spirit_wood_fruit: bool = False
    maybe_has_magic_shell: bool = False
    # 记录神龙次数，用于提示多龙未出龙力的风险。
    dragon_wish_count: int = 0
    # 避免反复推送“未出龙力”提醒。
    warned_missing_dragon_power: bool = False


@dataclass
class CardStats:
    """卡牌幻境全局养成状态：跨楼层累计，决定攻略分支是否可用。"""

    # 四象之书是否已经满级。只有满级后才允许使用四象封印。
    is_four_symbols_book_maxed: bool = False
    # 是否已经获得四象封印卡牌/技能。
    has_four_symbols_seal: bool = False
    # 当前手牌上限，后续实测 OCR 后可更新。
    hand_limit: int = 0
    # 当前抽牌冷却缩减或抽牌数量收益，先记录是否拿过相关小恶魔收益。
    has_draw_cooldown_bonus: bool = False
    has_draw_count_bonus: bool = False
    # 是否已经拿过蛮牛拓印符号，后续可用于判断是否继续处理蛮牛。
    has_bull_rubbing_symbol: bool = False


@AgentServer.custom_action("Card1201")
class Card1201(CustomAction):
    """卡牌幻境自动化入口。

    当前文件先建立与马尔斯类似的模块边界和主循环骨架，具体战斗、
    事件、称号和结算策略后续在各 manager 中逐步补齐。
    """

    def __init__(self):
        super().__init__()
        self.config = CardConfig()
        self.state = CardState()
        self.stats = CardStats()

    def reset_state(self):
        """重置局内运行态和全局养成态，保留本次任务配置。"""
        self.state = CardState()
        self.stats = CardStats()

    @property
    def layers(self):
        """兼容旧式写法：当前迷宫层数。"""
        return self.state.layers

    @layers.setter
    def layers(self, value):
        self.state.layers = value

    @property
    def isLeaveMaze(self):
        """兼容旧式写法：是否完成出图准备。"""
        return self.state.should_leave_maze

    @isLeaveMaze.setter
    def isLeaveMaze(self, value):
        self.state.should_leave_maze = value

    def _sleep_after_action(self, delay_seconds=0):
        """执行旧脚本动作后的等待时间。"""
        try:
            delay = float(delay_seconds or 0)
        except (TypeError, ValueError):
            delay = 0
        if delay > 0:
            time.sleep(delay)

    def _parse_percent(self, value):
        """把 '50%' 这类旧脚本文本转成浮点百分比。"""
        return float(str(value).strip().rstrip("%"))

    def _tap_percent(self, context: Context, x_percent, y_percent, delay=0, desc=""):
        """按旧脚本百分比坐标点击，自动映射到 720x1280。"""
        x = round(TARGET_SCREEN_WIDTH * self._parse_percent(x_percent) / 100)
        y = round(TARGET_SCREEN_HEIGHT * self._parse_percent(y_percent) / 100)
        x = max(0, min(TARGET_SCREEN_WIDTH - 1, x))
        y = max(0, min(TARGET_SCREEN_HEIGHT - 1, y))
        if desc:
            logger.debug(f"卡牌幻境点击：{desc} -> ({x}, {y})")
        context.tasker.controller.post_click(x, y).wait()
        self._sleep_after_action(delay)
        return True

    def _tap_area_center(self, context: Context, area, delay=0, desc=""):
        """点击旧脚本百分比区域中心，常用于图片/OCR 占位的临时落点。"""
        if not area:
            logger.debug(f"卡牌幻境跳过无坐标动作：{desc}")
            self._sleep_after_action(delay)
            return False
        left, top, right, bottom = [self._parse_percent(part) for part in area.split()]
        return self._tap_percent(
            context,
            (left + right) / 2,
            (top + bottom) / 2,
            delay=delay,
            desc=desc,
        )

    def _image_meta(self, image_key):
        """读取图片占位元信息。"""
        if isinstance(image_key, CardImageKey):
            return CARD_IMAGE_PLACEHOLDERS[image_key]
        for meta in CARD_IMAGE_PLACEHOLDERS.values():
            if meta.key.value == image_key:
                return meta
        return CardImagePlaceholder(
            key=CardImageKey.UNKNOWN,
            template=f"fight/Card/TODO_{str(image_key).replace(' ', '_')}.png",
            note=str(image_key),
        )

    def _image_hit_placeholder(self, context: Context, image_key, area=None, similar=None):
        """图片识别占位：后续补模板后，在这里替换成 run_recognition 或 pipeline 节点。"""
        meta = self._image_meta(image_key)
        area = area if area is not None else meta.area
        similar = similar if similar is not None else meta.similar
        logger.debug(
            f"卡牌幻境图片识别占位：{meta.key.value}, template={meta.template}, "
            f"area={area}, similar={similar}，当前默认未命中"
        )
        return False

    def _click_image_placeholder(
        self, context: Context, image_key, area=None, similar=None, delay=0
    ):
        """点击图片占位：旧脚本只有搜索范围，真正落点等补模板后由识别结果决定。"""
        meta = self._image_meta(image_key)
        area = area if area is not None else meta.area
        similar = similar if similar is not None else meta.similar
        logger.info(
            f"卡牌幻境图片点击占位：{meta.key.value}，template={meta.template}, "
            f"area={area}, similar={similar}，当前不点击"
        )
        self._sleep_after_action(delay)
        return False

    def _click_text_placeholder(self, context: Context, text, area=None, delay=0):
        """OCR 点击占位：后续可替换成 TextRecognition，当前点击旧脚本 OCR 区域中心。"""
        logger.info(f"卡牌幻境 OCR 点击占位：{text}，后续需要补 OCR/文字识别节点")
        return self._tap_area_center(context, area, delay=delay, desc=f"OCR占位-{text}")

    def _click_text_by_priority(
        self, context: Context, priorities, roi=None, desc="文本", return_text=False
    ):
        """按文本优先级点击当前画面选项。"""
        return fightUtils.click_text_by_priority(
            context,
            priorities,
            expected=priorities,
            roi=roi,
            desc=f"卡牌幻境-{desc}",
            return_text=return_text,
        )

    def _use_card_skill(self, context: Context, priorities, delay=0.5, desc="卡牌技能"):
        """尝试用 OCR 点击卡牌/封印书技能，图片模板未补齐时的主要执行方式。"""
        clicked = self._click_text_by_priority(
            context,
            priorities,
            roi=[0, 650, 720, 620],
            desc=desc,
        )
        self._sleep_after_action(delay)
        return clicked

    def _attack_center(self, context: Context, delay=0.5, desc="攻击目标"):
        """点击屏幕中部目标，适合释放卡牌/魔法后的确认或攻击龙心。"""
        return self._tap_percent(context, "50%", "50%", delay=delay, desc=desc)

    def _use_four_symbols_seal(self, context: Context, delay=0.5, desc="四象封印"):
        """使用四象封印。四象之书未满级时禁止使用，避免攻略节奏被打乱。"""
        if not self.stats.is_four_symbols_book_maxed:
            logger.info("四象之书尚未满级，跳过四象封印")
            return False
        used = self._use_card_skill(
            context, ["四象封印", "四象"], delay=delay, desc=desc
        )
        if used:
            self.stats.has_four_symbols_seal = True
        return used

    def update_four_symbols_book_stats(self, context: Context):
        """更新四象之书状态。图片模板未补前，优先尝试 OCR 文案。"""
        if self.stats.is_four_symbols_book_maxed:
            return True
        image = context.tasker.controller.post_screencap().wait().get()
        candidates = fightUtils.ocr_text_candidates(
            context,
            ["四象之书", "满级", "Lv.MAX", "MAX", "已满级"],
            roi=[0, 120, 720, 920],
            image=image,
        )
        for candidate in candidates:
            text = fightUtils.normalize_ocr_text(getattr(candidate, "text", ""))
            if "四象之书" in text and (
                "满级" in text or "MAX" in text.upper() or "已满级" in text
            ):
                self.stats.is_four_symbols_book_maxed = True
                self.stats.has_four_symbols_seal = True
                logger.info("检测到四象之书已满级，允许使用四象封印")
                return True
        if self._image_hit_placeholder(
            context,
            CardImageKey.FOUR_SYMBOLS_BOOK_MAX,
        ):
            self.stats.is_four_symbols_book_maxed = True
            self.stats.has_four_symbols_seal = True
            logger.info("通过图片占位检测到四象之书已满级")
            return True
        return False

    def run_small_monster_layer_script(self, context: Context):
        """按攻略处理小怪层：冥想补能量，四象封印清场。"""
        logger.info("执行卡牌幻境小怪层攻略流程：冥想 + 四象封印")
        self._click_image_placeholder(
            context, CardImageKey.SMALL_CARD_PANEL
        )
        self._use_card_skill(context, ["冥想"], desc="小怪层-冥想")
        self._attack_center(context, delay=0.5, desc="小怪层-释放冥想")

        # 旧脚本这里有两个带图片条件的居中点击，先保留占位，等模板补齐后再决定是否执行。
        if self._image_hit_placeholder(context, CardImageKey.SMALL_CONFIRM_1):
            self._attack_center(context, desc="小怪层-居中确认1")
        if self._image_hit_placeholder(context, CardImageKey.SMALL_CONFIRM_2):
            self._attack_center(context, desc="小怪层-居中确认2")

        self._click_text_placeholder(
            context, "特殊", area="13.6% 77.1% 75.5% 85.3%"
        )
        if self._use_four_symbols_seal(context, delay=0.5, desc="小怪层-四象封印"):
            self._attack_center(context, desc="小怪层-释放四象")
        return True

    def run_boss_layer_script(self, context: Context):
        """按攻略处理 Boss：连斩进洞，抽魂，瓦解龙心，四象后斩杀。"""
        logger.info("执行卡牌幻境 Boss 层攻略流程")
        if context.run_recognition(
            "Fight_OpenedDoor", context.tasker.controller.post_screencap().wait().get()
        ).hit:
            return True

        self._click_image_placeholder(
            context, CardImageKey.BOSS_CARD_PANEL, delay=7
        )
        self._use_card_skill(context, ["连斩"], delay=0.5, desc="Boss-连斩1")
        self._attack_center(context, delay=1, desc="Boss-连斩1攻击")
        self._use_card_skill(context, ["连斩"], delay=0.5, desc="Boss-连斩2")
        self._attack_center(context, delay=1, desc="Boss-连斩2攻击")
        self._use_card_skill(context, ["冥想"], delay=0.5, desc="Boss-冥想")
        self._attack_center(context, delay=1, desc="Boss-释放冥想")

        # 前几个 Boss 未获得龙力时，按攻略需要用火系卷轴补伤害进洞。
        if not self.state.has_dragon_power and self.layers < 80:
            logger.info("尚未获得龙力，Boss 前期尝试用流星雨/火球补伤害")
            if not fightUtils.cast_magic("火", "流星雨", context, (360, 640)):
                fightUtils.cast_magic("火", "火球术", context, (360, 640))

        self._click_text_by_priority(
            context,
            self.config.boss_heart_entry_priorities,
            roi=[0, 650, 720, 430],
            desc="Boss-进入幻境",
        )
        self._click_image_placeholder(
            context, CardImageKey.BOSS_HEART_ENTRY, delay=5
        )
        self._click_text_by_priority(
            context,
            self.config.nightmare_skill_priorities,
            roi=[0, 300, 720, 760],
            desc="Boss-梦魇抽魂",
        )

        # 攻略强调瓦解要给龙心，不是给 Boss 本体。
        if not fightUtils.cast_magic("暗", "瓦解射线", context, (360, 640)):
            self._click_text_by_priority(
                context,
                self.config.disintegrate_magic_priorities,
                roi=[0, 220, 720, 900],
                desc="Boss-瓦解龙心",
            )
            self._attack_center(context, delay=0.5, desc="Boss-瓦解确认")

        if self._use_four_symbols_seal(context, delay=1, desc="Boss-四象封印"):
            self._attack_center(context, delay=2, desc="Boss-A龙心斩杀")
        else:
            logger.warning("Boss 层跳过四象封印，尝试直接攻击龙心兜底")
            self._attack_center(context, delay=2, desc="Boss-A龙心兜底")
        context.run_task("Fight_ReturnMainWindow")
        return True

    def run_loot_all_script(self, context: Context):
        """转换自 `整体搜刮.zjs`：按事件图片识别结果分发搜刮脚本。"""
        logger.info("执行卡牌幻境整体搜刮脚本")
        if self._image_hit_placeholder(context, CardImageKey.MAGE_EVENT):
            self.run_loot_mage_script(context)
        if self._image_hit_placeholder(context, CardImageKey.TREE_EVENT):
            self.run_loot_tree_script(context)
        if self._image_hit_placeholder(context, CardImageKey.BULL_EVENT):
            self.run_loot_bull_script(context)
        if self._image_hit_placeholder(context, CardImageKey.EQUIPMENT_SHOP):
            self.run_loot_equipment_script(context)
        if self._image_hit_placeholder(context, CardImageKey.SCROLL_SHOP):
            self.run_loot_scroll_script(context)
        return True

    def run_guide_building_choice_script(self, context: Context):
        """按攻略处理建筑/事件选项，优先安全收益，避开掉卡牌的选项。"""
        priorities = list(self.config.guide_building_choice_priorities)
        if not self.state.maybe_has_meditation and "战斗" in priorities:
            priorities.remove("战斗")

        selected = fightUtils.click_text_by_priority(
            context,
            priorities,
            expected=self.config.guide_building_choice_expected,
            roi=[0, 430, 720, 760],
            desc="卡牌幻境-攻略建筑选项",
            return_text=True,
        )
        if not selected:
            return False

        selected = fightUtils.normalize_ocr_text(selected)
        if selected in ["交流"]:
            self.state.maybe_has_meditation = True
            logger.info("攻略事件：法师交流，记录可能已获得冥想")
        elif selected in ["战斗"]:
            logger.info("攻略事件：已有冥想后选择法师战斗")
        elif selected in ["放过", "探索", "紧逼"]:
            self.state.maybe_has_green_dragon_scale = True
            logger.info("攻略事件：记录可能已获得绿龙鳞片")
        elif selected in ["砍伐"]:
            self.state.maybe_has_spirit_wood_fruit = True
            logger.info("攻略事件：记录可能已获得灵木果实")
        elif selected in ["砸碎"]:
            self.state.maybe_has_magic_shell = True
            logger.info("攻略事件：记录可能已获得魔力贝壳")
        elif "手牌上限" in selected or "抽牌" in selected:
            if "冷却" in selected:
                self.stats.has_draw_cooldown_bonus = True
            if "数量" in selected:
                self.stats.has_draw_count_bonus = True
            if "手牌上限" in selected:
                self.stats.hand_limit += 1
            logger.info(f"攻略事件：小恶魔选择收益项 {selected}")
        return True

    def run_loot_mage_script(self, context: Context):
        """转换自 `搜刮法师.zjs`：法师事件交流。"""
        self._click_image_placeholder(
            context, CardImageKey.MAGE_EVENT, delay=1
        )
        if self._click_text_placeholder(
            context, "交流", area="13.3% 54.8% 86.9% 80.2%", delay=0.5
        ):
            self.state.maybe_has_meditation = True
            logger.info("已处理法师交流，按攻略记录为可能已获得冥想")
        return True

    def run_loot_bull_script(self, context: Context):
        """转换自 `搜刮蛮牛.zjs`：蛮牛事件拓印符号。"""
        self._click_image_placeholder(
            context, CardImageKey.BULL_EVENT
        )
        if self._click_text_placeholder(
            context, "拓印符号", area="13.3% 54.8% 86.9% 80.2%"
        ):
            self.stats.has_bull_rubbing_symbol = True
            logger.info("已处理蛮牛拓印符号")
        return True

    def run_loot_tree_script(self, context: Context):
        """转换自 `搜刮树妖.zjs`：树妖事件交流。"""
        self._click_image_placeholder(
            context, CardImageKey.TREE_EVENT, delay=0.5
        )
        self._click_text_placeholder(
            context, "交流", area="13.3% 54.8% 86.9% 80.2%", delay=0.5
        )
        return True

    def run_loot_equipment_script(self, context: Context):
        """转换自 `搜刮装备.zjs`：商店购买前两件装备。"""
        self._click_image_placeholder(
            context, CardImageKey.EQUIPMENT_SHOP, delay=0.5
        )
        self._tap_percent(context, "23.5%", "52.5%", delay=0.5, desc="装备商店-第一件")
        self._click_text_placeholder(
            context, "确认购买", area="10.7% 68.5% 91.1% 80.7%", delay=0.5
        )
        self._tap_percent(context, "46.8%", "52.4%", delay=0.5, desc="装备商店-第二件")
        self._click_text_placeholder(
            context, "确认购买", area="10.7% 68.5% 91.1% 80.7%", delay=0.5
        )
        if self._image_hit_placeholder(context, CardImageKey.SHOP_CLOSE):
            self._tap_percent(context, "81%", "103.1%", desc="装备商店-关闭")
        return True

    def run_loot_scroll_script(self, context: Context):
        """转换自 `搜刮卷轴.zjs`：卷轴商店购买四个位置。"""
        self._click_image_placeholder(
            context, CardImageKey.SCROLL_SHOP
        )
        for x, y, delay, desc in [
            ("23.5%", "52.5%", 0, "卷轴商店-第一件"),
            ("46.8%", "52.4%", 0.5, "卷轴商店-第二件"),
            ("70.1%", "52.4%", 0.5, "卷轴商店-第三件"),
            ("23.9%", "67.3%", 0, "卷轴商店-第四件"),
        ]:
            self._tap_percent(context, x, y, delay=delay, desc=desc)
            if self._image_hit_placeholder(context, CardImageKey.SHOP_CONFIRM):
                self._tap_percent(context, "51.2%", "67.1%", desc="卷轴商店-确认购买")
        if self._image_hit_placeholder(context, CardImageKey.SHOP_CLOSE):
            self._tap_percent(context, "79.6%", "102.2%", desc="卷轴商店-关闭")
        return True

    def run_downstairs_script(self, context: Context):
        """转换自 `下楼.zjs`：优先保留旧脚本下楼点，随后用通用下楼兜底。"""
        logger.info("执行卡牌幻境下楼脚本")
        self._click_image_placeholder(
            context, CardImageKey.DOWNSTAIRS, delay=1
        )
        return fightUtils.handle_downstair_event(context)

    def run_temporary_leave_script(self, context: Context):
        """转换自 `暂离.zjs`：打开菜单并确认暂离。"""
        logger.info("执行卡牌幻境暂离脚本")
        self._tap_percent(context, "8.8%", "9%", desc="暂离-打开菜单")
        self._click_text_placeholder(
            context, "暂离", area="40.8% 100.9% 61.1% 105.9%"
        )
        self._click_text_placeholder(
            context, "确定", area="28.1% 47.8% 70.2% 72.6%"
        )
        self._click_text_placeholder(
            context, "暂离中", area="53% 17.4% 95.2% 26.7%"
        )
        return True

    def run_dragon_wish_script(self, context: Context):
        """处理神龙事件：按卡牌幻境优先级自动选择愿望。"""
        wish = fightUtils.handle_dragon_event("卡牌幻境", context)
        if not wish:
            return False
        self.state.dragon_wish_count += 1
        if wish in ["我想获得巨龙之力", "我要获得巨龙之力"]:
            self.state.has_dragon_power = True
            logger.info("卡牌幻境已记录获得巨龙之力")
        elif wish in ["我想学习龙语魔法", "我要学习龙语魔法"]:
            self.state.has_dragon_language = True
            logger.info("卡牌幻境已记录获得龙语魔法")
        elif self.state.dragon_wish_count >= 2 and not self.state.has_dragon_power:
            logger.warning("已遇到多次神龙但尚未获得巨龙之力，1201 后续 Boss 风险较高")
        return True

    def run_arthur_round_table_script(self, context: Context):
        """处理亚瑟王圆桌会议：按卡牌幻境收益优先级选择议题。"""
        return fightUtils.handle_arthur_round_table_event(
            context,
            topic_priorities=self.config.arthur_round_table_topic_priorities,
            type_priorities=self.config.arthur_round_table_type_priorities,
        )

    def run_buy_stamina_with_diamonds_script(self, context: Context):
        """转换自 `钻石.zjs`：自动肉鸽体力不足时的钻石购买点击序列。"""
        logger.info("执行卡牌幻境钻石购买体力脚本")
        self._tap_percent(context, "49.9%", "41.9%", desc="钻石购买-入口")
        self._tap_percent(context, "27.7%", "59.2%", desc="钻石购买-数量/取消位")
        self._tap_percent(context, "66.7%", "59%", desc="钻石购买-确认位")
        return True

    def initialize(self, context: Context):
        self.reset_state()
        logger.info("卡牌幻境初始化完成")
        context.run_task("Fight_ReturnMainWindow")
        layer_detail = context.run_task("Fight_CheckLayer")
        if layer_detail.nodes:
            self.layers = fightUtils.extract_num_layer(
                layer_detail.nodes[0].recognition.best_result.text
            )
        logger.info(f"当前层数: {self.layers}, 进入卡牌幻境初始化")

        self.hp_manager = CardHPManager(self)
        self.boss_handler = CardBossHandler(self)
        self.title_manager = CardTitleManager(self)
        self.special_layer_manager = CardSpecialLayerManager(self)
        self.events_dispatcher = CardEventDispatcher(self)
        self.settlement_manager = CardSettlementManager(self)

    def Check_CurrentLayers(self, context: Context):
        self.layers = fightUtils.handle_currentlayer_event(context)
        return True

    @timing_decorator
    def handle_preLayers_event(self, context: Context):
        self.update_four_symbols_book_stats(context)
        self.hp_manager.Check_DefaultStatus(context)
        return True

    @timing_decorator
    def handle_clearCurLayer_event(self, context: Context):
        if self.layers >= 30 and self.layers % 10 == 0:
            return self.boss_handler.handle_boss_event(context)
        self.run_small_monster_layer_script(context)
        context.run_task(
            "Card_Fight_ClearCurrentLayer",
            pipeline_override={
                "Card_Fight_ClearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )
        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.info("卡牌幻境检测到死亡，尝试小SL")
            fightUtils.Saveyourlife(context)
            return False
        if context.run_recognition("BackText", image).hit:
            logger.info("卡牌幻境检测到卡返回，回到主界面后重试本层")
            context.run_task("Fight_ReturnMainWindow")
            return False
        return True

    @timing_decorator
    def handle_postLayers_event(self, context: Context):
        self.events_dispatcher.handle_events(context)
        self.title_manager.Check_DefaultTitle(context)
        if (
            self.layers >= 100
            and not self.state.has_dragon_power
            and not self.state.warned_missing_dragon_power
        ):
            self.state.warned_missing_dragon_power = True
            logger.warning("攻略建议：100层前未获得巨龙之力时，1201成功率很低，建议考虑重开")
            send_message("MaaGB", "卡牌幻境100层前未获得巨龙之力，攻略建议重开")
        if self.layers >= self.config.target_leave_layer:
            self.settlement_manager.handle_before_leave_maze_event(context)
            return True
        self.run_downstairs_script(context)
        return True

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.initialize(context)
        logger.info(f"卡牌幻境目标层数: {self.config.target_leave_layer}")

        while self.layers <= self.config.target_leave_layer:
            if context.tasker.stopping:
                logger.info("检测到停止任务，退出卡牌幻境agent")
                return CustomAction.RunResult(success=False)

            if not self.Check_CurrentLayers(context):
                return CustomAction.RunResult(success=False)
            logger.info(f"Start Card1201 Explore {self.layers} layer.")

            self.handle_preLayers_event(context)
            if not self.handle_clearCurLayer_event(context):
                continue
            if not self.handle_interrupt_event(context):
                continue
            if not self.handle_postLayers_event(context):
                continue
            if self.isLeaveMaze:
                logger.info(f"当前层数 {self.layers}, 卡牌幻境出图准备完成")
                break

        logger.info(f"卡牌幻境探索结束，当前到达{self.layers}层")
        if self.config.manual_leave == "暂离":
            self.run_temporary_leave_script(context)
            send_message("MaaGB", f"卡牌幻境到达{self.layers}层，已暂离保存")
        else:
            context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Card_Fight_ClearCurrentLayer")
class Card_Fight_ClearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor(target_wish="卡牌幻境")

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        layers_arg = json.loads(argv.custom_action_param).get("layers")
        if layers_arg is not None:
            self.fightProcessor.layers = layers_arg

        self.fightProcessor.targetWish = "卡牌幻境"
        self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
