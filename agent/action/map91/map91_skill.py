import time

from maa.context import Context

from action.fight import fightUtils
from utils import logger


DOUQI_BUTTON_CENTER = (360, 792)


class Map91FighterSkillManager:
    """91-1201 人物技能处理。"""

    def __init__(self, map91=None) -> None:
        self.map91 = map91

    def cast_douqi_burst(self, context: Context) -> bool:
        context.run_task("Fight_ReturnMainWindow")
        image = context.tasker.controller.post_screencap().wait().get()
        reco = context.run_recognition("RoleSkill_Fighter", image)
        if not reco or not reco.hit:
            logger.warning("91-1201 未识别到格斗家技能入口，跳过本轮小怪清理")
            return False

        box = reco.best_result.box
        context.tasker.controller.post_click(
            box[0] + box[2] // 2,
            box[1] + box[3] // 2,
        ).wait()
        time.sleep(0.4)

        image = context.tasker.controller.post_screencap().wait().get()
        candidates = fightUtils.ocr_text_candidates(
            context,
            ["斗气"],
            roi=[160, 500, 400, 360],
            image=image,
        )
        recognized = []
        target = None
        for result in candidates:
            text = fightUtils.normalize_ocr_text(getattr(result, "text", ""))
            recognized.append(f"{text}:{getattr(result, 'box', None)}")
            if "斗气" in text:
                target = result
                break
        if recognized:
            logger.info(f"91-1201 格斗家技能 OCR候选: {' | '.join(recognized)}")

        if target is None:
            logger.warning("91-1201 已打开格斗家技能，但未找到斗气，改用按钮中心补点")
        else:
            logger.info(
                f"91-1201 已识别到斗气，固定点击按钮中心 {DOUQI_BUTTON_CENTER}"
            )

        click_x, click_y = DOUQI_BUTTON_CENTER
        context.tasker.controller.post_click(click_x, click_y).wait()
        time.sleep(1.5)
        context.tasker.controller.post_click(click_x, click_y).wait()
        time.sleep(0.5)
        context.run_task("Fight_ReturnMainWindow")
        logger.info("91-1201 格斗家技能：已释放斗气")
        return True
