from enum import Enum


class ResultStatus(str, Enum):
    SUCCESS = "SUCCESS"
    BUSINESS_OUTCOME = "BUSINESS_OUTCOME"
    RECOVERABLE_ERROR = "RECOVERABLE_ERROR"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    HARD_FAILURE = "HARD_FAILURE"


class ReplayError(Exception):
    """Base class for replay errors."""


class BusinessOutcome(ReplayError):
    """Expected business result that is not a successful workflow completion."""


class RecoverableError(ReplayError):
    """Temporary error that may succeed if retried or recovered."""


class DriftDetected(ReplayError):
    """The runtime surface no longer matches the artifact."""


class HardFailure(ReplayError):
    """Failure that should stop replay immediately."""