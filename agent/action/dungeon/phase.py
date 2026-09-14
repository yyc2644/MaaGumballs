from dataclasses import dataclass
from enum import Enum
from typing import Any


class PhaseStatus(str, Enum):
    SUCCESS = "success"
    RETRY = "retry"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class PhaseResult:
    status: PhaseStatus
    reason: str = ""
    data: Any = None

    @property
    def ok(self) -> bool:
        return self.status is PhaseStatus.SUCCESS

    @classmethod
    def success(cls, data=None, reason: str = "") -> "PhaseResult":
        return cls(PhaseStatus.SUCCESS, reason, data)

    @classmethod
    def retry(cls, reason: str = "") -> "PhaseResult":
        return cls(PhaseStatus.RETRY, reason)

    @classmethod
    def stopped(cls, reason: str = "") -> "PhaseResult":
        return cls(PhaseStatus.STOPPED, reason)

    @classmethod
    def failed(cls, reason: str = "") -> "PhaseResult":
        return cls(PhaseStatus.FAILED, reason)
