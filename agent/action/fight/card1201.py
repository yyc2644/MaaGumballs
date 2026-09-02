import json
import time
from dataclasses import dataclass

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from action.fight import fightProcessor, fightUtils
from action.fight.downstair import FightDownstairManager
from action.fight.fightUtils import timing_decorator
from action.card.card_boss import CardBossHandler
from action.card.card_events import CardEventDispatcher
from action.card.card_hp import CardHPManager
from action.card.card_settlement import CardSettlementManager
from action.card.card_special_layer import CardSpecialLayerManager
from action.card.card_title import CardTitleManager
from utils import logger, send_message


@dataclass
class CardConfig:
    """Runtime options controlled by interface pipeline overrides."""

    target_leave_layer: int = 1201
    manual_leave: str = "自动结算"
    max_same_layer_retries: int = 12


@dataclass
class CardState:
    layers: int = 1
    should_leave_maze: bool = False
    has_dragon_power: bool = False
    has_dragon_language: bool = False
    maybe_has_meditation: bool = False
    dragon_wish_count: int = 0
    warned_missing_dragon_power: bool = False
    same_layer_retries: int = 0
    last_observed_layer: int = -1
    preprocessed_layer: int = -1
    combat_prepared_layer: int = -1
    earth_gate_checked_layer: int = -1
    earth_gate_uses: int = 0


