"""Allowlisted diagnostics: no exception messages, headers, input, or frame locals."""

from pathlib import Path

from openai import APIConnectionError, APIError, APITimeoutError


PROVIDER_CODES = frozenset({
    "insufficient_quota", "credit_balance_exhausted", "billing_not_active",
    "usage_limit_exceeded", "project_spend_limit_exceeded", "organization_spend_limit_exceeded",
    "organization_usage_limit_exceeded", "session_budget_exceeded", "rate_limit_exceeded",
    "model_not_found", "resource_not_found", "authentication_error", "invalid_api_key",
    "permission_denied", "invalid_request", "invalid_request_error", "context_length_exceeded",
    "server_error", "internal_error", "server_overloaded", "flex_unavailable", "connection_failed",
    "request_timeout", "sandbox_error", "executor_version_incompatible", "active_turn_not_steerable",
    "cyber_policy", "misalignment_policy_violation",
})
STAGES = frozenset({
    "preflight", "create_session", "read_stream", "parse_event", "dispatch_tool", "submit_tool",
    "retrieve_turn", "retrieve_items", "validate_output", "cancel_session", "delete_session",
    "inspect_session", "list_turns", "inspect_turn", "client_setup", "unknown",
})
EXCEPTION_TYPES = frozenset({
    "APIError", "APIConnectionError", "APITimeoutError", "APIResponseValidationError",
    "BadRequestError", "AuthenticationError", "PermissionDeniedError", "NotFoundError",
    "ConflictError", "UnprocessableEntityError", "RateLimitError", "InternalServerError",
    "AttributeError", "TypeError", "ValueError", "KeyError", "RuntimeError", "TimeoutError",
    "ValidationError", "PydanticSerializationError", "JSONDecodeError", "AgentFailure",
})
AGENT_DIRECTORY = Path(__file__).resolve().parent


def provider_code(value) -> str | None:
    return value if isinstance(value, str) and value in PROVIDER_CODES else None


def error_category(error: BaseException) -> str:
    code = provider_code(getattr(error, "code", None))
    if isinstance(error, (TimeoutError, APITimeoutError)):
        return "timeout"
    if isinstance(error, APIConnectionError):
        return "connection_error"
    if code in {"insufficient_quota", "credit_balance_exhausted", "billing_not_active"}:
        return "billing_or_quota_error"
    if code in {"usage_limit_exceeded", "project_spend_limit_exceeded", "organization_spend_limit_exceeded",
                "organization_usage_limit_exceeded", "session_budget_exceeded"}:
        return "usage_limit"
    if code == "rate_limit_exceeded":
        return "rate_limit"
    if code in {"model_not_found", "resource_not_found", "permission_denied"}:
        return "access_or_resource_error"
    if code in {"authentication_error", "invalid_api_key"}:
        return "authentication_error"
    status = getattr(error, "status_code", None)
    if isinstance(error, APIError):
        return {401: "authentication_error", 403: "access_denied", 429: "rate_or_quota_limit"}.get(
            status, "provider_error")
    return "agent_error"


def safe_exception(error: BaseException, stage: str) -> dict:
    """Only static metadata; deliberately never call str(error) or format_exc()."""
    kind = type(error).__name__
    result = {"stage": stage if stage in STAGES else "unknown",
              "exception_type": kind if kind in EXCEPTION_TYPES else "UnexpectedError",
              "category": error_category(error)}
    status = getattr(error, "status_code", None)
    if type(status) is int and 100 <= status <= 599:
        result["http_status"] = status
    code = provider_code(getattr(error, "code", None))
    if code:
        result["provider_code"] = code
    # Line numbers in known application files are useful without showing paths/code/locals.
    locations = []
    trace = error.__traceback__
    while trace:
        path = Path(trace.tb_frame.f_code.co_filename)
        if path.parent == AGENT_DIRECTORY and path.name in {"runtime.py", "maintenance.py", "__main__.py"}:
            locations.append({"file": path.name, "line": trace.tb_lineno})
        trace = trace.tb_next
    if locations:
        result["locations"] = locations[-5:]
    return result
