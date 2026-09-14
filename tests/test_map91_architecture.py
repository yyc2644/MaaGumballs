import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.dungeon.normal_layer import LootPhase, MonsterPhase
from action.fight.map91 import Map91, Map91Config
from action.map91.map91_events import Map91EventDispatcher


class FakeContext:
    def __init__(self):
        self.tasker = SimpleNamespace(stopping=False)


class Map91ArchitectureTests(unittest.TestCase):
    def test_default_target_layer_is_91(self):
        self.assertEqual(Map91Config().target_leave_layer, 1201)

    def test_normal_layer_is_split_into_monster_and_loot_phases(self):
        map91 = Map91()
        map91.config.target_leave_layer = 1
        map91.hp_manager = SimpleNamespace(check_default_status=Mock(return_value=True))
        map91.title_manager = SimpleNamespace(check_default_title=Mock(return_value=True))
        map91.boss_handler = SimpleNamespace(handle_boss_event=Mock(return_value=True))
        map91.events_dispatcher = SimpleNamespace(handle_events=Mock(return_value=False))
        map91.special_layer_manager = SimpleNamespace(
            handle_special_layer_event=Mock(return_value=False)
        )
        map91.earth_gate_manager = SimpleNamespace(
            handle_earth_gate_event=Mock(return_value=False)
        )
        map91.settlement_manager = SimpleNamespace(
            handle_before_leave_maze_event=Mock(return_value=True)
        )
        map91.downstair_manager = SimpleNamespace(
            handle_downstair_event=Mock(return_value=True)
        )

        runner = map91.build_dungeon_runner()

        self.assertIsInstance(runner.normal_layers.phases[0], MonsterPhase)
        self.assertIsInstance(runner.normal_layers.phases[1], LootPhase)

    def test_event_dispatcher_is_currently_placeholder(self):
        dispatcher = Map91EventDispatcher(SimpleNamespace(layers=1))

        self.assertFalse(dispatcher.handle_events(FakeContext()))


if __name__ == "__main__":
    unittest.main()
