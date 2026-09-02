import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))

from action.fight import fightUtils
from action.fight.sleeptown1201 import Sleeptown1201
from action.sleeptown.sleeptown_boss import BOSS_POS, SleeptownBossHandler
from action.sleeptown.sleeptown_divine_forge_sequence import (
    DivineForgeSequenceConfig,
    SleeptownDivineForgeSequenceTemplate,
)
from action.sleeptown.sleeptown_periodic import SleeptownPeriodicManager
from action.sleeptown.sleeptown_title import SleeptownTitleManager


class FakeContext:
    def __init__(self):
        self.tasks = []

    def run_task(self, name, **kwargs):
        del kwargs
        self.tasks.append(name)
        return SimpleNamespace(nodes=[object()])


class SleeptownPeriodicTests(unittest.TestCase):
    def test_schedule_uses_floors_ending_in_nine(self):
        expected = {
            8: False,
            9: True,
            18: False,
            19: True,
            49: True,
            50: False,
        }
        for layer, should_run in expected.items():
            with self.subTest(layer=layer):
                self.assertEqual(
                    SleeptownPeriodicManager.is_periodic_layer(layer),
                    should_run,
                )

    def test_periodic_check_runs_talent_items_and_equipment(self):
        manager = SleeptownPeriodicManager(SimpleNamespace(layers=29))
        context = FakeContext()
        with patch.object(
            manager, "check_activity_talent", return_value=True
        ) as talent, patch.object(
            manager, "consume_periodic_items"
        ) as consume, patch.object(manager, "equip_noble_set") as equip:
            self.assertTrue(manager.handle_pre_layer(context))

        talent.assert_called_once_with(context)
        consume.assert_called_once_with(context)
        equip.assert_called_once_with(context)
        self.assertEqual(context.tasks.count("Bag_Open"), 1)
        self.assertEqual(context.tasks[-1], "Fight_ReturnMainWindow")

    def test_uses_renamed_sleeptown_item_templates(self):
        self.assertEqual(
            SleeptownPeriodicManager.CONSUMABLES,
            (
                ("佛手", "fight/Sleeptown/Item/佛手.png"),
                ("宝钱", "fight/Sleeptown/Item/宝钱.png"),
                ("柿子", "fight/Sleeptown/Item/柿子.png"),
            ),
        )

    def test_noble_set_matches_mars_three_piece_set(self):
        self.assertEqual(
            SleeptownPeriodicManager.NOBLE_SET,
            (
                ("腰带", 1, "贵族丝带"),
                ("戒指", 2, "礼仪戒指"),
                ("披风", 3, "天鹅绒斗篷"),
            ),
        )

    def test_count_alert_reports_actual_counts_and_threshold(self):
        manager = SleeptownPeriodicManager(SimpleNamespace(layers=49))
        context = FakeContext()
        with patch.object(
            manager, "_read_item_count", side_effect=[3, 1]
        ), patch.object(fightUtils, "send_alert") as alert:
            counts = manager.check_target_item_counts(context)

        self.assertEqual(counts, {"退退退": 3, "吃瓜群众": 1})
        alert.assert_called_once_with(
            "沉眠小镇49层道具检查",
            "退退退：3（已达标）\n吃瓜群众：1（不足3个）",
        )
        self.assertTrue(manager.count_alert_sent)

    def test_missed_floor_49_count_check_runs_once_after_49(self):
        manager = SleeptownPeriodicManager(SimpleNamespace(layers=50))
        context = FakeContext()
        with patch.object(
            manager, "_read_item_count", side_effect=[0, 4]
        ), patch.object(fightUtils, "send_alert") as alert, patch.object(
            manager, "consume_periodic_items"
        ) as consume, patch.object(manager, "equip_noble_set") as equip:
            self.assertTrue(manager.handle_pre_layer(context))
            self.assertFalse(manager.handle_pre_layer(context))

        alert.assert_called_once()
        consume.assert_not_called()
        equip.assert_not_called()