@AgentServer.custom_action("Card1201")
class Card1201(CustomAction):
    """Card Wonderland long-run state machine.

    The implementation intentionally uses OCR and the shared fight/downstairs
    processors.  It does not depend on the uncommitted Card image templates
    that made the old branch silently skip most of its actions.
    """

    def __init__(self):
        super().__init__()
        self.config = CardConfig()
        self.state = CardState()
        self.hp_manager = None
        self.boss_handler = None
        self.title_manager = None
        self.special_layer_manager = None
        self.events_dispatcher = None
        self.settlement_manager = None
        self.downstair_manager = None

    @property
    def layers(self):
        return self.state.layers

    @layers.setter
    def layers(self, value):
        self.state.layers = int(value)

    @property
    def isLeaveMaze(self):
        return self.state.should_leave_maze

    @isLeaveMaze.setter
    def isLeaveMaze(self, value):
        self.state.should_leave_maze = bool(value)

    @staticmethod
    def _node_expected(context: Context, node_name: str, default):
        """Read an OCR setting node without assuming MaaFW's list shape."""
        try:
            node = context.get_node_data(node_name)
            value = node["recognition"]["param"]["expected"]
            if isinstance(value, (list, tuple)):
                value = value[0] if value else default
            return value
        except (KeyError, TypeError, ValueError, IndexError):
            logger.warning(f"读取配置 {node_name} 失败，使用默认值 {default}")
            return default

    def load_config(self, context: Context):
        target = self._node_expected(
            context, "Card_Target_Layer_Setting", self.config.target_leave_layer
        )
        try:
            target = int(target)
        except (TypeError, ValueError):
            target = self.config.target_leave_layer
        self.config.target_leave_layer = max(1, min(1201, target))
        self.config.manual_leave = str(
            self._node_expected(
                context, "Card_ManualLeave_Setting", self.config.manual_leave
            )
        )

    def initialize(self, context: Context):
        self.state = CardState()
        self.hp_manager = CardHPManager(self)
        self.boss_handler = CardBossHandler(self)
        self.title_manager = CardTitleManager(self)
        self.special_layer_manager = CardSpecialLayerManager(self)
        self.events_dispatcher = CardEventDispatcher(self)
        self.settlement_manager = CardSettlementManager(self)
        self.downstair_manager = FightDownstairManager(self)

        context.run_task("Fight_ReturnMainWindow")
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.error("卡牌幻境初始化失败：无法识别当前层数")
            return False
        self.layers = layer
        self.special_layer_manager.ensure_seal_book(context)
        logger.info(
            f"卡牌幻境初始化完成：当前{self.layers}层，目标{self.config.target_leave_layer}层"
        )
        return True

    def Check_CurrentLayers(self, context: Context):
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.warning("卡牌幻境层数识别失败，本轮不更新层数")
            return False

        if layer != self.state.last_observed_layer:
            self.state.same_layer_retries = 0
            self.state.last_observed_layer = layer
            self.state.earth_gate_checked_layer = -1
        self.layers = layer
        return True

    def recover_stalled_layer(self, context: Context):
        logger.error(
            f"卡牌幻境在{self.layers}层连续重试"
            f"{self.state.same_layer_retries}次，停止任务并保留现场"
        )
        context.run_task("Screenshot")
        context.run_task("Fight_ReturnMainWindow")
        self.state.same_layer_retries = 0
        self.state.preprocessed_layer = -1
        self.state.combat_prepared_layer = -1
        return False

    def should_try_earth_gate(self) -> bool:
        """Use Earth Gate on floor 49 and every later x9 floor, once per visit."""
        return (
            self.layers >= 49
            and self.layers % 10 == 9
            and self.state.earth_gate_checked_layer != self.layers
        )

    def try_earth_gate(self, context: Context) -> bool:
        if not self.should_try_earth_gate():
            return False

        current_layer = self.layers
        self.state.earth_gate_checked_layer = current_layer
        context.run_task("Fight_ReturnMainWindow")
        if not fightUtils.check_magic("土", "大地之门", context):
            logger.info(f"第{current_layer}层没有大地之门，继续向下")
            context.run_task("Fight_ReturnMainWindow")
            return False

        logger.info(f"第{current_layer}层检测到大地之门，优先返回低层发育")
        if not fightUtils.cast_magic("土", "大地之门", context):
            logger.warning("大地之门施放失败，本次继续向下")
            context.run_task("Fight_ReturnMainWindow")
            return False

        for _ in range(15):
            time.sleep(1)
            if not self.Check_CurrentLayers(context):
                continue
            if self.layers != current_layer:
                self.state.earth_gate_uses += 1
                self.state.preprocessed_layer = -1
                self.state.combat_prepared_layer = -1
                logger.info(
                    f"大地之门完成：{current_layer}层 -> {self.layers}层，"
                    f"累计使用{self.state.earth_gate_uses}次"
                )
                return True

        logger.warning("等待大地之门后层数没有变化，本次停止重复施放")
        context.run_task("Fight_ReturnMainWindow")
        return False

    def cast_card_skill(
        self,
        context: Context,
        card_name: str,
        target: tuple[int, int] | None = None,
    ) -> bool:
        """Open the Card panel and cast one named card using OCR."""
        context.run_task("Fight_ReturnMainWindow")
        context.tasker.controller.post_click(600, 1150).wait()
        time.sleep(0.7)
        clicked = fightUtils.click_text_by_priority(
            context,
            [card_name],
            expected=[card_name],
            roi=[25, 260, 670, 760],
            desc=f"卡牌技能-{card_name}",
        )
        if not clicked:
            self.ensure_maze_main_window(context)
            return False

        time.sleep(0.4)
        confirmed = fightUtils.click_text_by_priority(
            context,
            ["使用", "释放", "发动", "确定"],
            roi=[60, 650, 600, 500],
            desc=f"卡牌技能-{card_name}-确认",
        )
        if target is not None:
            context.tasker.controller.post_click(*target).wait()
        elif not confirmed:
            # Non-target cards generally use the centered action area.
            context.tasker.controller.post_click(360, 800).wait()
        time.sleep(0.6)
        self.ensure_maze_main_window(context)
        return True

    def ensure_maze_main_window(self, context: Context) -> bool:
        """Close Card's hand overlay before combat, events, or downstairs."""
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_MainWindow", image).hit:
            return True

        # The shared Fight_ReturnMainWindow pipeline does not know Card's hand
        # overlay. Android Back closes it without clicking a card accidentally.
        context.tasker.controller.post_press_key(4).wait()
        time.sleep(0.5)
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_MainWindow", image).hit:
            return True

        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        return bool(context.run_recognition("Fight_MainWindow", image).hit)

    def cast_four_symbols(self, context: Context) -> bool:
        used = fightUtils.cast_magic_special("四象封印", context)
        if not used:
            logger.debug("本层没有可用的四象封印，交给通用清层器")
        return used

    def run_small_monster_layer_script(self, context: Context):
        logger.info(f"第{self.layers}层：冥想/四象后通用清层")
        if self.state.combat_prepared_layer != self.layers:
            if self.cast_card_skill(context, "冥想"):
                self.state.maybe_has_meditation = True
            self.cast_four_symbols(context)
            self.state.combat_prepared_layer = self.layers
        return context.run_task(
            "Card_Fight_ClearCurrentLayer",
            pipeline_override={
                "Card_Fight_ClearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )

    def run_boss_layer_script(self, context: Context):
        logger.info(f"第{self.layers}层：执行卡牌幻境Boss流程")
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True

        if self.state.combat_prepared_layer == self.layers:
            return context.run_task(
                "Card_Fight_ClearCurrentLayer",
                pipeline_override={
                    "Card_Fight_ClearCurrentLayer": {
                        "custom_action_param": {"layers": self.layers}
                    }
                },
            )

        self.cast_card_skill(context, "连斩", target=(360, 800))
        self.cast_card_skill(context, "连斩", target=(360, 800))
        if self.cast_card_skill(context, "冥想"):
            self.state.maybe_has_meditation = True
        context.tasker.controller.post_click(360, 800).wait()
        time.sleep(1)

        entered = fightUtils.click_text_by_priority(
            context,
            ["进入龙心", "进入幻境", "进入"],
            roi=[40, 540, 640, 500],
            desc="进入龙之心",
        )
        if not entered:
            logger.info("未识别到龙心入口文字，使用攻略记录坐标兜底")
            context.tasker.controller.post_click(360, 600).wait()
        time.sleep(1.5)

        fightUtils.cast_magic_special("抽取心脏灵魂", context)
        fightUtils.cast_magic("气", "瓦解射线", context, (360, 600))
        self.cast_four_symbols(context)
        context.tasker.controller.post_click(360, 600).wait()
        fightUtils.cast_magic_special("斩杀", context)
        context.run_task("Fight_ReturnMainWindow")
        context.tasker.controller.post_click(360, 800).wait()
        time.sleep(1)
        self.state.combat_prepared_layer = self.layers

        return context.run_task(
            "Card_Fight_ClearCurrentLayer",
            pipeline_override={
                "Card_Fight_ClearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )

    def run_dragon_wish_script(self, context: Context):
        wish = fightUtils.handle_dragon_event("卡牌幻境", context)
        if not wish:
            return False
        self.state.dragon_wish_count += 1
        normalized = fightUtils.normalize_ocr_text(wish)
        if "巨龙之力" in normalized:
            self.state.has_dragon_power = True
        elif "龙语魔法" in normalized:
            self.state.has_dragon_language = True
        logger.info(f"卡牌幻境已完成神龙愿望：{normalized}")
        return True

    @timing_decorator
    def handle_preLayers_event(self, context: Context):
        self.hp_manager.Check_DefaultStatus(context)
        self.title_manager.Check_DefaultTitle(context)
        return True

    @timing_decorator
    def handle_clearCurLayer_event(self, context: Context):
        if self.layers >= 30 and self.layers % 10 == 0:
            return self.boss_handler.handle_boss_event(context)
        return bool(self.run_small_monster_layer_script(context))

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        if not self.ensure_maze_main_window(context):
            logger.warning("卡牌幻境无法关闭卡牌面板，本轮停止后续交互")
            return False
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.warning("卡牌幻境检测到死亡，执行小SL")
            fightUtils.Saveyourlife(context)
            return False
        if self.events_dispatcher.handle_events(context, image=image):
            context.run_task("Fight_ReturnMainWindow")
            return False
        if context.run_recognition("BackText", image).hit:
            logger.info("卡牌幻境检测到阻塞弹窗，返回主界面重试本层")
            context.run_task("Fight_ReturnMainWindow")
            return False
        return True

    @timing_decorator
    def handle_postLayers_event(self, context: Context):
        if not self.ensure_maze_main_window(context):
            return False
        self.special_layer_manager.handle_special_layer_event(context)
        image = context.tasker.controller.post_screencap().wait().get()
        if not context.run_recognition("Fight_OpenedDoor", image).hit:
            logger.debug("本层门尚未打开，继续清理而不尝试下楼")
            return False

        if (
            self.layers >= 100
            and not self.state.has_dragon_power
            and not self.state.warned_missing_dragon_power
        ):
            self.state.warned_missing_dragon_power = True
            logger.warning("100层前未获得巨龙之力，继续按明确目标推进")
            send_message("MaaGB", "卡牌幻境100层前未获得巨龙之力，仍继续推进")

        if self.try_earth_gate(context):
            # Layer changed. Restart from per-layer preprocessing on the new floor.
            return False

        if self.layers >= self.config.target_leave_layer:
            return self.settlement_manager.handle_before_leave_maze_event(context)

        return self.downstair_manager.handle_downstair_event(context)

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.load_config(context)
        if not self.initialize(context):
            return CustomAction.RunResult(success=False)

        while self.layers <= self.config.target_leave_layer:
            if context.tasker.stopping:
                logger.info("检测到停止任务，退出卡牌幻境agent")
                return CustomAction.RunResult(success=False)
            if not self.Check_CurrentLayers(context):
                time.sleep(1)
                continue
            if self.state.same_layer_retries >= self.config.max_same_layer_retries:
                self.recover_stalled_layer(context)
                return CustomAction.RunResult(success=False)

            logger.info(f"Start Card Explore {self.layers} layer.")
            if self.state.preprocessed_layer != self.layers:
                self.handle_preLayers_event(context)
                self.state.preprocessed_layer = self.layers
            if not self.handle_clearCurLayer_event(context):
                self.state.same_layer_retries += 1
                continue
            if not self.handle_interrupt_event(context):
                self.state.same_layer_retries += 1
                continue
            if not self.handle_postLayers_event(context):
                self.state.same_layer_retries += 1
                continue
            if self.isLeaveMaze:
                break

        logger.info(f"卡牌幻境探索结束，当前到达{self.layers}层")
        if self.config.manual_leave in ["暂离", "保存暂离"]:
            context.run_task("Save_Status")
            send_message("MaaGB", f"卡牌幻境到达{self.layers}层，已暂离保存")
        else:
            context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Card_Fight_ClearCurrentLayer")
class CardFightClearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()
        self.fightProcessor.targetWish = "卡牌幻境"

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        layers_arg = None
        if argv.custom_action_param:
            try:
                layers_arg = json.loads(argv.custom_action_param).get("layers")
            except (TypeError, ValueError, json.JSONDecodeError):
                logger.warning("Card清层参数解析失败，沿用当前层数")
        if layers_arg is not None:
            self.fightProcessor.layers = int(layers_arg)
        self.fightProcessor.targetWish = "卡牌幻境"
        succeeded = self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=bool(succeeded))
