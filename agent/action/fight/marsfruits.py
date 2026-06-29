'''
福神亚瑟王獬豸 刷果实
'''
from math import floor
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from agent.utils import logger

from agent.action.fight.fightUtils import timing_decorator
from agent.action.fight import fightUtils
from agent.action.fight import fightProcessor

import time
import json


boss_x, boss_y = 360, 800
boss_slave_1_x, boss_slave_1_y = 100, 660
boss_slave_2_x, boss_slave_2_y = 640, 660
special_layer_monster_1_x, special_layer_monster_1_y = 90, 650
special_layer_monster_2_x, special_layer_monster_2_y = 363, 650


@AgentServer.custom_action("Marsfruit")
class Marsfruit(CustomAction):
    def __init__(self):
        super().__init__()
        self.isTitle_L1 = False
        self.isTitle_L10 = False
        self.isTitle_L61 = False
        self.isTitle_L86 = False
        self.useEarthGate = 0
        self.isGetDragonTitle = False
        self.isGetTitanFoot = False
        self.isGetMagicAssist = False
        self.isUseMagicAssist = False
        self.is_android_skill_enabled = False
        self.isLeaveMaze = False
        self.isAutoPickup = False
        self.is_demontitle_enable = False
        self.isDeath = False
        self.useDemon = 0
        self.layers = 1

    def initialize(self, context: Context):
        self.__init__()
        logger.info("马尔斯101初始化完成")
        # 检查当前层数
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )

        # 进入地图初始化
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        # 初始化魔法助手状态
        if fightUtils.check_magic_special("魔法助手", context):
            self.isGetMagicAssist = True
            logger.info(f"已获得魔法助手")
            if self.layers > self.target_leave_layer_para - 19:
                self.isUseMagicAssist = True
                logger.info(f"已开启魔法助手")
        # 初始化泰坦之足状态
        if fightUtils.check_magic_special("泰坦之足", context):
            logger.info(f"已获得泰坦之足")
            self.isGetTitanFoot = True
        # 初始化恶魔系称号状态
        # 如果恶魔系称号期望开启，那么在初始化阶段启用手记获取称号
        # if self.astrological_title_para:
        #     context.run_task("Fight_ReturnMainWindow")
        #     OpenDetail = context.run_task("Bag_Open")
        #     if OpenDetail:
        #         time.sleep(1)
        #         fightUtils.findItem("阿瑞斯的手记", True, context, threshold=0.8)
        #     time.sleep(1)
        #
        #     if context.run_recognition(
        #         "Mars_GetDemonTitle_Confirm",
        #         context.tasker.controller.post_screencap().wait().get(),
        #     ):
        #         taskdetail = context.run_task("Mars_GetDemonTitle_Confirm")
        #     else:
        #         taskdetail = context.run_task("Mars_GetDemonTitle_Confirm_2")
        #     if taskdetail.nodes:
        #         logger.info("已获得恶魔系称号")
        #         self.is_demontitle_enable = True
        #     else:
        #         logger.info("获取恶魔系称号失败")

    def Check_CurrentLayers(self, context: Context):
        tempLayers = fightUtils.handle_currentlayer_event(context)
        self.layers = tempLayers
        return True

    def Check_GridAndMonster(
        self, context: Context, clear=True, checkGrid=True, checkMonster=True
    ):
        """
        检查当前层是否有地板或者怪物残留
        :param context: 上下文对象
        :param clear: 是否清除残留
        :param checkGrid: 是否检查地板
        :param checkMonster: 是否检查怪物
        :return: 是否存在地板或者怪物
        """
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 200}}
            },
        )
        processor = fightProcessor.FightProcessor()
        if processor.checkGirdAndMonster(
            context,
            context.tasker.controller.post_screencap().wait().get(),
            checkGrid=checkGrid,
            checkMonster=checkMonster,
        ):
            if clear:
                logger.info("有地板或者怪物残留，再次清层")
                context.run_task(
                    "Mars_Fight_ClearCurrentLayer",
                    pipeline_override={
                        "Mars_Fight_ClearCurrentLayer": {
                            "custom_action_param": {"layers": self.layers}
                        }
                    },
                )
            if checkMonster:
                logger.info("有怪物残留")
            if checkGrid:
                logger.info("有地板残留")
            return True
        logger.info("无地板或者怪物残留")
        # context.run_task("Screenshot")
        return False

    def Check_DefaultEquipment(self, context: Context):
        """
        检查默认装备
        1. 检查出图装备
        """
        if self.layers == 59:
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
                time.sleep(1)
                context.run_task("Fight_ReturnMainWindow")
                logger.info(f"current layers {self.layers},装备检查完成")
            else:
                logger.info("背包打开失败")
                context.run_task("Fight_ReturnMainWindow")
                return False
        return True

    @timing_decorator
    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号,除了大铸剑师，其他都只点一级，压血
        1. 检查1层的称号: 魔法学徒点满
        2. 检查28层称号: 点满符文师
        3. 检查61层的称号: 位面点满即可
        4. 检查86层的称号: 位面，大铸剑师，大剑师都点满
        """
        if (self.layers >= 1 and self.layers <= 3) and self.isTitle_L1 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
            return True
        elif (self.layers >= 10 and self.layers <= 13) and self.isTitle_L10 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "符文师", 4, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L10 = True
            return True
        elif (self.layers >= 61 and self.layers <= 63) and self.isTitle_L61 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L61 = True
            return True

        elif (self.layers >= 86 and self.layers <= 88) and self.isTitle_L86 == False:
            fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "大剑师", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            # fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
            # fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 2, context)
            if self.isTitle_L10 == False:
                fightUtils.title_learn("冒险", 3, "符文师", 3, context)
                self.isTitle_L10 = True
            # fightUtils.title_learn("冒险", 3, "符文师", 3, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
            fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            # fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            # 不需要额外三系和其他
            # if self.astrological_title_para and self.is_demontitle_enable:
            #     logger.info("点了恶魔")
            #     fightUtils.title_learn("恶魔", 1, "堕落者", 1, context)
            #     fightUtils.title_learn("恶魔", 2, "下位恶魔", 3, context)
            #     fightUtils.title_learn("恶魔", 3, "中位恶魔", 3, context)
            #     fightUtils.title_learn("恶魔", 4, "上位恶魔", 3, context)
            #     fightUtils.title_learn("恶魔", 5, "恶魔大领主", 1, context)
            #     fightUtils.title_learn_branch("恶魔", 5, "攻击强化", 3, context)
            #     fightUtils.title_learn_branch(
            #         "恶魔", 5, "攻击强化", 3, context, repeatable=True
            #     )
            #     fightUtils.title_learn_branch("恶魔", 5, "生命强化", 3, context)
            # else:
            #     logger.info("没点恶魔")
            # if fightUtils.title_check("巨龙", context):
            #     self.isGetDragonTitle = True
            #     fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
            #     fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)

            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L86 = True
            return True
        return False

    @timing_decorator
    def Check_DefaultStatus(self, context: Context):
        """检查冈布奥状态"""
        tempNum = self.layers % 10
        if (
            (11 <= self.layers <= 79) and (tempNum == 1 or tempNum == 5 or tempNum == 9)
        ) or self.layers >= 80:
            # 如果大地回来，低于60层就不检查状态
            if (self.layers <= 60) and self.useEarthGate > 0:
                return True
            StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
            CurrentHP = float(StatusDetail["当前生命值"])
            MaxHp = float(StatusDetail["最大生命值"])
            HPStatus = CurrentHP / MaxHp
            logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")

            if HPStatus < 0.8:
                if self.layers <= 60:
                    fightUtils.cast_magic_special("生命颂歌", context)
                if self.layers >= 110:
                    fightUtils.cast_magic("气", "静电场", context)
                cast_state = {"痊愈术": True, "神恩术": True, "治疗术": True}
                while HPStatus < 0.8:
                    if cast_state["痊愈术"]:
                        if not fightUtils.cast_magic("水", "痊愈术", context):
                            cast_state["痊愈术"] = False
                    elif cast_state["神恩术"]:
                        if not fightUtils.cast_magic("光", "神恩术", context):
                            cast_state["神恩术"] = False
                    elif not fightUtils.cast_magic("水", "治疗术", context):
                        logger.info("没有任何治疗方法了= =")
                        break
                    context.run_task("Fight_ReturnMainWindow")
                    StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
                    AfterHP = float(StatusDetail["当前生命值"])
                    MaxHp = float(StatusDetail["最大生命值"])
                    HPStatus = AfterHP / MaxHp
                    logger.info(f"current hp is {AfterHP}, HPStatus is {HPStatus}")
            else:
                logger.info("当前生命值大于80%，不使用治疗")

            # 保命
            if self.layers >= 51 and not fightUtils.checkBuffStatus(
                "神圣重生", context
            ):
                fightUtils.cast_magic("光", "神圣重生", context)
        return True

    def Get_CurrentHPStatus(self, context: Context):
        StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
        CurrentHP = float(StatusDetail["当前生命值"])
        MaxHp = float(StatusDetail["最大生命值"])
        HPStatus = CurrentHP / MaxHp
        return HPStatus


    def handle_EarthGate_event(self, context: Context):
        """
        大地成功返回True,否则返回False
        """
        if (
            ((self.layers > 60) and (self.layers % 10 == 9))
            # 在61~63层时释放大地，或者x9(>60)层时释放大地
            or (61 <= self.layers <= 63)
        ) and self.useEarthGate < self.target_earthgate_para:
            # 识别是否门关着
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("Fight_ClosedDoor", image):
                logger.info("当前层无法释放大地，跳过")
                return False
            context.run_task("Fight_ReturnMainWindow")
            if fightUtils.check_magic("土", "大地之门", context):
                fightUtils.cast_magic("气", "静电场", context)
                if self.isUseMagicAssist:
                    # 关闭魔法助手, 节省卷轴
                    fightUtils.cast_magic_special("魔法助手", context)
                    self.isUseMagicAssist = False
                if fightUtils.cast_magic("土", "大地之门", context):
                    templayer = self.layers
                    for _ in range(10):
                        logger.info(f"等待大地之门特效结束")
                        self.Check_CurrentLayers(context)
                        if self.layers != templayer and self.layers != -1:
                            logger.info(f"大地之门特效结束, 当前层数为{self.layers}")
                            self.useEarthGate += 1
                            return True
                        time.sleep(1)
        return False

    @timing_decorator
    def handle_preLayers_event(self, context: Context):
        self.handle_android_skill_event(context)
        self.handle_UseMagicAssist_event(context)
        # 添加开场检查血量，防止意外
        if (self.layers > self.target_leave_layer_para - 20) and self.layers % 10 != 0:
            self.Check_DefaultStatus(context)
            if not fightUtils.checkBuffStatus("寒冰护盾", context):
                if self.layers > self.target_leave_layer_para - 10:
                    fightUtils.cast_magic("气", "静电场", context)
                    fightUtils.cast_magic("水", "寒冰护盾", context)
                    # 这里检查是否有远程怪物存在
                    if self.Check_GridAndMonster(
                        context, clear=False, checkGrid=False, checkMonster=True
                    ):
                        logger.info("当前层有远程怪物, 寒冰护盾替换成极光屏障")
                        if not fightUtils.cast_magic("水", "极光屏障", context):
                            fightUtils.cast_magic("水", "寒冰护盾", context)
                else:
                    fightUtils.cast_magic("水", "寒冰护盾", context)
                    # 在100~110层时释放地震，减少技能消耗，提高清层效率
        if self.isUseMagicAssist and 100 < self.layers < 110:
            fightUtils.cast_magic("土", "地震术", context)
        # self.Check_DefaultEquipment(context)
        return True

    def handle_perfect_event(self, context: Context):
        # 检测完美击败
        if (self.layers % 2 == 1) and context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                "Fight_Perfect",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                pass

    @timing_decorator
    def handle_before_leave_maze_event(self, context: Context):
        '''
        正常情况下，福神可以直接1201出图，不需要更多的判断
        '''
        logger.info("触发Mars结算事件")
        context.run_task("Fight_ReturnMainWindow")
        # 先关闭魔法助手
        if self.isUseMagicAssist:
            fightUtils.cast_magic_special("魔法助手", context)
            self.isUseMagicAssist = False

        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        self.gotoSpecialLayer(context)
        fightUtils.openBagAndUseItem("电能试剂", True, context)

        self.leaveSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)
        self.gotoSpecialLayer(context)
        fightUtils.openBagAndUseItem("能量电池", True, context)

        self.leaveSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)
        fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
        if fightUtils.title_check("巨龙", context):
            fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
            fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
            if self.layers > 100:
                fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)

            if self.useEarthGate > 1:
                fightUtils.title_learn("巨龙", 5, "邪龙血统", 1, context)
                fightUtils.title_learn_branch("巨龙", 5, "攻击强化", 3, context)
                fightUtils.title_learn_branch(
                    "巨龙", 5, "攻击强化", 3, context, repeatable=True
                )
                fightUtils.title_learn_branch("巨龙", 5, "生命强化", 3, context)

        context.run_task("Fight_ReturnMainWindow")
        # 这里进夹层压血
        if self.target_earthgate_para >= 0:
            self.gotoSpecialLayer(context)
            fightUtils.cast_magic("土", "石肤术", context)
            if not fightUtils.cast_magic("暗", "死亡波纹", context):
                if not fightUtils.cast_magic("火", " 末日审判", context):
                    fightUtils.cast_magic("土", "地震术", context)

            for _ in range(20):
                if fightUtils.checkBuffStatus("神圣重生", context):
                    logger.info("发现神圣重生buff, 使用祝福术尝试复活")
                    fightUtils.cast_magic("光", "祝福术", context)
                else:
                    time.sleep(5)
                    break

            self.Control_tenpecentHP(context)
            # 增加截图调试
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
                },
            )
            context.run_task("Screenshot")
            self.leaveSpecialLayer(context)
            context.run_task("Fight_ReturnMainWindow")

        fightUtils.title_learn("战斗", 5, "剑圣", 1, context)
        context.run_task("Fight_ReturnMainWindow")

        fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("战斗", 5, "魔力强化", 3, context)
        fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
        context.run_task("Fight_ReturnMainWindow")

        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            time.sleep(1)
            for _ in range(2):
                if fightUtils.findItem("武器大师执照", True, context, threshold=0.8):
                    break
        # 这里进夹层压血
        if self.target_earthgate_para >= 0:
            self.gotoSpecialLayer(context)
            death = None

            for i in range(20):
                fightUtils.cast_magic("光", "祝福术", context)
                death = context.run_recognition(
                    "Fight_FindRespawn",
                    context.tasker.controller.post_screencap().wait().get(),
                )
                if death:
                    logger.info(f"已死亡，准备出图")
                    self.isDeath = True
                    context.run_task("Screenshot")
                    break
                elif self.layers == 99:
                    logger.info(f"当前在99层，大概率无法死亡，走正常流程离开")
                    time.sleep(3)
                    context.run_task("Fight_ReturnMainWindow")
                    self.leaveSpecialLayer(context)
                    context.run_task("Fight_ReturnMainWindow")
                    context.run_task("Screenshot")
                    break
                if i > 15:
                    time.sleep(3)
                    if not self.Check_GridAndMonster(context, False):
                        context.run_task("Screenshot")
                        logger.info(f"怪物不在了，无法死亡，走正常流程离开")
                        time.sleep(3)
                        context.run_task("Fight_ReturnMainWindow")
                        self.leaveSpecialLayer(context)
                        context.run_task("Fight_ReturnMainWindow")
                        context.run_task("Screenshot")
                        break

            # 增加截图调试
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
                },
            )

            if death:
                logger.info("可以出图了")
                context.run_task("Fight_FindLeaveText")
                # 等待6秒
                time.sleep(6)
                if context.run_recognition(
                    "ConfirmButton",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    context.run_task("ConfirmButton")

        self.isLeaveMaze = True
        # 到这可以出图了

    @timing_decorator
    def handle_MarsExchangeShop_event(self, context: Context, image):
        # MarsDagger : ExchangeForDagger
        # MarsHighLevelStaff : ExchangeForHighlevel
        # MarsMagicNecklace : ExchangeForHighlevel
        # 大于10层才处理交换商店事件,刷果子需要压低攻击,压低血量,提高魔力和护盾
        target = None
        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForDagger"
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if self.layers > 10 and context.run_recognition("Mars_Exchange_Shop", image):
            logger.info("触发Mars交换战利品事件")
            context.run_task("Mars_Exchange_Shop")
            nodedetail = context.run_task("Mars_Exchange_Shop_Check")
            if nodedetail:
                for node in nodedetail.nodes:
                    # all in 法杖
                    if node.name == "Mars_Exchange_Shop_Check_Staff":
                        target = "法杖"
                        #优先换掉盾牌,这个傻逼玩意
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForStaff"
                        #其次换掉短剑,和其他
                        exchange_dir_2 = "fight/Mars/MarsExchangeDir/ExchangeForStaff2"
                    #todo 首先保证10个反甲,其次辅助祷告书和火焰护身符
                    elif node.name == "Mars_Exchange_Shop_Check_Thornmail":
                        target = "反甲"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForHighlevel"
                        exchange_dir_2 = ("fight/Mars/MarsExchangeDir/ExchangeForHighlevel_2")
                    #todo 其次祷告书
                    elif node.name == "Mars_Exchange_Shop_Check_Highlevel_1":
                        target = "魔法伤害加成法杖"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForHighlevel"
                        exchange_dir_2 = (
                            "fight/Mars/MarsExchangeDir/ExchangeForHighlevel_2"
                        )
                    #todo 最后换掉不需要的几个，诅咒挂坠,守护挂坠,愤怒法师的短棍
                    elif node.name == "Mars_Exchange_Shop_Check_Highlevel_2":
                        target = "魔法伤害加成项链"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForHighlevel"
                        exchange_dir_2 = (
                            "fight/Mars/MarsExchangeDir/ExchangeForHighlevel_2"
                        )
                if target:
                    logger.info(f"交换商店出现了{target}")
                    if context.run_recognition(
                        "Mars_Exchange_Shop_Add",
                        context.tasker.controller.post_screencap().wait().get(),
                    ):
                        for _ in range(5):
                            context.run_task(
                                "Mars_Exchange_Shop_Add",
                                pipeline_override={
                                    "Mars_Exchange_Shop_Add_Equipment_Choose": {
                                        "template": exchange_dir
                                    },
                                    "Mars_Exchange_Shop_Add_Equipment_Choose_2": {
                                        "template": exchange_dir_2
                                    },
                                },
                            )
                            # context.run_task("Screenshot")
                            if context.run_recognition(
                                "Mars_Exchange_Shop_Add_Equipment_Select",
                                context.tasker.controller.post_screencap().wait().get(),
                            ):
                                context.run_task(
                                    "Mars_Exchange_Shop_Add_Equipment_Select"
                                )
                            else:
                                logger.info("没有可供兑换的战利品了,跳过这次交换")
                                break

                            if AddButtonRecoDetail := context.run_recognition(
                                "Mars_Exchange_Shop_AddButtonReco",
                                context.tasker.controller.post_screencap().wait().get(),
                            ):
                                box = AddButtonRecoDetail.best_result.box
                                for _ in range(10):
                                    context.tasker.controller.post_click(
                                        box[0] + box[2] // 2,
                                        box[1] + box[3] // 2,
                                    ).wait()
                                    time.sleep(0.02)
                            else:
                                logger.warning(
                                    "一般不会到这里,进入这里说明由于未知原因离开交换商店了。"
                                )
                            context.run_task("Mars_Exchange_Shop_Confirm_Exchange")

                            # 如果交换完已经在桌面了，说明10个短剑都交换完了
                            if context.run_recognition(
                                "Fight_MainWindow",
                                context.tasker.controller.post_screencap().wait().get(),
                            ):
                                if target != None:
                                    logger.info(f"已经交换了十把{target}~")
                                break
                            else:
                                logger.info("可用于更换的战利品没有了, 去获取更多吧~")
                else:
                    logger.info("这个交换商店没有任何目标战利品, 去其他楼层找吧~")
            context.run_task("Fight_ReturnMainWindow")
            return True

    @timing_decorator
    def handle_MarsRuinsShop_event(self, context: Context, image):
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if context.run_recognition("Mars_RuinsShop", image):
            logger.info("触发Mars商店事件")
            context.run_task("Mars_RuinsShop")
            return True
        return False

    @timing_decorator
    def handle_MarsReward_event(self, context: Context, image=None):
        normalReward = self.layers % 2 == 1
        bossReward = self.layers >= 30 and self.layers % 10 == 0
        if not (normalReward or bossReward):
            return True
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()

        if normalReward:
            self.handle_MarsStele_event(context, image)
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
                },
            )
            self.Check_GridAndMonster(context)
            for _ in range(5):
                if not context.run_recognition("Mars_Reward", image):
                    logger.debug("当前截图中奖励可能被遮挡, 再次截图尝试")
                    context.run_task(
                        "WaitStableNode_ForOverride",
                        pipeline_override={
                            "WaitStableNode_ForOverride": {
                                "pre_wait_freezes": {"time": 300}
                            }
                        },
                    )
                    image = context.tasker.controller.post_screencap().wait().get()
                else:
                    break
        if normalReward and context.run_recognition("Mars_Reward", image):
            logger.info("触发Mars奖励事件")
            mars_reward_detail = context.run_task("Mars_Reward")
            if mars_reward_detail.nodes:
                for node in mars_reward_detail.nodes:
                    if node.name == "Mars_Inter_Confirm_Fail":
                        logger.info("领取Mars奖励失败, 为了防止卡死, 跳过这次领取")
                        return False
            return True

        if bossReward and context.run_recognition("Mars_BossReward", image):
            logger.info("触发MarsBoss奖励事件")
            context.run_task("Mars_BossReward")
            if self.isGetTitanFoot == False and self.layers >= 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isGetTitanFoot = True
                    # 关闭泰坦
            if self.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.isGetMagicAssist = True
                    # 关闭魔法助手
            return True
        return True

    @timing_decorator
    def handle_MarsBody_event(self, context: Context, image):
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        # 摸金事件卡返回基本只会发生在夹层中
        if bodyRecoDetail := context.run_recognition("Mars_Body", image):
            logger.info("触发Mars摸金事件")
            for body in bodyRecoDetail.filterd_results:
                box = body.box
                context.tasker.controller.post_click(
                    box[0] + box[2] // 2,
                    box[1] + box[3] // 2,
                ).wait()
                context.run_task(
                    "WaitStableNode_ForOverride",
                    pipeline_override={
                        "WaitStableNode_ForOverride": {
                            "pre_wait_freezes": {"time": 100}
                        }
                    },
                )
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition(
                    "Mars_Inter_Confirm_Success",
                    img,
                ):
                    context.run_task("Mars_Inter_Confirm_Success")
                elif context.run_recognition("Mars_Inter_Confirm_Pickup", img):
                    context.run_task("Mars_Inter_Confirm_Pickup")
                    time.sleep(2)
                    context.run_task("Mars_Inter_Confirm_Success")
                    time.sleep(2)
                    context.run_task("Mars_Inter_Confirm_Success")
                else:
                    logger.info("可能在夹层中有怪物没有清理")
                    context.run_task("Mars_Inter_Confirm_Fail")
                    return False
            return True
        return True

    @timing_decorator
    def handle_MarsStele_event(self, context: Context, image):
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if self.layers % 2 == 1 and context.run_recognition("Mars_Stele", image):
            logger.info("触发Mars斩断事件")
            context.run_task("Mars_Stele")
            return True
        return False

    @timing_decorator
    #todo 战利品，只选择要的哪几个，尸体能不摸就不摸，加攻击和血量的绝对不能摸，
    def handle_MarsStatue_event(self, context: Context, image=None):
        if self.layers >= 30 and self.layers % 10 == 0:
            return False
        if self.layers < 10 and self.useEarthGate < 1:
            return False
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Mars_Statue", image):
            logger.info(f"触发Mars白胡子老头事件, 献祭一下战利品吧~")
            if self.useEarthGate > 0 and self.layers < 80:
                # 说明大地回来了，可以开始献祭至高战利品了
                logger.info(f"大地已回来，可以开始献祭至高战利品了")
                context.run_task(
                    "Mars_Statue",
                    pipeline_override={"Mars_Statue_Open_Next2": {"enabled": True}},
                )
            else:
                context.run_task(
                    "Mars_Statue",
                    pipeline_override={"Mars_Statue_Open_Next2": {"enabled": False}},
                )
            if self.isGetTitanFoot == False and self.layers > 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isGetTitanFoot = True
                    # 关闭泰坦
            if self.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.isGetMagicAssist = True
                    # 关闭魔法助手
            return True
        return False

    @timing_decorator
    #todo 福神不缺这点，夹层直接跳过
    def handle_SpecialLayer_event(self, context: Context, image):
        # 波塞冬不放柱子，用冰锥打裸男
        if (30 <= self.layers + 1 <= 150) and ((self.layers + 1) % 10 == 0):
            for _ in range(5):
                if not context.run_recognition("Mars_GotoSpecialLayer", image):
                    logger.debug("当前截图中休息室可能被遮挡, 再次截图尝试")
                    context.run_task(
                        "WaitStableNode_ForOverride",
                        pipeline_override={
                            "WaitStableNode_ForOverride": {
                                "pre_wait_freezes": {"time": 300}
                            }
                        },
                    )
                    image = context.tasker.controller.post_screencap().wait().get()
                else:
                    break
            logger.info("触发Mars休息室事件")
            if not self.gotoSpecialLayer(context):
                return False
            if self.isUseMagicAssist:
                fightUtils.cast_magic("土", "石肤术", context)
            if self.layers < 100:
                context.run_task("Mars_Shower")
            context.run_task("Mars_EatBread")
            if self.target_magicgumball_para == "波塞冬":
                if self.layers <= 89:
                    if fightUtils.cast_magic(
                        "暗",
                        "死亡波纹",
                        context,
                    ):
                        times = 2
                        for _ in range(times):
                            if not fightUtils.cast_magic(
                                "水",
                                "冰锥术",
                                context,
                                (special_layer_monster_1_x, special_layer_monster_1_y),
                            ):
                                break
                        for _ in range(times):
                            if not fightUtils.cast_magic(
                                "水",
                                "冰锥术",
                                context,
                                (special_layer_monster_2_x, special_layer_monster_2_y),
                            ):
                                break
            context.run_task("Fight_ReturnMainWindow")
            self.leaveSpecialLayer(context)
            # 检查一下状态
            self.Check_DefaultStatus(context)

            return True
        return True

    def handle_UseMagicAssist_event(self, context: Context):
        if (
            self.isGetMagicAssist
            # 福神默认700之后开魔法助手和泰坦
            and self.layers > 700
            and self.isUseMagicAssist == False
        ):
            logger.info("开启魔法助手帮助推图")
            fightUtils.cast_magic_special("魔法助手", context)
            self.isUseMagicAssist = True
    #todo,不捡血包,所以不开自动拾取，或者700层以后自动开
    def handle_auto_pickup_event(self, context: Context):
        if ( self.layers > 700):
            logger.info("开启自动拾取, 等待动画结束")
            context.run_task("Fight_PickUpAll_Emptyfloor")
            self.isAutoPickup = True

    @timing_decorator
    def handle_postLayers_event(self, context: Context):
        # self.handle_perfect_event(context)
        # 等待画面稳定
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
            },
        )
        fightUtils.handle_dragon_event("马尔斯", context)
        self.Check_DefaultStatus(context)
        # 检查默认装备，提升稳定性
        self.Check_DefaultEquipment(context)
        # 临时使用， 小恶魔活动结束直接删除即可
        if (
            # 距离出图楼层还有30层
            self.layers > self.target_leave_layer_para - 29
            and (self.layers - 1) % 10 == 0
            and self.useDemon < 3
        ):
            fightUtils.openBagAndUseItem("小恶魔", True, context)
            self.useDemon += 1
            if (
                self.target_earthgate_para == 2
                and self.useEarthGate < self.target_earthgate_para
                and self.layers >= 100
                and self.target_leave_layer_para >= 129
            ):
                # 把当前的大地次数记作目标大地次数，不要尝试大地，提前出图
                self.target_earthgate_para = self.useEarthGate
                self.target_leave_layer_para = 119
        self.handle_MarsReward_event(context)
        context.run_task("Fight_ReturnMainWindow")

        image = context.tasker.controller.post_screencap().wait().get()
        self.handle_MarsBody_event(context, image)
        self.handle_MarsRuinsShop_event(context, image)
        context.run_task("Fight_ReturnMainWindow")
        self.handle_MarsStatue_event(context, image)
        self.handle_MarsExchangeShop_event(context, image)
        # 点称号挪到战后，确保购买战利品有足够的探索点
        self.Check_DefaultTitle(context)

        if context.run_recognition("Fight_FindRespawn", image):
            logger.info("检测到死亡， 尝试小SL")
            fightUtils.Saveyourlife(context)
            fightUtils.cast_magic("水", "治疗术", context)
            fightUtils.cast_magic("土", "石肤术", context)
            return False

        if not self.handle_SpecialLayer_event(context, image):
            # 如果卡剧情(离开),则返回False, 重新清理该层
            return False

        if self.handle_EarthGate_event(context):
            # 大地成功,需要回到战前准备开始清理该层，大地失败则继续往下走
            return False

        # 检测隐藏冈布奥
        if self.layers >= 90 and context.run_recognition(
            "Mars_HideGumball", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Mars_HideGumball")

        if (
            (self.layers >= self.target_leave_layer_para - 2)
            # 到了99层依然没有获得魔法助手就结算
            or (101 > self.layers > 97 and self.isGetMagicAssist == False)
        ) and context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            self.handle_before_leave_maze_event(context)
        else:
            if self.isAutoPickup == self.target_autopickup_para:
                if not context.run_recognition("Fight_OpenedDoor", image):
                    context.run_task(
                        "Mars_Fight_ClearCurrentLayer",
                        pipeline_override={
                            "Mars_Fight_ClearCurrentLayer": {
                                "custom_action_param": {"layers": self.layers}
                            }
                        },
                    )
                if context.run_recognition(
                    "Fight_FindRespawn",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    logger.info("下楼事件前检测到死亡， 尝试小SL")
                    fightUtils.Saveyourlife(context)
                    fightUtils.cast_magic("水", "治疗术", context)
                    fightUtils.cast_magic("土", "石肤术", context)
                    return False
                logger.info("触发下楼事件")
                fightUtils.handle_downstair_event(context)
            else:
                logger.info("触发开启自动拾取事件")
                self.handle_auto_pickup_event(context)
        return True

    @timing_decorator
    def handle_clearCurLayer_event(self, context: Context):
        # boss层开始探索
        if self.layers >= 30 and self.layers % 10 == 0:
            # boss召唤动作
            if not self.handle_boss_event(context):
                return False
            # fightUtils.handle_dragon_event("马尔斯", context)
            # if context.run_recognition("Fight_FindRespawn", image):
            #     logger.info("检测到死亡， 尝试小SL")
            #     fightUtils.Saveyourlife(context)
            #     return False
            return True
        # 小怪层探索
        else:
            context.run_task(
                "Mars_Fight_ClearCurrentLayer",
                pipeline_override={
                    "Mars_Fight_ClearCurrentLayer": {
                        "custom_action_param": {"layers": self.layers}
                    }
                },
            )

        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image):
            logger.info("检测到死亡， 尝试小SL")
            fightUtils.Saveyourlife(context)
            fightUtils.cast_magic("水", "治疗术", context)
            fightUtils.cast_magic("土", "石肤术", context)
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Success",
            image,
        ):
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Success")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Fail",
            image,
        ):
            if context.run_recognition("Fight_FindRespawn", image):
                logger.info("检测到死亡， 尝试小SL")
                fightUtils.Saveyourlife(context)
                fightUtils.cast_magic("水", "治疗术", context)
                fightUtils.cast_magic("土", "石肤术", context)
                return False
            logger.info("检测到卡离开, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Fail")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image):
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True
    #todo 福神不需要休息
    def gotoSpecialLayer(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        time.sleep(1)
        if context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ):

            context.run_task("Mars_GotoSpecialLayer")
            for _ in range(10):
                if context.run_recognition(
                    "Mars_GotoSpecialLayer_Confirm",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    context.run_task("Mars_GotoSpecialLayer_Confirm")
                    break
                if context.run_recognition(
                    "Mars_Inter_Confirm_Fail",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    context.run_task("Mars_Inter_Confirm_Fail")
                    logger.info("进入休息室失败, 需要重新清理当前层")
                    return False
                time.sleep(1)

            while not context.run_recognition(
                "Mars_LeaveSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                time.sleep(1)
            logger.info("进入休息室")
            return True
        return True

    # def leaveSpecialLayer(self, context: Context):
    #     context.run_task("Fight_ReturnMainWindow")
    #     for _ in range(10):
    #         if context.run_recognition(
    #             "Mars_LeaveSpecialLayer",
    #             context.tasker.controller.post_screencap().wait().get(),
    #         ):
    #             context.run_task("Mars_LeaveSpecialLayer")
    #             break
    #     while not context.run_recognition(
    #         "Mars_GotoSpecialLayer",
    #         context.tasker.controller.post_screencap().wait().get(),
    #     ):
    #         time.sleep(1)
    #     logger.info("离开休息室")
    #     return True

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.target_leave_layer_para = int(
            context.get_node_data("Mars_Target_Layer_Setting")["recognition"]["param"][
                "expected"
            ][0]
        )
        self.target_earthgate_para = int(
            context.get_node_data("Mars_Target_Earthgate_Setting")["recognition"][
                "param"
            ]["expected"][0]
        )
        self.target_autopickup_para = bool(
            context.get_node_data("Fight_PickUpAll_Emptyfloor")["enabled"]
        )
        self.target_magicgumball_para = str(
            context.get_node_data("select_InputBox_Text2")["action"]["param"][
                "input_text"
            ]
        )
        self.astrological_title_para = (
            context.get_node_data("Mars_Astrological_Title_Setting")["recognition"][
                "param"
            ]["expected"][0]
        ).lower() == "true"

        # initialize
        self.initialize(context)
        logger.info(f"本次任务目标层数: {self.target_leave_layer_para}")

        while self.layers <= 1201:
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

            # 探索当前层
            if not self.handle_clearCurLayer_event(context):
                continue

            # 检查是否触发中断事件
            if not self.handle_interrupt_event(context):
                continue

            # 检查是否触发战后事件, 战后事件是否出现异常
            if not self.handle_postLayers_event(context):
                continue
            if self.isLeaveMaze:
                logger.info(f"current layers {self.layers},出图准备完成,开始退出agent")
                break

        logger.info(f"马尔斯探索结束，当前到达{self.layers}层")
        context.run_task("Fight_LeaveMaze")
        # 获取并打印统计信息
        stats = fightUtils.get_time_statistics()
        for func_name, data in stats.items():
            logger.info(
                f"{func_name} 执行 {data['count']} 次，总耗时: {data['total_time']:.4f}秒"
            )
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Mars_Fight_ClearCurrentLayer")
class Mars_Fight_ClearCurrentLayer(CustomAction):

    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor(target_wish="马尔斯")

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 读取传入的层数参数（兼容 dict/对象）
        layers_arg = json.loads(argv.custom_action_param)["layers"]
        if layers_arg is not None:
            # logger.info(f"Mars_Fight_ClearCurrentLayer 接收到 layers={layers_arg}")
            try:
                # 作为变量传入处理器，后续可按需使用
                self.fightProcessor.layers = layers_arg
            except Exception:
                pass

        # 进行特殊配置以适应Mars
        self.fightProcessor.grid_count = 40
        self.fightProcessor.targetWish = "马尔斯"
        self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
