from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger, send_message

from action.fight import fightUtils
from action.fight import fightProcessor
from action.fight.fightUtils import timing_decorator

import time
import cv2
import numpy as np

boss_x, boss_y = 360, 800


@AgentServer.custom_action("Card1201")
class Card1201(CustomAction):
    def __init__(self):
        super().__init__()
        self.isHaveSealBook = False
        self.isTitle_L1 = False
        self.isTitle_L36 = False
        self.isTitle_L63 = False
        self.isAutoPickup = False
        self.layers = 1
        self.card_meditation_count = 0

    def initialize(self, context: Context):
        self.__init__()
        logger.info("Card1201初始化完成")
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        context.run_task("Bag_Open")
        has_seal_book = fightUtils.checkEquipment("宝物", 7, "封印之书", context)
        if not has_seal_book:
            found_book = fightUtils.findEquipment(7, "封印之书", False, context)
            self.isHaveSealBook = found_book
        else:
            self.isHaveSealBook = True
        context.run_task("Fight_ReturnMainWindow")

    def Check_CurrentLayers(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        tempLayers = -1
        while tempLayers <= 0 and (
                RunResult := context.run_recognition(
                    "Fight_CheckLayer",
                    context.tasker.controller.post_screencap().wait().get(),
                )
        ):
            if RunResult.hit == False:
                continue
            tempLayers = fightUtils.extract_num_layer(RunResult.best_result.text)
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return False
        self.layers = tempLayers
        return True

    @timing_decorator
    def Check_DefaultEquipment(self, context: Context):
        if self.layers == 1 or self.layers == 26 or self.layers == 63:
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:
                if not fightUtils.checkEquipment("宝物", 7, "封印之书", context):
                    fightUtils.findEquipment(7, "封印之书", True, context)
                time.sleep(1)
                context.run_task("Fight_ReturnMainWindow")
                logger.info(f"current layers {self.layers},装备检查完成")
            else:
                logger.info("背包打开失败")
                return False
        elif self.layers == 39:
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:
                if not fightUtils.checkEquipment("腰带", 1, "贵族丝带", context):
                    fightUtils.findEquipment(1, "贵族丝带", True, context)
                if not fightUtils.checkEquipment("戒指", 2, "礼仪戒指", context):
                    fightUtils.findEquipment(2, "礼仪戒指", True, context)
                if not fightUtils.checkEquipment("披风", 3, "天鹅绒斗篷", context):
                    fightUtils.findEquipment(3, "天鹅绒斗篷", True, context)
                if not fightUtils.checkEquipment("宝物", 7, "冒险家竖琴", context):
                    fightUtils.findEquipment(7, "冒险家竖琴", True, context)
                logger.info(f"current layers {self.layers},装备检查完成")
            else:
                logger.info("背包打开失败")
                return False
        elif self.layers % 10 == 9:
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:
                has_truth_set = (
                    fightUtils.checkEquipment("宝物", 3, "真理挂坠", context) and
                    fightUtils.checkEquipment("宝物", 3, "真理之靴", context) and
                    fightUtils.checkEquipment("宝物", 3, "真理披风", context) and
                    fightUtils.checkEquipment("宝物", 3, "真理之戒", context)
                )
                has_demon_set = (
                    fightUtils.checkEquipment("宝物", 4, "恶魔挂坠", context) and
                    fightUtils.checkEquipment("宝物", 4, "恶魔之戒", context) and
                    fightUtils.checkEquipment("宝物", 4, "恶魔骨靴", context) and
                    fightUtils.checkEquipment("宝物", 4, "恶魔披肩", context)
                )
                has_mage_set = (
                    fightUtils.checkEquipment("宝物", 5, "魔导士挂坠", context) and
                    fightUtils.checkEquipment("宝物", 5, "魔导士之靴", context) and
                    fightUtils.checkEquipment("宝物", 5, "魔导士指轮", context) and
                    fightUtils.checkEquipment("宝物", 5, "魔导士斗篷", context)
                )
                if has_truth_set:
                    logger.info(f"current layers {self.layers},切换到真理套装")
                elif has_demon_set:
                    logger.info(f"current layers {self.layers},切换到恶魔套装")
                elif has_mage_set:
                    logger.info(f"current layers {self.layers},切换到魔导士套装")
                else:
                    logger.info(f"current layers {self.layers},没有找到套装,继续使用当前装备")
            else:
                logger.info("背包打开失败")
                return False
        elif self.layers == 1201:
            context.run_task("Fight_ReturnMainWindow")
            OpenDetail = context.run_task("Bag_Open")
            if not fightUtils.checkEquipment("头盔", 7, "斯巴达的头盔", context):
                fightUtils.findEquipment(7, "斯巴达的头盔", True, context)
            logger.info(f"current layers {self.layers},装备检查完成")
            context.run_task("Fight_ReturnMainWindow")
        return True

    @timing_decorator
    def Check_DefaultTitle(self, context: Context):
        if (self.layers == 1 or self.layers == 2) and self.isTitle_L1 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 3, context)
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
        elif (self.layers == 39) and self.isTitle_L36 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面法师", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L36 = True
        elif (self.layers == 63 or self.layers == 64) and self.isTitle_L63 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "锻造师", 1, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 1, context)
            fightUtils.title_learn("冒险", 5, "大附魔师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            self.isTitle_L63 = True
            context.run_task("Fight_ReturnMainWindow")
        elif (self.layers == 69) and self.isTitle_L63 == False:
            fightUtils.title_learn("巨龙", 1, "亚龙血统", 2, context)
            fightUtils.title_learn("巨龙", 2, "初级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 3, "中级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 4, "高级龙族血统", 1, context)
            self.isTitle_L63 = True
            context.run_task("Fight_ReturnMainWindow")
        return True

    def cast_card_skill(self, card_name: str, context: Context) -> bool:
        """施放卡牌技能(冥想、连斩等)"""
        logger.info(f"准备施放卡牌技能: {card_name}")
        context.run_task("Fight_ReturnMainWindow")
        time.sleep(0.5)
        context.tasker.controller.post_click(600, 1150).wait()
        time.sleep(1)
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "CardSkill_Click",
            image,
            pipeline_override={
                "CardSkill_Click": {
                    "recognition": "OCR",
                    "expected": card_name,
                    "roi": [50, 300, 500, 600],
                }
            }
        ).hit:
            context.run_task(
                "CardSkill_Click",
                pipeline_override={
                    "CardSkill_Click": {
                        "expected": card_name,
                        "next": "CardSkill_Cast",
                    }
                }
            )
            logger.info(f"施放卡牌技能: {card_name}")
            return True
        else:
            logger.info(f"没有找到卡牌: {card_name}")
            context.run_task("Fight_ReturnMainWindow")
            return False

    def enter_dragon_heart_room(self, context: Context) -> bool:
        """进入龙之心房间"""
        logger.info("尝试进入龙之心房间")
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "DragonHeart_Entrance",
            image,
            pipeline_override={
                "DragonHeart_Entrance": {
                    "recognition": "TemplateMatch",
                    "template": ["fight/dragon_heart.png", "fight/dragon_heart_entrance.png"],
                    "roi": [0, 0, 720, 1280],
                }
            }
        ).hit:
            logger.info("识别到龙之心入口,点击进入")
            context.run_task("DragonHeart_Entrance")
            time.sleep(2)
            return True
        else:
            logger.info("未找到龙之心入口,尝试直接点击龙之心位置")
            context.tasker.controller.post_click(360, 600).wait()
            time.sleep(2)
            return True

    def attack_dragon_heart(self, context: Context) -> bool:
        """攻击龙之心"""
        logger.info("攻击龙之心")
        context.tasker.controller.post_click(360, 600).wait()
        time.sleep(0.5)
        return True

    def handle_abattoir_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if (self.layers % 10 == 5 or self.layers % 10 == 4) and context.run_recognition(
            "JJC_Find_Abattoir", image,
        ).hit:
            logger.info(f"进入角斗场战斗！！！")
            context.run_task("JJC_Find_Abattoir")
            if self.layers <= 35:
                fightUtils.cast_magic("光", "祝福术", context)
                for _ in range(3):
                    fightUtils.cast_magic_special("天眼", context)
            elif self.layers <= 45:
                if not fightUtils.cast_magic("火", "失明术", context, (boss_x, boss_y)):
                    fightUtils.cast_magic("暗", "诅咒术", context, (boss_x, boss_y))
                for _ in range(3):
                    if not fightUtils.cast_magic("光", "祝福术", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)
            elif self.layers <= 55:
                if not fightUtils.cast_magic("火", "失明术", context, (boss_x, boss_y)):
                    fightUtils.cast_magic("暗", "诅咒术", context, (boss_x, boss_y))
                for _ in range(3):
                    if not fightUtils.cast_magic("水", "寒冰护盾", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)
            elif self.layers <= 75:
                for _ in range(2):
                    context.run_task("Bag_Open")
                    fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
                for _ in range(3):
                    if not fightUtils.cast_magic("水", "寒冰护盾", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)
            else:
                for _ in range(2):
                    context.run_task("Bag_Open")
                    fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
            if context.run_recognition(
                "Fight_Victory", context.tasker.controller.post_screencap().wait().get()
            ).hit:
                context.run_task("Fight_Victory")
            time.sleep(2)
            context.run_task("JJC_Abattoir_Chest")
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_small_monster_event(self, context: Context):
        """处理小怪层战斗: 每层冥想 + 四象封印"""
        logger.info(f"第{self.layers}层小怪层战斗")
        logger.info("施放冥想(卡牌)")
        self.cast_card_skill("冥想", context)
        time.sleep(0.5)
        logger.info("施放四象封印(特殊魔法)")
        fightUtils.cast_magic_special("四象封印", context)
        time.sleep(0.5)
        context.run_task("JJC_Fight_ClearCurrentLayer")
        return True

    def handle_boss_event(self, context: Context):
        """处理Boss层战斗: 连斩×2 → 冥想 → A一下Boss → 进龙心 → 梦魇技能 → 瓦解 → 四象封印 → A龙心 → 斩杀 → 出洞 → A本体"""
        logger.info(f"第{self.layers}层Boss层战斗")
        time.sleep(3)
        logger.info("施放连斩×2")
        self.cast_card_skill("连斩", context)
        time.sleep(0.3)
        self.cast_card_skill("连斩", context)
        time.sleep(0.3)
        logger.info("施放冥想")
        self.cast_card_skill("冥想", context)
        time.sleep(0.5)
        logger.info("攻击Boss本体")
        context.tasker.controller.post_click(boss_x, boss_y).wait()
        time.sleep(0.5)
        logger.info("尝试进入龙之心房间")
        self.enter_dragon_heart_room(context)
        logger.info("施放梦魇技能(抽取心脏灵魂)")
        fightUtils.cast_magic_special("抽取心脏灵魂", context)
        time.sleep(0.5)
        logger.info("施放瓦解射线")
        fightUtils.cast_magic("气", "瓦解射线", context)
        time.sleep(0.5)
        logger.info("施放四象封印")
        fightUtils.cast_magic_special("四象封印", context)
        time.sleep(0.5)
        logger.info("攻击龙之心")
        self.attack_dragon_heart(context)
        time.sleep(0.5)
        logger.info("施放斩杀")
        fightUtils.cast_magic_special("斩杀", context)
        time.sleep(1)
        logger.info("离开龙之心房间")
        context.run_task("Fight_ReturnMainWindow")
        time.sleep(1)
        logger.info("再次攻击Boss本体")
        context.tasker.controller.post_click(boss_x, boss_y).wait()
        time.sleep(1)
        logger.info("Boss战结束,开始捡东西")
        time.sleep(3)
        context.run_task("Fight_OpenedDoor")
        return True

    @timing_decorator
    def handle_preLayers_event(self, context: Context):
        self.Check_DefaultEquipment(context)
        self.Check_DefaultTitle(context)
        self.handle_abattoir_event(context)
        return True

    @timing_decorator
    def handle_perfect_event(self, context: Context):
        if (not self.isHaveSealBook and 
            context.run_recognition("Fight_Perfect", 
            context.tasker.controller.post_screencap().wait().get()).hit):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition("Fight_Perfect", 
            context.tasker.controller.post_screencap().wait().get()).hit:
                pass

    @timing_decorator
    def handle_sparta_event(self, context: Context):
        if not self.isHaveSealBook:
            for _ in range(3):
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("JJC_Find_Body", img).hit:
                    context.run_task("JJC_Find_Body")
                    self.isHaveSealBook = True
                    logger.info("已有封印之书，或找到封印之书了！！")
                    break

    @timing_decorator
    def handle_skillShop_event(self, context: Context, image):
        if self.layers >= 40:
            return True
        if context.run_recognition("Fight_SkillShop", image).hit:
            fightUtils.handle_skillShop_event(context,
                target_skill=["石肤术", "地震术", "静电场", "毁灭之刃", 
                              "瓦解射线", "失明术", "治疗术", "寒冰护盾", "死亡波纹"])

    @timing_decorator
    def handle_stone_event(self, context: Context, image):
        if self.layers <= 29 and context.run_recognition("JJC_StoneChest", image).hit:
            context.run_task("JJC_StoneChest")

    def handle_auto_pickup_event(self, context: Context):
        logger.info("开启自动拾取, 等待动画结束")
        context.run_task("Fight_PickUpAll_Emptyfloor")
        self.isAutoPickup = True

    def handle_postLayers_event(self, context: Context):
        self.handle_perfect_event(context)
        image = context.tasker.controller.post_screencap().wait().get()
        self.handle_stone_event(context, image)
        self.handle_skillShop_event(context, image)
        self.handle_sparta_event(context)
        fightUtils.handle_dragon_event("工资", context)
        if self.isAutoPickup:
            logger.info("触发下楼事件")
            fightUtils.handle_downstair_event(context)
        else:
            logger.info("触发开启自动拾取事件")
            self.handle_auto_pickup_event(context)

    @timing_decorator
    def handle_clearCurLayer_event(self, context: Context):
        if self.layers >= 30 and self.layers % 10 == 0:
            time.sleep(6)
            self.handle_boss_event(context)
            fightUtils.handle_dragon_event("工资", context)
            return False
        else:
            if self.layers >= 1:
                self.handle_small_monster_event(context)
            else:
                context.run_task("JJC_Fight_ClearCurrentLayer")
        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("JJC_Inter_Confirm", image).hit:
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("JJC_Inter_Confirm")
            return False
        if context.run_recognition("BackText", image).hit:
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False
        return True

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        self.initialize(context)
        while self.layers < 101:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)
            if not self.Check_CurrentLayers(context):
                return CustomAction.RunResult(success=False)
            logger.info(f"Start Explore {self.layers} layer.")
            self.handle_preLayers_event(context)
            if self.layers == 95:
                logger.info(f"current layers {self.layers}, 开始退出agent")
                break
            if not self.handle_clearCurLayer_event(context):
                continue
            if not self.handle_interrupt_event(context):
                continue
            self.handle_postLayers_event(context)
        logger.info(f"卡牌1201探索结束，当前到达{self.layers}层")
        context.run_task("Fight_LeaveMaze")
        stats = fightUtils.get_time_statistics()
        for func_name, data in stats.items():
            logger.info(f"{func_name} 执行 {data['count']} 次，总耗时: {data['total_time']:.4f}秒")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_Fight_ClearCurrentLayer")
