"""Utilities for querying and analyzing audit log data from Redis."""

import json
from datetime import datetime
from typing import Any, Optional

from core.audit.logger import AuditLogger
from core.redis_client import get_audit_keys
from core.settings import get_settings

settings = get_settings()


def get_execution_history(execution_id: str) -> list[dict[str, Any]]:
    """
    Retrieve all events for a specific execution.

    Args:
        execution_id: The execution ID to retrieve history for

    Returns:
        List of audit events sorted by timestamp
    """
    audit_logger = AuditLogger()
    return audit_logger.get_execution_history(execution_id)


def get_recent_executions(limit: int = 10) -> list[dict[str, Any]]:
    """
    Retrieve the most recent crew executions.

    Args:
        limit: Maximum number of executions to return

    Returns:
        List of recent crew executions, newest first
    """
    keys = get_audit_keys("audit:*:crew_start:*")

    if not keys:
        return []

    # Extract unique execution_ids and sort by creation time (reverse)
    execution_ids = list(set([key.split(":")[1] for key in keys]))
    execution_ids = execution_ids[:limit]

    result = []
    for exec_id in execution_ids:
        try:
            history = get_execution_history(exec_id)
            if history:
                # Get first event (CREW_START)
                start_event = next(
                    (e for e in history if e.get("event_type") == "crew_start"), None
                )
                if start_event:
                    result.append(start_event)
        except Exception:
            pass

    return result