class SleeptownTitleTests(unittest.TestCase):
    def test_plane_prophet_route_starts_at_49_and_runs_once(self):
        sleeptown = SimpleNamespace(
            layers=48,
            state=SimpleNamespace(floor49_visit_count=0),
        )
        manager = SleeptownTitleManager(sleeptown)
        context = FakeContext()

        with patch.object(fightUtils, "title_learn") as learn, patch.object(
            fightUtils, "title_learn_branch"
        ) as branch:
            self.assertFalse(manager.check_default_title(context))
            learn.assert_not_called()

            sleeptown.layers = 49
            self.assertTrue(manager.check_default_title(context))
            self.assertFalse(manager.check_default_title(context))

        self.assertEqual(
            [call.args[:4] for call in learn.call_args_list],
            [
                ("魔法", 1, "魔法学徒", 1),
                ("魔法", 2, "黑袍法师", 1),
                ("魔法", 3, "咒术师", 2),
                ("魔法", 4, "土系大师", 1),
                ("魔法", 5, "位面先知", 1),
                ("魔法", 2, "黑袍法师", 3),
            ],
        )
        self.assertEqual(
            [call.args[:4] for call in branch.call_args_list],
            [
                ("魔法", 5, "魔力强化", 3),
                ("魔法", 5, "生命强化", 3),
                ("魔法", 5, "魔法强化", 3),
            ],
        )

    def test_second_visit_calls_demon_title_placeholder_once(self):
        sleeptown = SimpleNamespace(
            layers=49,
            state=SimpleNamespace(floor49_visit_count=2),
        )
        manager = SleeptownTitleManager(sleeptown)
        manager.magic_route_checked = True
        context = FakeContext()

        with patch.object(
            manager, "ensure_demon_titles", return_value=True
        ) as demon:
            self.assertTrue(manager.check_default_title(context))
            self.assertFalse(manager.check_default_title(context))

        demon.assert_called_once_with(context)
        self.assertTrue(manager.demon_route_checked)

    def test_third_visit_finishes_great_sword_and_weapon_master(self):
        sleeptown = SimpleNamespace(
            layers=49,
            state=SimpleNamespace(floor49_visit_count=3),
        )
        manager = SleeptownTitleManager(sleeptown)
        manager.magic_route_checked = True
        manager.demon_route_checked = True
        context = FakeContext()

        with patch.object(fightUtils, "title_learn") as learn:
            self.assertTrue(manager.check_default_title(context))

        self.assertEqual(
            [call.args[:4] for call in learn.call_args_list],
            [
                ("战斗", 1, "见习战士", 3),
                ("战斗", 2, "战士", 3),
                ("战斗", 3, "剑舞者", 3),
                ("战斗", 4, "大剑师", 3),
                ("冒险", 1, "寻宝者", 2),
                ("冒险", 2, "勘探家", 2),
                ("冒险", 3, "锻造师", 3),
                ("冒险", 4, "武器大师", 3),
            ],
        )
        self.assertTrue(manager.third_visit_titles_checked)


class SleeptownFloor49CounterTests(unittest.TestCase):
    def test_counts_real_arrivals_but_not_same_floor_retries(self):
        sleeptown = Sleeptown1201()
        context = FakeContext()
        with patch.object(
            fightUtils,
            "handle_currentlayer_event",
            side_effect=[49, 49, 50, 49],
        ):
            for _ in range(4):
                self.assertTrue(sleeptown.check_current_layers(context))

        self.assertEqual(sleeptown.state.floor49_visit_count, 2)

    def test_counts_each_real_arrival_at_floor_51(self):
        sleeptown = Sleeptown1201()
        context = FakeContext()
        with patch.object(
            fightUtils,
            "handle_currentlayer_event",
            side_effect=[51, 51, 49, 51],
        ):
            for _ in range(4):
                self.assertTrue(sleeptown.check_current_layers(context))

        self.assertEqual(sleeptown.state.floor51_visit_count, 2)


