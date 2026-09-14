from collections.abc import Callable

from maa.context import Context

from action.dungeon.phase import PhaseResult
from utils import logger


class LayerPhase:
    name = "layer_phase"

    def run(self, context: Context, state) -> PhaseResult:
        raise NotImplementedError


class MonsterPhase(LayerPhase):
    """刷怪阶段扩展点。"""

    name = "monster"

    def __init__(self, callback: Callable[[Context, object], bool] | None = None):
        self.callback = callback

    def run(self, context: Context, state) -> PhaseResult:
        if self.callback is None:
            return PhaseResult.success(reason="monster_phase_not_implemented")
        return (
            PhaseResult.success()
            if self.callback(context, state)
            else PhaseResult.retry("monster_phase_failed")
        )


class LootPhase(LayerPhase):
    """搜刮阶段扩展点。"""

    name = "loot"

    def __init__(self, callback: Callable[[Context, object], bool] | None = None):
        self.callback = callback

    def run(self, context: Context, state) -> PhaseResult:
        if self.callback is None:
            return PhaseResult.success(reason="loot_phase_not_implemented")
        return (
            PhaseResult.success()
            if self.callback(context, state)
            else PhaseResult.retry("loot_phase_failed")
        )


class LegacyNormalLayerAdapter:
    """兼容旧 FightProcessor，待底层识别拆分后替换。"""

    def __init__(self, clear_layer: Callable[[Context, object], bool]):
        self.clear_layer = clear_layer

    def run(self, context: Context, state) -> PhaseResult:
        logger.debug("沉眠小镇普通层暂使用 FightProcessor 兼容适配器")
        return (
            PhaseResult.success()
            if self.clear_layer(context, state)
            else PhaseResult.retry("legacy_normal_layer_failed")
        )


class NormalLayerRunner:
    """执行普通层，当前支持显式阶段或旧清层适配器。"""

    def __init__(self, phases: tuple[LayerPhase, ...] | None = None,
                 legacy_adapter: LegacyNormalLayerAdapter | None = None):
        self.phases = phases
        self.legacy_adapter = legacy_adapter

    def run(self, context: Context, state) -> PhaseResult:
        if self.phases is None:
            if self.legacy_adapter is None:
                return PhaseResult.failed("normal_layer_runner_not_configured")
            return self.legacy_adapter.run(context, state)

        for phase in self.phases:
            if context.tasker.stopping:
                return PhaseResult.stopped(f"stopped_in_{phase.name}_phase")
            result = phase.run(context, state)
            if not result.ok:
                return result
        return PhaseResult.success()