def get_execution_summary(execution_id: str) -> dict[str, Any]:
    """
    Get a summary of an execution including metrics.

    Args:
        execution_id: The execution ID

    Returns:
        Dictionary with execution summary including duration, success, agent names, etc.
    """
    history = get_execution_history(execution_id)

    if not history:
        return {"error": f"No events found for execution {execution_id}"}

    # Find start and end events
    start_event = next(
        (e for e in history if e.get("event_type") == "crew_start"), None
    )
    end_event = next((e for e in history if e.get("event_type") == "crew_end"), None)

    # Count by type
    event_counts = {}
    for event in history:
        event_type = event.get("event_type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    # Extract tool calls
    tool_calls = [e for e in history if e.get("event_type") == "tool_call"]
    tool_names = set(tc.get("metadata", {}).get("tool_name") for tc in tool_calls)

    # Extract agent steps
    agent_steps = [e for e in history if e.get("event_type") == "agent_step"]
    agent_names = set(
        step.get("metadata", {}).get("agent_name") for step in agent_steps
    )

    summary = {
        "execution_id": execution_id,
        "event_counts": event_counts,
        "total_events": len(history),
        "start_event": start_event,
        "end_event": end_event,
        "tools_used": list(tool_names) if tool_names else [],
        "agents_involved": list(agent_names) if agent_names else [],
        "tool_call_count": len(tool_calls),
        "agent_step_count": len(agent_steps),
    }

    # Add metrics if available
    if start_event and end_event:
        try:
            start_time = datetime.fromisoformat(
                start_event.get("metadata", {}).get("timestamp", "")
            )
            end_time = datetime.fromisoformat(
                end_event.get("metadata", {}).get("timestamp", "")
            )
            duration = (end_time - start_time).total_seconds()
            summary["duration_seconds"] = duration
            summary["start_time"] = start_event.get("metadata", {}).get("timestamp")
            summary["end_time"] = end_event.get("metadata", {}).get("timestamp")
        except (ValueError, KeyError):
            pass

    return summary


def search_events(
    execution_id: Optional[str] = None,
    event_type: Optional[str] = None,
    tool_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Search audit events with optional filters.

    Args:
        execution_id: Filter by execution ID
        event_type: Filter by event type (e.g., "tool_call", "agent_step")
        tool_name: Filter by tool name
        agent_name: Filter by agent name

    Returns:
        List of matching events
    """
    if not execution_id:
        return []

    history = get_execution_history(execution_id)

    # Apply filters
    results = history

    if event_type:
        results = [e for e in results if e.get("event_type") == event_type]

    if tool_name:
        results = [
            e for e in results if e.get("metadata", {}).get("tool_name") == tool_name
        ]

    if agent_name:
        results = [
            e for e in results if e.get("metadata", {}).get("agent_name") == agent_name
        ]

    return results


def get_failed_tool_calls(execution_id: str) -> list[dict[str, Any]]:
    """
    Get all failed tool calls from an execution.

    Args:
        execution_id: The execution ID

    Returns:
        List of failed tool call events
    """
    events = search_events(execution_id=execution_id, event_type="tool_call")
    return [e for e in events if not e.get("metadata", {}).get("success", True)]


def get_execution_errors(execution_id: str) -> list[dict[str, Any]]:
    """
    Get all errors from an execution.

    Args:
        execution_id: The execution ID

    Returns:
        List of error events
    """
    events = search_events(execution_id=execution_id, event_type="crew_error")
    return events + search_events(execution_id=execution_id, event_type="tool_error")


def cleanup_old_audits(days: Optional[int] = None) -> int:
    """
    Delete audit records older than specified days.

    Args:
        days: Days to keep (default from settings.audit_retention_days)

    Returns:
        Number of records deleted
    """
    if days is None:
        days = settings.audit_retention_days

    audit_logger = AuditLogger()
    return audit_logger.clear_old_audits(days)


def export_execution_as_json(execution_id: str, pretty: bool = True) -> str:
    """
    Export an execution's audit trail as JSON.

    Args:
        execution_id: The execution ID
        pretty: Whether to pretty-print JSON

    Returns:
        JSON string representation of the execution
    """
    summary = get_execution_summary(execution_id)
    history = get_execution_history(execution_id)

    export_data = {"summary": summary, "events": history}

    if pretty:
        return json.dumps(export_data, indent=2, default=str)
    else:
        return json.dumps(export_data, default=str)


def get_tool_performance(execution_id: str) -> dict[str, Any]:
    """
    Analyze tool performance metrics for an execution.

    Args:
        execution_id: The execution ID

    Returns:
        Dictionary with tool performance metrics
    """
    tool_calls = search_events(execution_id=execution_id, event_type="tool_call")

    if not tool_calls:
        return {"total_tool_calls": 0}

    # Group by tool
    tool_metrics = {}
    for call in tool_calls:
        metadata = call.get("metadata", {})
        tool_name = metadata.get("tool_name", "unknown")

        if tool_name not in tool_metrics:
            tool_metrics[tool_name] = {
                "count": 0,
                "successful": 0,
                "failed": 0,
                "total_duration_seconds": 0.0,
                "avg_duration_seconds": 0.0,
            }

        metrics = tool_metrics[tool_name]
        metrics["count"] += 1

        if metadata.get("success", True):
            metrics["successful"] += 1
        else:
            metrics["failed"] += 1

        duration = metadata.get("duration_seconds", 0)
        metrics["total_duration_seconds"] += duration

    # Calculate averages
    for tool_name, metrics in tool_metrics.items():
        if metrics["count"] > 0:
            metrics["avg_duration_seconds"] = (
                metrics["total_duration_seconds"] / metrics["count"]
            )

    return {
        "total_tool_calls": len(tool_calls),
        "unique_tools": len(tool_metrics),
        "tools": tool_metrics,
    }


def get_agent_activity(execution_id: str) -> dict[str, Any]:
    """
    Analyze agent activity for an execution.

    Args:
        execution_id: The execution ID

    Returns:
        Dictionary with agent activity metrics
    """
    agent_steps = search_events(execution_id=execution_id, event_type="agent_step")

    if not agent_steps:
        return {"total_steps": 0}

    # Group by agent
    agent_metrics = {}
    for step in agent_steps:
        metadata = step.get("metadata", {})
        agent_name = metadata.get("agent_name", "unknown")

        if agent_name not in agent_metrics:
            agent_metrics[agent_name] = {
                "step_count": 0,
                "tools_used": set(),
                "total_duration_seconds": 0.0,
            }

        metrics = agent_metrics[agent_name]
        metrics["step_count"] += 1

        tool_used = metadata.get("tool_used")
        if tool_used:
            metrics["tools_used"].add(tool_used)

        duration = metadata.get("duration_seconds", 0)
        metrics["total_duration_seconds"] += duration

    # Convert sets to lists
    for agent_name, metrics in agent_metrics.items():
        metrics["tools_used"] = list(metrics["tools_used"])

    return {
        "total_steps": len(agent_steps),
        "unique_agents": len(agent_metrics),
        "agents": agent_metrics,
    }
