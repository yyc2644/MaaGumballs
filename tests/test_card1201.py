import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.card.card_events import CardEventDispatcher
from action.card.card_hp import CardHPManager
from action.card.card_settlement import CardSettlementManager
from action.fight import fightUtils
from action.fight.card1201 import Card1201
from action.fight.downstair import FightDownstairManager


class FakeWait:
    def wait(self):
        return self


class FakeController:
    def __init__(self):
        self.clicks = []

    def post_click(self, x, y):
        self.clicks.append((x, y))
        return FakeWait()


class FakeContext:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.tasks = []
        self.tasker = SimpleNamespace(controller=FakeController(), stopping=False)

    def get_node_data(self, name):
        value = self.settings[name]
        return {"recognition": {"param": {"expected": [value]}}}

    def run_task(self, name, **kwargs):
        self.tasks.append(name)
        return SimpleNamespace(nodes=[])

    def run_recognition(self, name, image=None, **kwargs):
        return SimpleNamespace(hit=False)


class CardConfigTests(unittest.TestCase):
    def test_loads_exact_target_and_leave_mode(self):
        card = Card1201()
        context = FakeContext(
            {
                "Card_Target_Layer_Setting": "601",
                "Card_ManualLeave_Setting": "保存暂离",
            }
        )
        card.load_config(context)
        self.assertEqual(card.config.target_leave_layer, 601)
        self.assertEqual(card.config.manual_leave, "保存暂离")

    def test_target_is_clamped_to_supported_long_run(self):
        card = Card1201()
        context = FakeContext(
            {
                "Card_Target_Layer_Setting": "9999",
                "Card_ManualLeave_Setting": "自动结算",
            }
        )
        card.load_config(context)
        self.assertEqual(card.config.target_leave_layer, 1201)


class CardSettlementTests(unittest.TestCase):
    def test_does_not_leave_before_exact_target(self):
        card = Card1201()
        card.config.target_leave_layer = 95
        manager = CardSettlementManager(card)
        context = FakeContext()
        card.layers = 94
        self.assertFalse(manager.handle_before_leave_maze_event(context))
        self.assertFalse(card.isLeaveMaze)

        card.layers = 95
        self.assertTrue(manager.handle_before_leave_maze_event(context))
        self.assertTrue(card.isLeaveMaze)
        self.assertIn("Screenshot", context.tasks)

    def test_stall_recovery_keeps_maze_state_for_debugging(self):
        card = Card1201()
        card.layers = 37
        card.state.same_layer_retries = 12
        context = FakeContext()
        self.assertFalse(card.recover_stalled_layer(context))
        self.assertNotIn("Save_Status", context.tasks)
        self.assertIn("Screenshot", context.tasks)
        self.assertEqual(card.state.same_layer_retries, 0)

    def test_earth_gate_schedule_starts_at_49_and_rechecks_each_visit(self):
        card = Card1201()
        for layer, expected in [(39, False), (48, False), (49, True), (59, True)]:
            card.layers = layer
            card.state.earth_gate_checked_layer = -1
            self.assertEqual(card.should_try_earth_gate(), expected)

        card.layers = 49
        card.state.earth_gate_checked_layer = 49
        self.assertFalse(card.should_try_earth_gate())
        card.state.earth_gate_checked_layer = -1
        self.assertTrue(card.should_try_earth_gate())


class CardCombatPreparationTests(unittest.TestCase):
    def test_small_layer_preparation_runs_once_per_floor(self):
        card = Card1201()
        card.layers = 12
        context = FakeContext()
        with patch.object(card, "cast_card_skill", return_value=True) as meditate, patch.object(
            card, "cast_four_symbols", return_value=True
        ) as four_symbols:
            card.run_small_monster_layer_script(context)
            card.run_small_monster_layer_script(context)
        self.assertEqual(meditate.call_count, 1)
        self.assertEqual(four_symbols.call_count, 1)


class CardEventTests(unittest.TestCase):
    def test_safe_choice_marks_meditation(self):
        card = Card1201()
        dispatcher = CardEventDispatcher(card)
        context = FakeContext()
        with patch.object(
            fightUtils, "click_text_by_priority", return_value="交流"
        ):
            self.assertTrue(dispatcher._handle_safe_choice(context, object()))
        self.assertTrue(card.state.maybe_has_meditation)

    def test_ocr_normalization_handles_common_variants(self):
        self.assertEqual(
            fightUtils.normalize_ocr_text("我要學習龍語魔法！"),
            "我要学习龙语魔法",
        )

    def test_empty_dragon_ocr_returns_false_instead_of_crashing(self):
        context = FakeContext()
        with patch.object(fightUtils.time, "sleep", return_value=None):
            self.assertFalse(fightUtils.dragonwish("卡牌幻境", context))


class CardHPTests(unittest.TestCase):
    def test_hp_ratio(self):
        card = Card1201()
        manager = CardHPManager(card)
        self.assertEqual(
            manager._hp_ratio({"当前生命值": "75", "最大生命值": "100"}),
            0.75,
        )
        self.assertEqual(manager._hp_ratio({}), 1.0)


class DownstairTests(unittest.TestCase):
    def test_invalid_old_layer_is_never_reported_as_changed(self):
        card = Card1201()
        manager = FightDownstairManager(card)
        changed, current, attempts = manager._wait_until_layer_changed(
            FakeContext(), -1
        )
        self.assertFalse(changed)
        self.assertEqual(current, -1)
        self.assertEqual(attempts, 0)


if __name__ == "__main__":
    unittest.main()
