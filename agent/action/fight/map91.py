import json
import time
from dataclasses import dataclass

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from action.dungeon.boss import BossStrategyRegistry, CallableBossStrategy
from action.dungeon.normal_layer import LootPhase, MonsterPhase, NormalLayerRunner
from action.dungeon.runner import DungeonRunner
from action.dungeon.state import DungeonState
from action.fight import fightProcessor, fightUtils
from action.fight.downstair import FightDownstairManager
from action.fight.fightUtils import timing_decorator
from action.map91.map91_boss import Map91BossHandler
from action.map91.map91_earth_gate import Map91EarthGateManager
from action.map91.map91_events import Map91EventDispatcher
from action.map91.map91_hp import Map91HPManager
from action.map91.map91_settlement import Map91SettlementManager
from action.map91.map91_skill import Map91FighterSkillManager
from action.map91.map91_special_layer import Map91SpecialLayerManager
from action.map91.map91_title import Map91TitleManager
from utils import logger, send_message


def _read_setting(context: Context, node_name: str, default):
    try:
        value = context.get_node_data(node_name)["recognition"]["param"]["expected"]
        if isinstance(value, (list, tuple)):
            value = value[0] if value else default
        return value
    except (KeyError, TypeError, ValueError, IndexError):
        logger.warning(f"读取配置 {node_name} 失败，使用默认值 {default}")
        return default


@dataclass
class Map91Config:
    """由 interface pipeline override 控制的运行参数。"""

    target_leave_layer: int = 1199
    manual_leave: str = "保存暂离"
    max_same_layer_retries: int = 12
    monster_phase_enabled: bool = True
    loot_phase_enabled: bool = True


@dataclass
class Map91State:
    layers: int = 1
    should_leave_maze: bool = False
    same_layer_retries: int = 0
    last_observed_layer: int = -1
    preprocessed_layer: int = -1
    earth_gate_checked_layer: int = -1

    def to_dungeon_state(self) -> DungeonState:
        return DungeonState(
            current_layer=self.layers,
            should_leave=self.should_leave_maze,
            same_layer_retries=self.same_layer_retries,
            last_observed_layer=self.last_observed_layer,
            preprocessed_layer=self.preprocessed_layer,
        )

    def sync_from_dungeon_state(self, state: DungeonState) -> None:
        self.layers = state.current_layer
        self.should_leave_maze = state.should_leave
        self.same_layer_retries = state.same_layer_retries
        self.last_observed_layer = state.last_observed_layer
        self.preprocessed_layer = state.preprocessed_layer


