import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agent"))
import action.fight.downstair as downstair
import action.fight.getKeyFromHole as get_key


class Job:
    def __init__(self, value=None): self.value = value
    def wait(self): return self
    def get(self): return self.value

class Controller:
    def post_screencap(self): return Job(object())
    def post_click(self, *args): return Job()

class Detail:
    def __init__(self, success=True): self.status = SimpleNamespace(succeeded=success)

class PullContext:
    def __init__(self, confirm=True):
        self.confirm, self.tasks = confirm, []
        self.tasker = SimpleNamespace(controller=Controller(), stopping=False)
    def run_task(self, name, **kwargs):
        self.tasks.append(name)
        return Detail(self.confirm if name == "ClickConfirmForKey" else True)

class PullStringFlowTests(unittest.TestCase):
    def test_aligned_piece_ocr_confirms_and_succeeds(self):
        solution = SimpleNamespace(source="key", source_point=(1, 2), target="shadow", target_point=(3, 4), mode="test", confidence=1.0)
        context = PullContext()
        with patch.object(get_key.HiddenCaveSolver, "analyze", return_value=solution), patch.object(get_key, "drag_key_to_target", return_value=(True, 4.0)), patch.object(get_key.time, "sleep", return_value=None):
            result = get_key.GetKeyFromHole_Test().run(context, None)
        self.assertTrue(result.success)
        self.assertEqual(context.tasks, ["FindKeyHole", "ClickConfirmForKey"])

    def test_failed_confirm_returns_failure(self):
        solution = SimpleNamespace(source="key", source_point=(1, 2), target="shadow", target_point=(3, 4), mode="test", confidence=1.0)
        context = PullContext(False)
        with patch.object(get_key.HiddenCaveSolver, "analyze", return_value=solution), patch.object(get_key, "drag_key_to_target", return_value=(True, 4.0)), patch.object(get_key.time, "sleep", return_value=None), patch.object(get_key, "TOTAL_ROUNDS", 1):
            self.assertFalse(get_key.GetKeyFromHole_Test().run(context, None).success)

class Recognition:
    def __init__(self, hit): self.hit = hit

class DownContext:
    def __init__(self, has_solver, solver_success=True):
        self.has_solver, self.solver_success = has_solver, solver_success
        self.tasks, self.open_checks = [], 0
        self.tasker = SimpleNamespace(controller=Controller(), stopping=False)
    def get_node_data(self, name): return {} if self.has_solver and name == "GetKeyFromHole" else None
    def run_task(self, name, **kwargs):
        self.tasks.append(name)
        return Detail(self.solver_success if name == "GetKeyFromHole" else True)
    def run_recognition(self, name, image=None):
        if name == "FindKeyHole": return Recognition(True)
        if name == "Fight_OpenedDoor":
            self.open_checks += 1
            return Recognition(self.open_checks > 1)
        return Recognition(False)

class DownstairIntegrationTests(unittest.TestCase):
    def run_case(self, has_solver, solver_success=True):
        context = DownContext(has_solver, solver_success)
        manager = downstair.FightDownstairManager(SimpleNamespace(layers=75))
        manager.processor.get_last_door_click_target = lambda layer: None
        changes = iter([(False, 75, 1), (True, 76, 1)])
        manager._wait_until_layer_changed = lambda context, layer: next(changes)
        alerts, messages = [], []
        with patch.object(downstair.fightUtils, "handle_currentlayer_event", return_value=75), patch.object(downstair.fightUtils, "timing_section", return_value=nullcontext()), patch.object(downstair.fightUtils, "send_alert", side_effect=lambda *x: alerts.append(x)), patch.object(downstair, "send_message", side_effect=lambda *x: messages.append(x)), patch.object(downstair.time, "sleep", return_value=None), patch.object(manager, "_save_status_before_keyhole_notice", return_value=False):
            self.assertTrue(manager.handle_downstair_event(context))
        return context.tasks, alerts, messages

    def test_solver_success_skips_notification(self):
        tasks, alerts, messages = self.run_case(True, True)
        self.assertIn("GetKeyFromHole", tasks)
        self.assertFalse(alerts or messages)

    def test_missing_solver_keeps_notification(self):
        tasks, alerts, messages = self.run_case(False)
        self.assertNotIn("GetKeyFromHole", tasks)
        self.assertTrue(alerts and messages)

    def test_failed_solver_keeps_notification(self):
        tasks, alerts, messages = self.run_case(True, False)
        self.assertIn("GetKeyFromHole", tasks)
        self.assertTrue(alerts and messages)

if __name__ == "__main__": unittest.main()
