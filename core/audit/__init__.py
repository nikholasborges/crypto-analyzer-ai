"""Audit logging package for the multi-agent system."""

from core.audit.decorators import audit_function, audit_tool_call
from core.audit.logger import AuditLogger
from core.audit.models import (
    AgentStep,
    AuditEvent,
    CrewExecution,
    EventType,
    ExecutionError,
    TaskCompletion,
    ToolCall,
)
from core.audit.queries import (
    cleanup_old_audits,
    export_execution_as_json,
    get_agent_activity,
    get_execution_history,
    get_execution_summary,
    get_failed_tool_calls,
    get_recent_executions,
    get_tool_performance,
    search_events,
)

__all__ = [
    # Logger
    "AuditLogger",
    # Models
    "EventType",
    "AuditEvent",
    "CrewExecution",
    "AgentStep",
    "ToolCall",
    "TaskCompletion",
    "ExecutionError",
    # Decorators
    "audit_tool_call",
    "audit_function",
    # Queries
    "get_execution_history",
    "get_recent_executions",
    "get_execution_summary",
    "search_events",
    "get_failed_tool_calls",
    "cleanup_old_audits",
    "export_execution_as_json",
    "get_tool_performance",
    "get_agent_activity",
]