@AgentServer.custom_action("Map91")
class Map91(CustomAction):
    """91-1201 自动化主流程。

    本类只负责流程编排：小怪层分为刷怪和搜刮两个阶段；Boss、事件、称号、
    生存、特殊层、大地之门和结算分别委托给 action/map91 下的模块。
    """

    def __init__(self):
        super().__init__()
        self.config = Map91Config()
        self.state = Map91State()
        self.hp_manager = None
        self.boss_handler = None
        self.title_manager = None
        self.special_layer_manager = None
        self.earth_gate_manager = None
        self.events_dispatcher = None
        self.fighter_skill_manager = None
        self.settlement_manager = None
        self.downstair_manager = None
        self.dungeon_state = self.state.to_dungeon_state()
        self.dungeon_runner = None

    @property
    def layers(self) -> int:
        return self.state.layers

    @layers.setter
    def layers(self, value):
        self.state.layers = int(value)

    @property
    def is_leave_maze(self) -> bool:
        return self.state.should_leave_maze

    @is_leave_maze.setter
    def is_leave_maze(self, value):
        self.state.should_leave_maze = bool(value)

    @property
    def isLeaveMaze(self):
        return self.is_leave_maze

    @isLeaveMaze.setter
    def isLeaveMaze(self, value):
        self.is_leave_maze = value

    def load_config(self, context: Context) -> None:
        target = _read_setting(
            context,
            "Map91_Target_Layer_Setting",
            self.config.target_leave_layer,
        )
        try:
            target = int(target)
        except (TypeError, ValueError):
            target = self.config.target_leave_layer
        if target < 1199:
            logger.warning(f"91-1201 目标层数被外部设置为{target}，已强制修正为1199")
            target = 1199
        self.config.target_leave_layer = min(1199, target)
        self.config.manual_leave = str(
            _read_setting(
                context,
                "Map91_ManualLeave_Setting",
                self.config.manual_leave,
            )
        )
        self.config.monster_phase_enabled = self._node_enabled(
            context,
            "Map91_MonsterPhase",
            self.config.monster_phase_enabled,
        )
        self.config.loot_phase_enabled = self._node_enabled(
            context,
            "Map91_LootPhase",
            self.config.loot_phase_enabled,
        )

    @staticmethod
    def _node_enabled(context: Context, node_name: str, default: bool) -> bool:
        try:
            node = context.get_node_data(node_name)
            value = node.get("enabled", default)
        except (KeyError, TypeError, ValueError):
            return default
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "no")
        return bool(value)

    def initialize(self, context: Context) -> bool:
        self.state = Map91State()
        Map91EventDispatcher.reset_runtime_state()
        self.dungeon_state = self.state.to_dungeon_state()
        self.hp_manager = Map91HPManager(self)
        self.boss_handler = Map91BossHandler(self)
        self.title_manager = Map91TitleManager(self)
        self.special_layer_manager = Map91SpecialLayerManager(self)
        self.earth_gate_manager = Map91EarthGateManager(self)
        self.events_dispatcher = Map91EventDispatcher(self)
        self.fighter_skill_manager = Map91FighterSkillManager(self)
        self.settlement_manager = Map91SettlementManager(self)
        self.downstair_manager = FightDownstairManager(self)

        context.run_task("Fight_ReturnMainWindow")
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.error("91-1201 初始化失败：无法识别当前层数")
            return False
        self.layers = layer
        self.dungeon_state.observe_layer(layer)
        logger.info(
            f"91-1201 初始化完成：当前{self.layers}层，"
            f"目标{self.config.target_leave_layer}层"
        )
        return True

    def build_dungeon_runner(self) -> DungeonRunner:
        boss_registry = BossStrategyRegistry()
        boss_registry.set_fallback(
            CallableBossStrategy(
                lambda context, state: self.boss_handler.handle_boss_event(context),
                "91-1201 Boss回退",
            )
        )

        normal_runner = NormalLayerRunner(
            phases=(
                MonsterPhase(
                    lambda context, state: bool(self.run_monster_phase(context))
                ),
                LootPhase(lambda context, state: bool(self.run_loot_phase(context))),
            )
        )
        return DungeonRunner(
            state=self.dungeon_state,
            target_layer=self.config.target_leave_layer,
            max_same_layer_retries=self.config.max_same_layer_retries,
            read_layer=self._read_layer_for_runner,
            is_boss_layer=lambda layer: layer >= 30 and layer % 10 == 0,
            before_layer=lambda context, state: self._before_layer_for_runner(
                context, state
            ),
            interrupt=lambda context, state: self._interrupt_for_runner(
                context, state
            ),
            after_layer=lambda context, state: self._after_layer_for_runner(
                context, state
            ),
            normal_layers=normal_runner,
            boss_strategies=boss_registry,
        )

    def _read_layer_for_runner(self, context: Context) -> int:
        layer = fightUtils.handle_currentlayer_event(context)
        if layer > 0:
            self.layers = layer
        return layer

    def _before_layer_for_runner(self, context: Context, state: DungeonState) -> bool:
        self.state.sync_from_dungeon_state(state)
        return bool(self.handle_pre_layers_event(context))

    def _interrupt_for_runner(self, context: Context, state: DungeonState) -> bool:
        self.state.sync_from_dungeon_state(state)
        return bool(self.handle_interrupt_event(context))

    def _after_layer_for_runner(self, context: Context, state: DungeonState) -> bool:
        self.state.sync_from_dungeon_state(state)
        result = self.handle_post_layers_event(context)
        state.should_leave = self.is_leave_maze
        self.state.sync_from_dungeon_state(state)
        return bool(result)

    def check_current_layers(self, context: Context) -> bool:
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.warning("91-1201 层数识别失败，本轮不更新层数")
            return False
        if layer != self.state.last_observed_layer:
            self.state.same_layer_retries = 0
            self.state.last_observed_layer = layer
            self.state.earth_gate_checked_layer = -1
        self.layers = layer
        return True

    def clear_current_layer(self, context: Context):
        return context.run_task(
            "Map91_Fight_ClearCurrentLayer",
            pipeline_override={
                "Map91_Fight_ClearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )

    @timing_decorator
    def handle_pre_layers_event(self, context: Context) -> bool:
        self.hp_manager.check_default_status(context)
        self.title_manager.check_default_title(context)
        return True

    @timing_decorator
    def run_monster_phase(self, context: Context) -> bool:
        if not self.config.monster_phase_enabled:
            logger.info(f"91-1201 第{self.layers}层：小怪层刷怪阶段已关闭")
            return True
        logger.info(f"91-1201 第{self.layers}层：执行小怪层刷怪阶段")
        if not self.fighter_skill_manager.cast_douqi_burst(context):
            return False
        succeeded = bool(self.clear_current_layer(context))
        context.run_task("ConfirmButton_500ms")
        context.run_task("Fight_ReturnMainWindow")
        return succeeded

    @timing_decorator
    def run_loot_phase(self, context: Context) -> bool:
        if not self.config.loot_phase_enabled:
            logger.info(f"91-1201 第{self.layers}层：小怪层搜刮阶段已关闭")
            return True
        logger.info(f"91-1201 第{self.layers}层：执行小怪层搜刮阶段")
        for _ in range(6):
            if context.tasker.stopping:
                return False
            context.run_task("Fight_ReturnMainWindow")
            image = context.tasker.controller.post_screencap().wait().get()
            if self.events_dispatcher.handle_events(context, image=image):
                context.run_task("Fight_ReturnMainWindow")
                continue
            if self.special_layer_manager.handle_special_layer_event(context, image):
                context.run_task("Fight_ReturnMainWindow")
                continue
            break
        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context) -> bool:
        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.warning("91-1201 检测到死亡，执行小 SL")
            fightUtils.Saveyourlife(context)
            return False
        if self.events_dispatcher.handle_events(context, image=image):
            context.run_task("Fight_ReturnMainWindow")
            return False
        if context.run_recognition("BackText", image).hit:
            context.run_task("Fight_ReturnMainWindow")
            return False
        return True

    @timing_decorator
    def handle_post_layers_event(self, context: Context) -> bool:
        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        if self.special_layer_manager.handle_special_layer_event(context, image):
            return False
        if not context.run_recognition("Fight_OpenedDoor", image).hit:
            return False
        if self.earth_gate_manager.handle_earth_gate_event(context):
            return False
        if self.layers >= self.config.target_leave_layer:
            return self.settlement_manager.handle_before_leave_maze_event(context)
        return self.downstair_manager.handle_downstair_event(context)

    def _recover_stalled_layer(self, context: Context) -> None:
        logger.error(
            f"91-1201 在{self.layers}层连续重试"
            f"{self.state.same_layer_retries}次，停止并保留现场"
        )
        context.run_task("Screenshot")
        context.run_task("Fight_ReturnMainWindow")

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        del argv
        self.load_config(context)
        if not self.initialize(context):
            return CustomAction.RunResult(success=False)

        self.dungeon_runner = self.build_dungeon_runner()
        result = self.dungeon_runner.run(context)
        self.state.sync_from_dungeon_state(self.dungeon_state)
        if result.status.value == "stopped":
            logger.info("检测到停止任务，退出91-1201 agent")
            return CustomAction.RunResult(success=False)
        if not result.ok:
            self._recover_stalled_layer(context)
            return CustomAction.RunResult(success=False)

        logger.info(f"91-1201 探索结束，当前到达{self.layers}层")
        if self.config.manual_leave in ("暂离", "保存暂离", "暂停"):
            context.run_task("Save_Status")
            send_message("MaaGB", f"91-1201 到达{self.layers}层，已暂离保存")
        else:
            context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Map91_Fight_ClearCurrentLayer")
class Map91FightClearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fight_processor = fightProcessor.FightProcessor()
        self.fight_processor.targetWish = "工资"

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
                logger.warning("91-1201 清层参数解析失败，沿用当前层数")
        if layers_arg is not None:
            self.fight_processor.layers = int(layers_arg)
        self.fight_processor.targetWish = "工资"
        self.fight_processor.grid_count = 40
        self.fight_processor.max_grid_loop = 40
        with fightUtils.timing_section("map91.fight.clear_current_layer"):
            succeeded = self.fight_processor.clearCurrentLayer(
                context,
                isclearall=True,
            )
        return CustomAction.RunResult(success=bool(succeeded))


def _new_map91_fight_processor(layers: int | None = None):
    processor = fightProcessor.FightProcessor()
    processor.targetWish = "工资"
    processor.grid_count = 40
    processor.max_grid_loop = 40
    processor.isCheckDragon = False
    processor.last_door_grid = None
    processor.last_door_kind = None
    processor.last_door_layer = None
    processor.visited = [[0] * processor.cols for _ in range(processor.rows)]
    if layers is not None:
        processor.layers = int(layers)
    return processor


@AgentServer.custom_action("Map91_Debug_MonsterPhase")
class Map91DebugMonsterPhase(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        del argv
        logger.info("91-1201 小怪层打怪调试启动")
        detected_layer = fightUtils.handle_currentlayer_event(context)
        skill_manager = Map91FighterSkillManager()
        if not skill_manager.cast_douqi_burst(context):
            return CustomAction.RunResult(success=False)
        processor = _new_map91_fight_processor(
            detected_layer if detected_layer > 0 else None
        )
        with fightUtils.timing_section("map91.debug_monster_phase"):
            succeeded = processor.clearCurrentLayer(context, isclearall=True)
        context.run_task("ConfirmButton_500ms")
        context.run_task("Fight_ReturnMainWindow")
        logger.info("91-1201 小怪层打怪调试完成：已执行翻地板和打怪")
        return CustomAction.RunResult(
            success=bool(succeeded) and not context.tasker.stopping
        )


@AgentServer.custom_action("Map91_Debug_LootPhase")
class Map91DebugLootPhase(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        del argv
        logger.info("91-1201 小怪层搜刮调试启动")
        detected_layer = fightUtils.handle_currentlayer_event(context)
        map91 = Map91()
        map91.layers = detected_layer if detected_layer > 0 else 1
        map91.events_dispatcher = Map91EventDispatcher(map91)
        map91.special_layer_manager = Map91SpecialLayerManager(map91)

        event_count = 0
        no_event_count = 0
        for _ in range(6):
            if context.tasker.stopping:
                return CustomAction.RunResult(success=False)
            context.run_task("Fight_ReturnMainWindow")
            image = context.tasker.controller.post_screencap().wait().get()
            if map91.events_dispatcher.handle_events(context, image=image):
                event_count += 1
                no_event_count = 0
                continue
            if map91.special_layer_manager.handle_special_layer_event(
                context,
                image=image,
            ):
                event_count += 1
                no_event_count = 0
                continue
            no_event_count += 1
            if no_event_count >= 2:
                break

        logger.info(
            f"91-1201 小怪层搜刮调试完成，处理事件{event_count}次，"
            f"连续未命中{no_event_count}轮"
        )
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Map91_ContinuousMonsterLoop")
class Map91ContinuousMonsterLoop(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        del argv
        logger.info("91-1201 连续小怪层调试启动：仅执行清图和下楼")

        processor = _new_map91_fight_processor()
        downstair_manager = FightDownstairManager(Map91())
        current_layer = fightUtils.handle_currentlayer_event(context)
        if current_layer > 0:
            downstair_manager.mars.layers = current_layer

        rounds = 0
        while not context.tasker.stopping:
            if current_layer <= 0:
                current_layer = fightUtils.handle_currentlayer_event(context)
                if current_layer <= 0:
                    logger.error("91-1201 连续小怪层调试：无法识别当前层数")
                    return CustomAction.RunResult(success=False)
                downstair_manager.mars.layers = current_layer

            tail = current_layer % 10
            logger.info(
                f"91-1201 连续小怪层调试：第{rounds + 1}轮，当前{current_layer}层，尾号{tail}"
            )
            skill_manager = Map91FighterSkillManager()
            if not skill_manager.cast_douqi_burst(context):
                return CustomAction.RunResult(success=False)
            with fightUtils.timing_section("map91.continuous_monster.clear"):
                succeeded = processor.clearCurrentLayer(context, isclearall=True)
            if not succeeded or context.tasker.stopping:
                return CustomAction.RunResult(success=False)

            if tail == 9:
                logger.info(
                    f"91-1201 连续小怪层调试：尾号9层已清完，停在{current_layer}层"
                )
                return CustomAction.RunResult(success=True)

            if not downstair_manager.handle_downstair_event(context):
                logger.warning(
                    f"91-1201 连续小怪层调试：第{current_layer}层下楼失败，停止循环"
                )
                return CustomAction.RunResult(success=False)

            time.sleep(0.3)
            current_layer = fightUtils.handle_currentlayer_event(context)
            if current_layer <= 0:
                logger.error("91-1201 连续小怪层调试：下楼后层数识别失败")
                return CustomAction.RunResult(success=False)
            downstair_manager.mars.layers = current_layer
            rounds += 1

        logger.info(f"91-1201 连续小怪层调试结束，当前停在{current_layer}层")
        return CustomAction.RunResult(success=not context.tasker.stopping)


@AgentServer.custom_action("Map91_Debug_FighterSkill")
class Map91DebugFighterSkill(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        del argv
        logger.info("91-1201 格斗家技能调试启动")
        skill_manager = Map91FighterSkillManager()
        succeeded = skill_manager.cast_douqi_burst(context)
        context.run_task("Fight_ReturnMainWindow")
        logger.info(f"91-1201 格斗家技能调试完成：{'成功' if succeeded else '失败'}")
        return CustomAction.RunResult(success=bool(succeeded))
