import math
from typing import Final

import cv2

from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger


STATUS_CIRCLE_RIGHT_NODE: Final = "Sleeptown_StatusCircleRight"
ENERGY_THRESHOLD_PERCENT: Final = 50.0
ENERGY_RING_RADII: Final = range(19, 25)


def calculate_red_ring_percent(image, center_x: int, center_y: int) -> float:
    """Calculate energy from the longest continuous red arc around an icon."""

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red_angles = []

    for degree in range(360):
        radian = math.radians(degree - 90)
        red_samples = 0

        for radius in ENERGY_RING_RADII:
            x = round(center_x + radius * math.cos(radian))
            y = round(center_y + radius * math.sin(radian))
            hue, saturation, value = (int(channel) for channel in hsv[y, x])
            blue, green, red = (int(channel) for channel in image[y, x])
            is_red = (
                (hue <= 12 or hue >= 168)
                and saturation >= 90
                and value >= 80
                and red >= green * 1.15
            )
            red_samples += int(is_red)

        red_angles.append(red_samples >= len(ENERGY_RING_RADII) // 2)

    longest_run = 0
    current_run = 0
    for is_red in red_angles + red_angles:
        current_run = current_run + 1 if is_red else 0
        longest_run = max(longest_run, current_run)

    return min(longest_run, 360) / 3.6


class SleeptownRightEnergyCheck(CustomAction):
    """Click the right status icon only when its red energy ring is at least 50%."""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        image = context.tasker.controller.post_screencap().wait().get()
        icon = context.run_recognition(STATUS_CIRCLE_RIGHT_NODE, image)
        if not icon.hit:
            logger.error("沉眠小镇能量检查失败：未识别到右侧状态图标")
            return CustomAction.RunResult(success=False)

        box = icon.box
        center_x = box.x + box.w // 2
        center_y = box.y + box.h // 2
        energy_percent = calculate_red_ring_percent(image, center_x, center_y)
        logger.info(
            f"右侧状态图标：center=({center_x},{center_y})，"
            f"red_ring={energy_percent:.2f}%"
        )

        if energy_percent < ENERGY_THRESHOLD_PERCENT:
            print(
                f"ENERGY_RESULT center=({center_x},{center_y}) "
                f"percent={energy_percent:.2f} decision=SKIP"
            )
            logger.info(
                f"能量低于 {ENERGY_THRESHOLD_PERCENT:.0f}%，不点击右侧状态图标"
            )
            return CustomAction.RunResult(success=True)

        print(
            f"ENERGY_RESULT center=({center_x},{center_y}) "
            f"percent={energy_percent:.2f} decision=CLICK"
        )
        logger.info(
            f"能量达到 {ENERGY_THRESHOLD_PERCENT:.0f}%，"
            f"通过 MAA Controller 点击 ({center_x},{center_y})"
        )
        context.tasker.controller.post_click(center_x, center_y).wait()
        return CustomAction.RunResult(success=True)
