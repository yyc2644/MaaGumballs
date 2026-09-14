import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.dungeon.boss import BossStrategyRegistry, CallableBossStrategy
from action.dungeon.normal_layer import (
    LootPhase,
    MonsterPhase,
    NormalLayerRunner,
)
from action.dungeon.phase import PhaseResult
from action.dungeon.runner import DungeonRunner
from action.dungeon.state import DungeonState


class FakeContext:
    def __init__(self, stopping=False):
        self.tasker = SimpleNamespace(stopping=stopping)


class DungeonArchitectureTests(unittest.TestCase):
    def test_normal_phases_run_in_order(self):
        calls = []
        runner = NormalLayerRunner(
            phases=(
                MonsterPhase(lambda context, state: calls.append("monster") or True),
                LootPhase(lambda context, state: calls.append("loot") or True),
            )
        )

        result = runner.run(FakeContext(), SimpleNamespace(current_layer=1))

        self.assertTrue(result.ok)
        self.assertEqual(calls, ["monster", "loot"])

    def test_boss_registry_dispatches_exact_floor_then_fallback(self):
        calls = []
        registry = BossStrategyRegistry()
        registry.register(
            30,
            CallableBossStrategy(
                lambda context, state: calls.append("boss30") or True,
                "boss30",
            ),
        )
        registry.set_fallback(
            CallableBossStrategy(
                lambda context, state: calls.append("fallback") or True,
                "fallback",
            )
        )

        registry.run(FakeContext(), SimpleNamespace(current_layer=30))
        registry.run(FakeContext(), SimpleNamespace(current_layer=40))

        self.assertEqual(calls, ["boss30", "fallback"])

    def test_runner_retries_and_finishes_after_layer_change(self):
        state = DungeonState(current_layer=1)
        read_layers = iter([1, 1, 2, 2])
        calls = []

        runner = DungeonRunner(
            state=state,
            target_layer=2,
            max_same_layer_retries=3,
            read_layer=lambda context: next(read_layers, 2),
            is_boss_layer=lambda layer: False,
            before_layer=lambda context, layer_state: True,
            interrupt=lambda context, layer_state: True,
            after_layer=lambda context, layer_state: (
                calls.append(layer_state.current_layer)
                or setattr(layer_state, "should_leave", True)
                or True
            )
            if layer_state.current_layer == 2
            else True,
            normal_layers=NormalLayerRunner(
                phases=(
                    MonsterPhase(lambda context, layer_state: True),
                    LootPhase(lambda context, layer_state: True),
                )
            ),
            boss_strategies=BossStrategyRegistry(),
        )

        result = runner.run(FakeContext())

        self.assertEqual(result.status, PhaseResult.success().status)
        self.assertEqual(state.current_layer, 2)
        self.assertEqual(calls, [2])


if __name__ == "__main__":
    unittest.main()