class JJC_Fight_ClearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        self.fightProcessor.clearCurrentLayer(context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_Select")
class Fight_Select(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        logger.info("选择药剂中")
        context.run_task("Select_Drug")
        logger.info("选择神器中")
        context.run_task("Select_Artifact")
        logger.info("选择链接角色1")
        context.run_task("Select_Gumball_1", pipeline_override={
            "select_InputBox_Click": {"next": "select_InputBox_Text1"}})
        logger.info("选择链接角色2")
        context.run_task("Select_Gumball_2", pipeline_override={
            "select_InputBox_Click": {"next": "select_InputBox_Text2"}})
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_PreWar")
class Fight_PreWar(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        context.run_task("Select_MainCharacter")
        logger.info("出来吧，冈布奥！！")
        start_x, start_y = (argv.box[0] + argv.box[2] // 2, argv.box[1] + argv.box[3] // 2)
        context.tasker.controller.post_click(start_x, start_y).wait()
        logger.info("准备进入迷宫！！！")
        time.sleep(1)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_CalEarning")
class JJC_CalEarning(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        time.sleep(5)
        for _ in range(10):
            context.tasker.controller.post_click(360, 640).wait()
            time.sleep(0.5)
            context.tasker.controller.post_click(360, 640).wait()
            if context.run_recognition("ConfirmButton", 
            context.tasker.controller.post_screencap().wait().get()).hit:
                context.run_task("ConfirmButton")
                break
        image = context.tasker.controller.post_screencap().wait().get()
        if recoDetail := context.run_recognition("CallEarning_Reco", image, pipeline_override={
            "CallEarning_Reco": {"recognition": "OCR", "expected": ["获得"], "roi": [78, 940, 471, 116]}}):
            if recoDetail.hit:
                EarningDetail = fightUtils.pair_by_distance(recoDetail.all_results, 400)
                if EarningDetail.get("获得金币"):
                    temp = int(EarningDetail["获得金币"]) // 10000
                    send_message(f"MaaGB", f"获得金币: {temp}w")
                logger.info(EarningDetail)
        context.run_task("ReturnBigMap")
        time.sleep(3)
        context.run_task("Start_Up")
        return CustomAction.RunResult(success=True)
