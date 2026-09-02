import json
from dataclasses import dataclass, field

from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger


@dataclass
class DivineForgeSequenceConfig:
    """神锻系列测序模板配置；规则确认前保持禁用。"""

    enabled: bool = False
    sequence_length: int = 0
    candidate_names: list[str] = field(default_factory=list)
    success_signal: str = ""
    restore_strategy: str = ""

    @classmethod
    def from_custom_action_param(cls, raw_param) -> "DivineForgeSequenceConfig":
        if not raw_param:
            return cls()
        try:
            data = json.loads(raw_param) if isinstance(raw_param, str) else raw_param
            return cls(
                enabled=bool(data.get("enabled", False)),
                sequence_length=max(0, int(data.get("sequence_length", 0))),
                candidate_names=list(data.get("candidate_names", [])),
                success_signal=str(data.get("success_signal", "")),
                restore_strategy=str(data.get("restore_strategy", "")),
            )
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
            logger.error("沉眠小镇神锻测序模板参数无效")
            return cls()

    def missing_fields(self) -> list[str]:
        missing = []
        if self.sequence_length <= 0:
            missing.append("sequence_length")
        if not self.candidate_names:
            missing.append("candidate_names")
        if not self.success_signal:
            missing.append("success_signal")
        if not self.restore_strategy:
            missing.append("restore_strategy")
        return missing


class SleeptownDivineForgeSequenceTemplate(CustomAction):
    """神锻系列测序骨架。

    现有 divineForgeLand 的熔炉测序会熔炼装备并通过小 SL 恢复现场；沉眠
    小镇的具体神锻对象和成功信号尚未确认，所以这里不直接复用其破坏性动作。

    实装顺序：
    1. prepare_candidate：准备本轮候选对象。
    2. capture_baseline：读取探测前状态。
    3. execute_probe：执行一次会推进随机序列的动作。
    4. detect_success：比较结果或识别成功图标。
    5. record_result：把本轮结果写入序列表。
    6. restore_for_next_probe：恢复到下一轮可重复探测的现场。
    """

    def prepare_candidate(self, context: Context, index: int, candidate: str) -> bool:
        del context, index, candidate
        # TODO(SDF-01): 补充候选神锻对象的查找、选择与数量检查。
        return False

    def capture_baseline(self, context: Context):
        del context
        # TODO(SDF-02): 明确测序前需要记录的属性、物品数或界面状态。
        return None

    def execute_probe(self, context: Context, candidate: str) -> bool:
        del context, candidate
        # TODO(SDF-03): 补充一次神锻动作；默认不得点击或消耗资源。
        return False

    def detect_success(self, context: Context, baseline, success_signal: str):
        del context, baseline, success_signal
        # TODO(SDF-04): 补充成功模板、OCR、属性差值或其他判据。
        return None

    def record_result(self, sequence: list, index: int, result) -> None:
        sequence[index] = result

    def restore_for_next_probe(self, context: Context, strategy: str) -> bool:
        del context, strategy
        # TODO(SDF-05): 明确返回、暂离、小 SL 或其他可恢复方案。
        return False

    def run_sequence(
        self,
        context: Context,
        config: DivineForgeSequenceConfig,
    ) -> list:
        """待补规则的测序主循环模板；当前不会执行任何游戏动作。"""
        del context, config
        logger.warning("神锻测序主循环尚未实装，未执行任何游戏动作")
        return []

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        config = DivineForgeSequenceConfig.from_custom_action_param(
            argv.custom_action_param
        )
        if not config.enabled:
            logger.info("神锻测序模板当前为禁用状态，不执行游戏动作")
            return CustomAction.RunResult(success=False)

        missing = config.missing_fields()
        if missing:
            logger.error("神锻测序模板缺少参数：" + ", ".join(missing))
            return CustomAction.RunResult(success=False)

        sequence = self.run_sequence(context, config)
        return CustomAction.RunResult(success=bool(sequence))