class SleeptownFloor51RetreatTests(unittest.TestCase):
    def _make_sleeptown(self):
        sleeptown = Sleeptown1201()
        sleeptown.layers = 51
        sleeptown.state.floor51_visit_count = 1
        sleeptown.periodic_manager = SimpleNamespace()
        return sleeptown

    def test_absent_retreat_item_allows_normal_downstairs_flow(self):
        sleeptown = self._make_sleeptown()
        context = FakeContext()
        sleeptown.periodic_manager.use_one_item = unittest.mock.Mock(
            return_value=False
        )

        self.assertFalse(sleeptown.handle_floor_51_retreat(context))
        sleeptown.periodic_manager.use_one_item.assert_called_once_with(
            context,
            "退退退",
            "fight/Sleeptown/Item/退退退.png",
        )

    def test_used_retreat_item_blocks_stairs_and_waits_for_layer_change(self):
        sleeptown = self._make_sleeptown()
        context = FakeContext()
        sleeptown.periodic_manager.use_one_item = unittest.mock.Mock(
            return_value=True
        )

        def return_to_earlier_floor(_context):
            sleeptown.layers = 49
            return True

        with patch.object(
            sleeptown, "check_current_layers", side_effect=return_to_earlier_floor
        ), patch("action.fight.sleeptown1201.time.sleep"):
            self.assertTrue(sleeptown.handle_floor_51_retreat(context))

        self.assertEqual(sleeptown.layers, 49)
        self.assertEqual(sleeptown.state.floor51_retreat_attempted_visit, 1)
        self.assertEqual(sleeptown.state.preprocessed_layer, -1)

    def test_same_floor_retry_never_consumes_a_second_item(self):
        sleeptown = self._make_sleeptown()
        sleeptown.state.floor51_retreat_attempted_visit = 1
        context = FakeContext()
        sleeptown.periodic_manager.use_one_item = unittest.mock.Mock()

        self.assertTrue(sleeptown.handle_floor_51_retreat(context))
        sleeptown.periodic_manager.use_one_item.assert_not_called()


class SleeptownBossTests(unittest.TestCase):
    def test_floor_30_dispatches_to_normal_attack_strategy(self):
        handler = SleeptownBossHandler(SimpleNamespace(layers=30))
        context = FakeContext()
        with patch.object(handler, "_is_boss_defeated", return_value=False), patch.object(
            handler, "_handle_floor_30", return_value=True
        ) as floor_30:
            self.assertTrue(handler.handle_boss_event(context))

        floor_30.assert_called_once_with(context)

    def test_floor_40_repeats_spell_combo_then_three_attacks(self):
        handler = SleeptownBossHandler(SimpleNamespace(layers=40))
        context = FakeContext()
        with patch.object(fightUtils, "cast_magic", return_value=True) as cast, patch.object(
            handler, "_normal_attack", side_effect=[False, False, False, True]
        ) as attack:
            self.assertTrue(handler._handle_floor_40(context))

        self.assertEqual(
            [call.args[:3] for call in cast.call_args_list],
            [
                ("气", "静电场", context),
                ("气", "瓦解射线", context),
                ("水", "冰锥术", context),
                ("气", "静电场", context),
                ("气", "瓦解射线", context),
                ("水", "冰锥术", context),
            ],
        )
        self.assertEqual(cast.call_args_list[1].args[3], BOSS_POS)
        self.assertEqual(cast.call_args_list[2].args[3], BOSS_POS)
        self.assertEqual(attack.call_count, 4)

    def test_floor_50_placeholder_does_not_attack(self):
        handler = SleeptownBossHandler(SimpleNamespace(layers=50))
        context = FakeContext()
        with patch.object(handler, "_is_boss_defeated", return_value=False), patch.object(
            handler, "_normal_attack"
        ) as attack:
            self.assertFalse(handler.handle_boss_event(context))

        attack.assert_not_called()


class SleeptownDivineForgeSequenceTemplateTests(unittest.TestCase):
    def test_template_is_disabled_and_empty_by_default(self):
        config = DivineForgeSequenceConfig.from_custom_action_param(None)

        self.assertFalse(config.enabled)
        self.assertEqual(
            config.missing_fields(),
            [
                "sequence_length",
                "candidate_names",
                "success_signal",
                "restore_strategy",
            ],
        )

    def test_template_parses_future_sequence_configuration(self):
        config = DivineForgeSequenceConfig.from_custom_action_param(
            {
                "enabled": True,
                "sequence_length": 12,
                "candidate_names": ["候选A", "候选B"],
                "success_signal": "属性变化",
                "restore_strategy": "小SL",
            }
        )

        self.assertTrue(config.enabled)
        self.assertEqual(config.sequence_length, 12)
        self.assertEqual(config.candidate_names, ["候选A", "候选B"])
        self.assertEqual(config.missing_fields(), [])

    def test_unimplemented_sequence_runner_performs_no_action(self):
        action = SleeptownDivineForgeSequenceTemplate()
        config = DivineForgeSequenceConfig(
            enabled=True,
            sequence_length=1,
            candidate_names=["候选A"],
            success_signal="属性变化",
            restore_strategy="小SL",
        )

        self.assertEqual(action.run_sequence(FakeContext(), config), [])


if __name__ == "__main__":
    unittest.main()
