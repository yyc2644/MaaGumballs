import json
import time
from dataclasses import dataclass

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from action.fight import fightProcessor, fightUtils
from action.fight.downstair import FightDownstairManager
from action.fight.fightUtils import timing_decorator
from action.sleeptown.sleeptown_boss import SleeptownBossHandler
from action.sleeptown.sleeptown_earth_gate import SleeptownEarthGateManager
from action.sleeptown.sleeptown_events import SleeptownEventDispatcher
from action.sleeptown.sleeptown_hp import SleeptownHPManager
from action.sleeptown.sleeptown_periodic import SleeptownPeriodicManager
from action.sleeptown.sleeptown_settlement import SleeptownSettlementManager
from action.sleeptown.sleeptown_special_layer import SleeptownSpecialLayerManager
from action.sleeptown.sleeptown_title import SleeptownTitleManager
from utils import logger, send_message


@dataclass
class SleeptownConfig:
    """由 interface pipeline override 控制的运行参数。"""

    target_leave_layer: int = 1201
    manual_leave: str = "自动结算"
    max_same_layer_retries: int = 12


@dataclass
class SleeptownState:
    layers: int = 1
    should_leave_maze: bool = False
    same_layer_retries: int = 0
    last_observed_layer: int = -1
    preprocessed_layer: int = -1
    earth_gate_checked_layer: int = -1
    floor49_visit_count: int = 0
    floor51_visit_count: int = 0
    floor51_retreat_attempted_visit: int = 0


