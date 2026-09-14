from collections.abc import Callable
from typing import Protocol

from maa.context import Context

from action.dungeon.phase import PhaseResult
from utils import logger


class BossStrategy(Protocol):
    def run(self, context: Context, state) -> PhaseResult:
        ...


class BossStrategyRegistry:
    """按楼层分派固定 Boss 解法。"""

    def __init__(self) -> None:
        self._strategies: dict[int, BossStrategy] = {}
        self._fallback: BossStrategy | None = None

    def register(self, layer: int, strategy: BossStrategy) -> None:
        if layer <= 0:
            raise ValueError("Boss layer must be positive")
        self._strategies[layer] = strategy

    def set_fallback(self, strategy: BossStrategy) -> None:
        self._fallback = strategy

    def get(self, layer: int) -> BossStrategy | None:
        return self._strategies.get(layer, self._fallback)

    def run(self, context: Context, state) -> PhaseResult:
        strategy = self.get(state.current_layer)
        if strategy is None:
            logger.warning(f"第{state.current_layer}层没有注册Boss策略")
            return PhaseResult.failed("boss_strategy_missing")
        return strategy.run(context, state)


class CallableBossStrategy:
    def __init__(self, callback: Callable[[Context, object], bool], name: str):
        self.callback = callback
        self.name = name

    def run(self, context: Context, state) -> PhaseResult:
        logger.info(f"执行Boss策略：{self.name}，第{state.current_layer}层")
        return (
            PhaseResult.success()
            if self.callback(context, state)
            else PhaseResult.retry(f"boss_strategy_failed:{self.name}")
        )
