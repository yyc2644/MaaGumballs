"""Run the Sleeptown suggestion-node validation with MaaFramework.

ADB is used by MaaFramework as its device controller. External ADB commands are
not used for clicks; they may be used separately to record the screen.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = PROJECT_ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from maa.controller import AdbController
from maa.define import LoggingLevelEnum
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

from action.sleeptown.sleeptown_suggestion import (
    SleeptownSuggestionPathValidation,
)


ACTION_NAME = "Sleeptown_Suggestion_Path_Validation"
ENTRY_NODE = "Sleeptown_Suggestion_Path_Validation"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adb",
        default=r"D:\MuMuPlayer\nx_main\adb.exe",
        help="ADB executable used by MaaFramework",
    )
    parser.add_argument("--address", default="127.0.0.1:16384")
    return parser.parse_args()


def require_job(job, operation: str):
    result = job.wait()
    if not result.status.succeeded:
        raise RuntimeError(f"{operation} failed: {result.status}")
    return result


def main() -> int:
    args = parse_args()
    Toolkit.init_option(str(PROJECT_ROOT))
    Tasker.set_stdout_level(LoggingLevelEnum.Info)
    Tasker.set_log_dir(PROJECT_ROOT / "debug" / "suggestion-validation")

    resource = Resource()
    require_job(
        resource.post_bundle(PROJECT_ROOT / "assets" / "resource" / "base"),
        "load Maa resource",
    )
    action = SleeptownSuggestionPathValidation()
    if not resource.register_custom_action(ACTION_NAME, action):
        raise RuntimeError(f"failed to register custom action: {ACTION_NAME}")

    controller = AdbController(args.adb, args.address)
    require_job(controller.post_connection(), "connect Maa ADB controller")
    controller.set_screenshot_target_short_side(720)

    tasker = Tasker()
    if not tasker.bind(resource, controller):
        raise RuntimeError("failed to bind Maa resource and controller")

    reconnect = tasker.post_task("Sleeptown_Suggestion_Reconnect").wait()
    if reconnect.status.succeeded:
        print("Maa dismissed the reconnect notice before validation")

    task = require_job(tasker.post_task(ENTRY_NODE), "run suggestion validation")
    detail = task.get()
    if detail is None or not detail.status.succeeded:
        raise RuntimeError(f"suggestion validation task failed: {detail}")

    print("Suggestion validation succeeded: B5 -> B4 -> B2 -> B1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
