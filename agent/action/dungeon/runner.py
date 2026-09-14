from collections.abc import Callable

from maa.context import Context

from action.dungeon.boss import BossStrategyRegistry
from action.dungeon.normal_layer import NormalLayerRunner
from action.dungeon.phase import PhaseResult
from action.dungeon.state import DungeonState
from utils import logger


class DungeonRunner:
    """通用副本逐层状态机。"""

    def __init__(
        self,
        state: DungeonState,
        target_layer: int,
        max_same_layer_retries: int,
        read_layer: Callable[[Context], int],
        is_boss_layer: Callable[[int], bool],
        before_layer: Callable[[Context, DungeonState], bool],
        interrupt: Callable[[Context, DungeonState], bool],
        after_layer: Callable[[Context, DungeonState], bool],
        normal_layers: NormalLayerRunner,
        boss_strategies: BossStrategyRegistry,
    ):
        self.state = state
        self.target_layer = target_layer
        self.max_same_layer_retries = max_same_layer_retries
        self.read_layer = read_layer
        self.is_boss_layer = is_boss_layer
        self.before_layer = before_layer
        self.interrupt = interrupt
        self.after_layer = after_layer
        self.normal_layers = normal_layers
        self.boss_strategies = boss_strategies

    def run(self, context: Context) -> PhaseResult:
        while self.state.current_layer <= self.target_layer:
            if context.tasker.stopping:
                return PhaseResult.stopped("task_stopped")

            layer = self.read_layer(context)
            if layer <= 0:
                self.state.mark_retry()
                continue
            self.state.observe_layer(layer)

            if self.state.same_layer_retries >= self.max_same_layer_retries:
                logger.error(
                    f"通用副本在{self.state.current_layer}层连续重试"
                    f"{self.state.same_layer_retries}次"
                )
                return PhaseResult.failed("same_layer_retry_limit")

            logger.info(f"通用副本流程：开始处理第{self.state.current_layer}层")
            if self.state.preprocessed_layer != self.state.current_layer:
                if not self.before_layer(context, self.state):
                    self.state.mark_retry()
                    continue
                self.state.preprocessed_layer = self.state.current_layer

            if self.is_boss_layer(self.state.current_layer):
                result = self.boss_strategies.run(context, self.state)
            else:
                result = self.normal_layers.run(context, self.state)
            if not result.ok:
                self.state.mark_retry()
                continue

            if not self.interrupt(context, self.state):
                self.state.mark_retry()
                continue
            if not self.after_layer(context, self.state):
                self.state.mark_retry()
                continue
            if self.state.should_leave:
                return PhaseResult.success()

        return PhaseResult.success()
