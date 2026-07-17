class AgentRuntimeError(Exception):
    retryable = False


class ToolTimeoutError(AgentRuntimeError):
    retryable = True


class ToolValidationError(AgentRuntimeError):
    retryable = False


class EvidenceValidationError(AgentRuntimeError):
    retryable = False


class HumanApprovalRequired(AgentRuntimeError):
    retryable = False