@AgentServer.custom_action("Sleeptown1201")
class Sleeptown1201(CustomAction):
    """沉眠小镇 1201 层长线探索主流程。

    类似 Mars101，本类只负责编排；地图事件、Boss、称号、生存、特殊层、
    大地之门和结算分别由 action/sleeptown 下的模块负责。
    """

    def __init__(self):
        super().__init__()
        self.config = SleeptownConfig()
        self.state = SleeptownState()
        self.hp_manager = None
        self.periodic_manager = None
        self.boss_handler = None
        self.title_manager = None
        self.special_layer_manager = None
        self.earth_gate_manager = None
        self.events_dispatcher = None
        self.settlement_manager = None
        self.downstair_manager = None

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

    @staticmethod
    def _node_expected(context: Context, node_name: str, default):
        try:
            value = context.get_node_data(node_name)["recognition"]["param"]["expected"]
            if isinstance(value, (list, tuple)):
                value = value[0] if value else default
            return value
        except (KeyError, TypeError, ValueError, IndexError):
            logger.warning(f"读取配置 {node_name} 失败，使用默认值 {default}")
            return default

    def load_config(self, context: Context):
        target = self._node_expected(
            context,
            "Sleeptown_Target_Layer_Setting",
            self.config.target_leave_layer,
        )
        try:
            target = int(target)
        except (TypeError, ValueError):
            target = self.config.target_leave_layer
        self.config.target_leave_layer = max(1, min(1201, target))
        self.config.manual_leave = str(
            self._node_expected(
                context,
                "Sleeptown_ManualLeave_Setting",
                self.config.manual_leave,
            )
        )

    def initialize(self, context: Context):
        self.state = SleeptownState()
        self.hp_manager = SleeptownHPManager(self)
        self.periodic_manager = SleeptownPeriodicManager(self)
        self.boss_handler = SleeptownBossHandler(self)
        self.title_manager = SleeptownTitleManager(self)
        self.special_layer_manager = SleeptownSpecialLayerManager(self)
        self.earth_gate_manager = SleeptownEarthGateManager(self)
        self.events_dispatcher = SleeptownEventDispatcher(self)
        self.settlement_manager = SleeptownSettlementManager(self)
        self.downstair_manager = FightDownstairManager(self)

        context.run_task("Fight_ReturnMainWindow")
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.error("沉眠小镇初始化失败：无法识别当前层数")
            return False
        self.layers = layer
        logger.info(
            f"沉眠小镇初始化完成：当前{self.layers}层，"
            f"目标{self.config.target_leave_layer}层"
        )
        return True

    def check_current_layers(self, context: Context):
        layer = fightUtils.handle_currentlayer_event(context)
        if layer <= 0:
            logger.warning("沉眠小镇层数识别失败，本轮不更新层数")
            return False
        if layer != self.state.last_observed_layer:
            self.state.same_layer_retries = 0
            self.state.last_observed_layer = layer
            self.state.earth_gate_checked_layer = -1
            if layer == 49:
                self.state.floor49_visit_count += 1
                logger.info(
                    "沉眠小镇本次运行第"
                    f"{self.state.floor49_visit_count}次到达49层"
                )
            elif layer == 51:
                self.state.floor51_visit_count += 1
                logger.info(
                    "沉眠小镇本次运行第"
                    f"{self.state.floor51_visit_count}次到达51层"
                )
        self.layers = layer
        return True

    def clear_current_layer(self, context: Context):
        return context.run_task(
            "Sleeptown_Fight_ClearCurrentLayer",
            pipeline_override={
                "Sleeptown_Fight_ClearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )

    @timing_decorator
    def handle_pre_layers_event(self, context: Context):
        self.hp_manager.check_default_status(context)
        self.periodic_manager.handle_pre_layer(context)
        self.title_manager.check_default_title(context)
        return True

    @timing_decorator
    def handle_clear_current_layer_event(self, context: Context):
        if self.layers >= 30 and self.layers % 10 == 0:
            return bool(self.boss_handler.handle_boss_event(context))
        return bool(self.clear_current_layer(context))

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.warning("沉眠小镇检测到死亡，执行小 SL")
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
    def handle_post_layers_event(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        if self.special_layer_manager.handle_special_layer_event(context, image):
            return False

        image = context.tasker.controller.post_screencap().wait().get()
        if not context.run_recognition("Fight_OpenedDoor", image).hit:
            return False
        if self.handle_floor_51_retreat(context):
            return False
        if self.earth_gate_manager.handle_earth_gate_event(context):
            return False
        if self.layers >= self.config.target_leave_layer:
            return self.settlement_manager.handle_before_leave_maze_event(context)
        return self.downstair_manager.handle_downstair_event(context)

    def handle_floor_51_retreat(self, context: Context) -> bool:
        """51层清层后优先使用一件“退退退”，成功触发时禁止下楼。"""
        if self.layers != 51:
            return False

        visit = self.state.floor51_visit_count
        if self.state.floor51_retreat_attempted_visit == visit:
            logger.warning("沉眠小镇51层已使用过退退退，等待层数变化，不执行下楼")
            return True

        used = self.periodic_manager.use_one_item(
            context,
            "退退退",
            "fight/Sleeptown/Item/退退退.png",
        )
        if not used:
            logger.info("沉眠小镇51层背包没有退退退，继续正常下楼")
            return False

        self.state.floor51_retreat_attempted_visit = visit
        logger.info("沉眠小镇51层已使用一件退退退，等待层数变化")
        for _ in range(15):
            time.sleep(1)
            if self.check_current_layers(context) and self.layers != 51:
                self.state.preprocessed_layer = -1
                logger.info(f"退退退已生效，当前回到{self.layers}层")
                return True

        logger.warning("使用退退退后15秒内层数未变化，保留现场且不执行下楼")
        context.run_task("Screenshot")
        return True

    def _recover_stalled_layer(self, context: Context):
        logger.error(
            f"沉眠小镇在{self.layers}层连续重试"
            f"{self.state.same_layer_retries}次，停止并保留现场"
        )
        context.run_task("Screenshot")
        context.run_task("Fight_ReturnMainWindow")

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
                logger.info("检测到停止任务，退出沉眠小镇 agent")
                return CustomAction.RunResult(success=False)
            if not self.check_current_layers(context):
                time.sleep(1)
                continue
            if self.state.same_layer_retries >= self.config.max_same_layer_retries:
                self._recover_stalled_layer(context)
                return CustomAction.RunResult(success=False)

            logger.info(f"Start Sleeptown Explore {self.layers} layer.")
            if self.state.preprocessed_layer != self.layers:
                self.handle_pre_layers_event(context)
                self.state.preprocessed_layer = self.layers
            if not self.handle_clear_current_layer_event(context):
                self.state.same_layer_retries += 1
                continue
            if not self.handle_interrupt_event(context):
                self.state.same_layer_retries += 1
                continue
            if not self.handle_post_layers_event(context):
                self.state.same_layer_retries += 1
                continue
            if self.is_leave_maze:
                break

        logger.info(f"沉眠小镇探索结束，当前到达{self.layers}层")
        if self.config.manual_leave in ("暂离", "保存暂离"):
            context.run_task("Save_Status")
            send_message("MaaGB", f"沉眠小镇到达{self.layers}层，已暂离保存")
        else:
            context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Sleeptown_Fight_ClearCurrentLayer")
class SleeptownFightClearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fight_processor = fightProcessor.FightProcessor()
        self.fight_processor.targetWish = "沉眠小镇"

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
                logger.warning("沉眠小镇清层参数解析失败，沿用当前层数")
        if layers_arg is not None:
            self.fight_processor.layers = int(layers_arg)
        # 沉眠小镇沿用 Mars 的通用清层参数：提高地板颜色匹配像素阈值，
        # 并要求清完全部可点击格子后才结束本层。
        self.fight_processor.grid_count = 40
        with fightUtils.timing_section("fight.normal_processor_total"):
            succeeded = self.fight_processor.clearCurrentLayer(
                context,
                isclearall=True,
            )
        return CustomAction.RunResult(success=bool(succeeded))
