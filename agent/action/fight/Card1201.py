from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from agent.utils import logger, send_message

from agent.action.fight import fightUtils
from agent.action.fight import fightProcessor
from agent.action.fight.fightUtils import timing_decorator

import time

boss_x, boss_y = 360, 800


@AgentServer.custom_action("Card1201")
class Card1201(CustomAction):
    def __init__(self):
        super().__init__()
        self.isHaveSpartanHat = False
        self.isTitle_L1 = False
        self.isTitle_L36 = False
        self.isTitle_L63 = False
        self.isAutoPickup = False
        self.layers = 1

    def initialize(self, context: Context):
        self.__init__()
        logger.info("Card1201初始化完成")
        # 检查当前层数
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )

        # 进入地图初始化
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        context.run_task("Bag_Open")
        # 检查是否已装备封印之书
        has_helmet = fightUtils.checkEquipment("宝物", 7, "封印之书", context)
        if not has_helmet:
            # 若未装备，则尝试寻找封印之书
            found_helmet = fightUtils.findEquipment(7, "封印之书", False, context)
            self.isHaveSpartanHat = found_helmet
        else:
            self.isHaveSpartanHat = True

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
        """
        检查默认装备
        1. 初始装备封印之书,第一次39学技能的时候换贵族+竖琴,后续一直传魔法套混瓦解
        2 todo 7里面需要增加一个封印之书 \MaaGumballs\assets\resource\base\image\equipments\7level
        """
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
            # 是否有套装,先检查背包是否有套装
            OpenDetail = context.run_task("Bag_Open")
            # todo: 没写完
            if OpenDetail.nodes:
                if (fightUtils.checkEquipment("腰带", 1, "贵族丝带", context) and
                        fightUtils.checkEquipment("腰带", 1, "贵族丝带", context) and
                        fightUtils.checkEquipment("腰带", 1, "贵族丝带", context) and
                        fightUtils.checkEquipment("腰带", 1, "贵族丝带", context)):
                    logger.info(f"current layers {self.layers},有3*魔法套")

                    fightUtils.findEquipment(3, "真理挂坠", True, context)
                    fightUtils.findEquipment(3, "真理之靴", True, context)
                    fightUtils.findEquipment(3, "真理披风", True, context)
                    fightUtils.findEquipment(3, "真理之戒", True, context)
                elif (
                        fightUtils.findEquipment(4, "恶魔挂坠", True, context) and
                        fightUtils.findEquipment(4, "恶魔之戒", True, context) and
                        fightUtils.findEquipment(4, "恶魔骨靴", True, context) and
                        fightUtils.findEquipment(4, "恶魔披肩", True, context)):
                    logger.info(f"current layers {self.layers},有4*魔法套")
                elif (
                        fightUtils.findEquipment(5, "魔导士挂坠", True, context) and
                        fightUtils.findEquipment(5, "魔导士之靴", True, context) and
                        fightUtils.findEquipment(5, "魔导士指轮", True, context) and
                        fightUtils.findEquipment(5, "魔导士斗篷", True, context)):
                    logger.info(f"current layers {self.layers},有5*魔法套")
                else:
                    logger.info(f"形不成形，意不在意，再去练一练吧")

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
        """
        检查默认称号
        1. 检查1、36、64和89层的称号
        """
        if (self.layers == 1 or self.layers == 2) and self.isTitle_L1 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 3, context)
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
        elif (self.layers == 39) and self.isTitle_L36 == False:
            # 先大地,保证回去刷冥想和连斩,39第一次大地,防止打不过40的boss
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面法师", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            # 战士系点不点都无所谓,输出全靠四象
            # fightUtils.title_learn("战斗", 1, "见习战士", 1, context)
            # fightUtils.title_learn("战斗", 2, "战士", 3, context)
            # fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            # fightUtils.title_learn("战斗", 4, "炎龙武士", 3, context)
            # fightUtils.title_learn("战斗", 5, "毁灭公爵", 1, context)
            # fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
            # fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)

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
            # 龙系称号,69之前没龙系可以跳楼了
            fightUtils.title_learn("巨龙", 1, "亚龙血统", 2, context)
            fightUtils.title_learn("巨龙", 2, "初级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 3, "中级龙族血统", 1, context)
            fightUtils.title_learn("巨龙", 4, "高级龙族血统", 1, context)

            self.isTitle_L63 = True
            context.run_task("Fight_ReturnMainWindow")

        return True

    # @timing_decorator
    # def Check_DefaultStatus(self, context: Context):

    #   有浴血不需要保命,先注释掉
    #     # 检查冈布奥状态
    #     tempNum = self.layers % 10
    #     if (
    #         (self.layers >= 55 and (tempNum == 1 or tempNum == 5 or tempNum == 9))
    #         or (self.layers >= 90 and tempNum == 4)
    #         or (self.layers == 39)
    #     ):
    #         StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
    #         CurrentHP = float(StatusDetail["当前生命值"])
    #         MaxHp = float(StatusDetail["最大生命值"])
    #         HPStatus = CurrentHP / MaxHp
    #         logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")
    #         if HPStatus < 0.8:
    #             while HPStatus < 0.8:
    #                 if not fightUtils.cast_magic("光", "神恩术", context):
    #                     if not fightUtils.cast_magic("水", "治疗术", context):
    #                         if not fightUtils.cast_magic("水", "治愈术", context):
    #                             logger.info("没有任何治疗方法了= =")
    #                             break
    #                 context.run_task("Fight_ReturnMainWindow")
    #                 StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
    #                 CurrentHP = float(StatusDetail["当前生命值"])
    #                 MaxHp = float(StatusDetail["最大生命值"])
    #                 HPStatus = CurrentHP / MaxHp
    #                 logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")
    #         else:
    #             logger.info("当前生命值大于80%，不使用治疗")

    #     context.run_task("Fight_ReturnMainWindow")
    #     if tempNum == 9 and self.layers >= 61 and self.layers <= 90:
    #         fightUtils.OpenNatureSwitch(False, context)
    #         logger.info("开启自然之力")
    #     elif tempNum == 1 and self.layers >= 61 and self.layers <= 90:
    #         fightUtils.OpenNatureSwitch(True, context)
    #         logger.info("开启自然守护")

    #     # 保命
    #     if self.layers == 89 and not fightUtils.checkBuffStatus("神圣重生", context):
    #         fightUtils.cast_magic("光", "神圣重生", context)

    #     return True

    def handle_boss_80_event(self, context: Context):
        fightUtils.cast_magic("火", "失明术", context)
        fightUtils.cast_magic("气", "静电场", context)
        if not fightUtils.cast_magic("水", "冰锥术", context):
            if not fightUtils.cast_magic("暗", "变形术", context):
                fightUtils.cast_magic("土", "石肤术", context)
        fightUtils.cast_magic("水", "寒冰护盾", context)
        fightUtils.cast_magic("水", "寒冰护盾", context)
        fightUtils.cast_magic("土", "石肤术", context)
        fightUtils.cast_magic("光", "神恩术", context)
        for _ in range(3):
            context.tasker.controller.post_click(boss_x, boss_y).wait()

    def handle_boss_80_90_event(self, context: Context):
        fightUtils.OpenNatureSwitch(True, context)
        logger.info("没有时停，开启自然守护流打法")
        fightUtils.cast_magic("火", "失明术", context)
        fightUtils.PushOne_defense(context)
        fightUtils.PushOne_defense(context)

        # 循环——直到boss死亡：使用动作队列逐个执行并检查boss状态
        actions = [
            lambda: fightUtils.cast_magic("水", "冰锥术", context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.cast_magic("土", "石肤术", context),
            lambda: fightUtils.cast_magic("火", "失明术", context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.PushOne_defense(context),
        ]

        index = 0
        for _ in range(10):
            # 执行当前动作
            actions[index]()

            # 检查boss是否存在
            if context.run_recognition(
                    "Fight_CheckBossStatus",
                    context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                logger.info(f"当前层数 {self.layers} 已经击杀boss")
                fightUtils.OpenNatureSwitch(False, context)
                return True

            # 移动到下一个动作，循环执行
            index = (index + 1) % len(actions)

        logger.warning("十多个回合还没有拿下，是不是狗子挂了")
        return False

    def handle_boss_100_event(self, context: Context):
        fightUtils.cast_magic("气", "静电场", context)
        fightUtils.cast_magic("火", "毁灭之刃", context)
        fightUtils.cast_magic("气", "瓦解射线", context)
        for _ in range(6):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
            time.sleep(0.3)

    def handle_boss_100Dragon_event(self, context: Context):
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("特殊", "龙威", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()

    def handle_boss_event(self, context: Context):
        # 30-60,垃圾牌+流星雨
        if self.layers <= 40:
            fightUtils.cast_magic("火", "流星雨", context)
            fightUtils.cast_magic("火", "流星雨", context)
            fightUtils.cast_magic("土", "石肤术", context)
        # 60以上,连斩+梦魇+瓦解+四象
        else:
            fightUtils.cast_magic("卡牌", "冥想", context)
            fightUtils.cast_magic("卡牌", "连斩", context)
            fightUtils.cast_magic("卡牌", "连斩", context)

            # todo进入龙之心
            fightUtils.cast_magic("特殊", "梦魇", context)
            fightUtils.cast_magic("气", "瓦解射线", context)
            fightUtils.cast_magic("特殊", "四象", context)

            # todo 攻击一次心脏
            # todo 离开心脏

            # todo 攻击一次本体

        # 捡东西
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
        # 检测完美击败
        if (
                not self.isHaveSpartanHat
                and context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ).hit
        ):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                    "Fight_Perfect",
                    context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                pass

    @timing_decorator
    def handle_sparta_event(self, context: Context):
        # 寻找斯巴达头盔
        if not self.isHaveSpartanHat:
            # 检测三次斯巴达的头盔，检查到了就提前结束检查
            for _ in range(3):
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("JJC_Find_Body", img).hit:
                    context.run_task("JJC_Find_Body")
                    self.isHaveSpartanHat = True
                    logger.info("已有斯巴达头盔，或找到斯巴达头盔了！！")
                    break

    @timing_decorator
    def handle_skillShop_event(self, context: Context, image):
        # 打开技能商店
        if self.layers >= 40:
            return True
        # 打开技能商店
        if context.run_recognition("Fight_SkillShop", image).hit:
            fightUtils.handle_skillShop_event(
                context,
                target_skill=[
                    "石肤术",
                    "地震术",
                    "静电场",
                    "毁灭之刃",
                    "瓦解射线",
                    "失明术",
                    "治疗术",
                    "寒冰护盾",
                    "死亡波纹",
                ],
            )

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
        # boss层开始探索
        if self.layers >= 30 and self.layers % 10 == 0:
            # boss召唤动作
            time.sleep(6)
            self.handle_boss_event(context)
            fightUtils.handle_dragon_event("工资", context)

            return False
        # 小怪层探索
        else:
            if (
                    self.layers >= 85
                    and self.layers % 2 == 1
                    and fightUtils.cast_magic("土", "地震术", context)
            ):
                time.sleep(3)
            else:
                context.run_task("JJC_Fight_ClearCurrentLayer")

        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        # 检测卡剧情
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
                "JJC_Inter_Confirm",
                image,
        ).hit:
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("JJC_Inter_Confirm")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image).hit:
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # initialize
        self.initialize(context)

        while self.layers < 101:
            # 检查是否停止任务
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            # 检查当前层数, 确保不是0层
            if not self.Check_CurrentLayers(context):
                return CustomAction.RunResult(success=False)
            logger.info(f"Start Explore {self.layers} layer.")

            # 检测是否触发战前事件
            self.handle_preLayers_event(context)

            # 检查是否到达100层
            if self.layers == 95:
                logger.info(f"current layers {self.layers}, 开始退出agent")
                break

            # 探索当前层
            if not self.handle_clearCurLayer_event(context):
                continue

            # 检查是否触发中断事件
            if not self.handle_interrupt_event(context):
                continue

            # 检查是否触发战后事件
            self.handle_postLayers_event(context)

        logger.info(f"竞技场探索结束，当前到达{self.layers}层")
        context.run_task("Fight_LeaveMaze")

        # 获取并打印统计信息
        stats = fightUtils.get_time_statistics()
        for func_name, data in stats.items():
            logger.info(
                f"{func_name} 执行 {data['count']} 次，总耗时: {data['total_time']:.4f}秒"
            )
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_Fight_ClearCurrentLayer")
class JJC_Fight_ClearCurrentLayer(CustomAction):

    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()

    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.fightProcessor.clearCurrentLayer(context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_Select")
class Fight_Select(CustomAction):
    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        logger.info("选择药剂中")
        context.run_task("Select_Drug")

        logger.info("选择神器中")
        context.run_task("Select_Artifact")

        logger.info("选择链接角色1")
        context.run_task(
            "Select_Gumball_1",
            pipeline_override={
                "select_InputBox_Click": {"next": "select_InputBox_Text1"}
            },
        )

        logger.info("选择链接角色2")
        context.run_task(
            "Select_Gumball_2",
            pipeline_override={
                "select_InputBox_Click": {"next": "select_InputBox_Text2"}
            },
        )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_PreWar")
class Fight_PreWar(CustomAction):
    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 战前准备
        context.run_task("Select_MainCharacter")

        logger.info("出来吧，冈布奥！！")

        # 点击进入地图界面
        start_x, start_y = (
            argv.box[0] + argv.box[2] // 2,
            argv.box[1] + argv.box[3] // 2,
        )
        context.tasker.controller.post_click(start_x, start_y).wait()
        logger.info("准备进入迷宫！！！")
        time.sleep(1)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_TestAction")
class Fight_TestAction(CustomAction):
    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        context.run_task("Fight_ReturnMainWindow")
        fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
        fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
        fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
        fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
        fightUtils.title_learn("魔法", 5, "位面先知", 1, context)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_DragonWishTest")
class JJC_DragonWishTest(CustomAction):

    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        fightUtils.dragonwish("工资", context)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_CalEarning")
class JJC_CalEarning(CustomAction):
    # 执行函数
    def run(
            self,
            context: Context,
            argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        time.sleep(5)
        for _ in range(10):
            context.tasker.controller.post_click(360, 640).wait()
            time.sleep(0.5)
            context.tasker.controller.post_click(360, 640).wait()
            if context.run_recognition(
                    "ConfirmButton", context.tasker.controller.post_screencap().wait().get()
            ).hit:
                context.run_task("ConfirmButton")
                break
        image = context.tasker.controller.post_screencap().wait().get()
        if recoDetail := context.run_recognition(
                "CallEarning_Reco",
                image,
                pipeline_override={
                    "CallEarning_Reco": {
                        "recognition": "OCR",
                        "expected": ["获得"],
                        "roi": [78, 940, 471, 116],
                    },
                },
        ):
            if recoDetail.hit:
                EarningDetail = fightUtils.pair_by_distance(recoDetail.all_results, 400)
                if EarningDetail["获得金币"]:
                    temp = int(EarningDetail["获得金币"]) // 10000
                    send_message(
                        f"MaaGB",
                        f"获得金币: {temp}w",
                    )
                logger.info(EarningDetail)

        context.run_task("ReturnBigMap")
        time.sleep(3)
        context.run_task("Start_Up")

        return CustomAction.RunResult(success=True)
