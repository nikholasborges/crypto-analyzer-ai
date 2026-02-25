"""Audit logger for capturing multi-agent system interactions."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from core.audit.models import (
    AgentStep,
    AuditEvent,
    CrewExecution,
    EventType,
    ExecutionError,
    TaskCompletion,
    ToolCall,
)
from core.redis_client import delete_audit_keys, get_audit_keys, set_audit_data
from core.settings import get_settings

logger = logging.getLogger(__name__)

# Thread pool for non-blocking Redis operations
_AUDIT_THREAD_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit-")


class AuditLogger:
    """Centralized audit logging for crew executions (non-blocking)."""

    def __init__(self):
        self.settings = get_settings()
        self.current_execution_id: Optional[str] = None

    def start_execution(
        self, topic: str, agent_names: list[str], task_count: int
    ) -> str:
        """
        Log the start of a crew execution (non-blocking).

        Args:
            topic: Research topic or input
            agent_names: List of agent names
            task_count: Number of tasks

        Returns:
            Execution ID for tracking this execution
        """
        if not self.settings.audit_enabled:
            return str(uuid4())

        self.current_execution_id = str(uuid4())
        event = CrewExecution(
            event_type=EventType.CREW_START,
            execution_id=self.current_execution_id,
            topic=topic,
            agent_names=agent_names,
            task_count=task_count,
        )
        # Submit to background thread (non-blocking)
        self._save_event_async(event)
        logger.debug(f"Audit: Crew execution started - ID: {self.current_execution_id}")
        return self.current_execution_id

    def end_execution(
        self,
        execution_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """
        Log the end of a crew execution (non-blocking).

        Args:
            execution_id: The execution ID to end
            success: Whether execution succeeded
            error_message: Error message if applicable
            duration_seconds: Total execution time
        """
        if not self.settings.audit_enabled:
            return

        event = CrewExecution(
            event_type=EventType.CREW_END,
            execution_id=execution_id,
            topic="",  # Not used for end event
            agent_names=[],
            task_count=0,
            ended_at=datetime.utcnow(),
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
        )
        # Submit to background thread (non-blocking)
        self._save_event_async(event)
        logger.debug(
            f"Audit: Crew execution ended - ID: {execution_id}, Success: {success}"
        )

    def log_agent_step(
        self,
        execution_id: str,
        agent_name: str,
        step_number: int,
        reasoning: str,
        tool_used: Optional[str] = None,
        tool_input: Optional[dict[str, Any]] = None,
        token_usage: Optional[dict[str, int]] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """
        Log an agent step during execution.

        Args:
            execution_id: Execution ID
            agent_name: Name of agent
            step_number: Step number
            reasoning: Agent's reasoning
            tool_used: Tool name if used
            tool_input: Tool input if used
            token_usage: Token usage
            duration_seconds: Step duration
        """
        if not self.settings.audit_enabled:
            return

        event = AgentStep(
            event_type=EventType.AGENT_STEP,
            execution_id=execution_id,
            agent_name=agent_name,
            step_number=step_number,
            reasoning=reasoning,
            tool_used=tool_used,
            tool_input=tool_input,
            token_usage=token_usage or {},
            duration_seconds=duration_seconds,
        )
        # Non-blocking async save
        self._save_event_async(event)

    def log_tool_call(
        self,
        execution_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_seconds: float = 0.0,
        error_message: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """
        Log a tool call.

        Args:
            execution_id: Execution ID
            tool_name: Tool name
            tool_input: Input parameters
            tool_output: Output from tool
            status_code: HTTP status code if applicable
            duration_seconds: Execution duration
            error_message: Error if failed
            success: Whether call succeeded
        """
        if not self.settings.audit_enabled:
            return

        event = ToolCall(
            event_type=EventType.TOOL_CALL,
            execution_id=execution_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status_code=status_code,
            duration_seconds=duration_seconds,
            error_message=error_message,
            success=success,
        )
        # Non-blocking async save
        self._save_event_async(event)

    def log_task_completion(
        self,
        execution_id: str,
        task_name: str,
        agent_name: str,
        output: str,
        token_usage: Optional[dict[str, int]] = None,
        duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log task completion.

        Args:
            execution_id: Execution ID
            task_name: Task name
            agent_name: Agent that ran it
            output: Task output
            token_usage: Token usage
            duration_seconds: Task duration
            success: Whether succeeded
            error_message: Error if failed
        """
        if not self.settings.audit_enabled:
            return

        # Truncate output for preview
        output_preview = output[:500] if output else ""

        event = TaskCompletion(
            event_type=EventType.TASK_END,
            execution_id=execution_id,
            task_name=task_name,
            agent_name=agent_name,
            output_preview=output_preview,
            full_output_length=len(output) if output else 0,
            token_usage=token_usage or {},
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
        )
        # Non-blocking async save
        self._save_event_async(event)

    def log_error(
        self,
        execution_id: str,
        error_type: str,
        error_message: str,
        error_traceback: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        recoverable: bool = False,
    ) -> None:
        """
        Log an error during execution.

        Args:
            execution_id: Execution ID
            error_type: Type of error
            error_message: Error message
            error_traceback: Full traceback
            context: Context of error
            recoverable: Whether error was recoverable
        """
        if not self.settings.audit_enabled:
            return

        event = ExecutionError(
            event_type=EventType.CREW_ERROR,
            execution_id=execution_id,
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            context=context,
            recoverable=recoverable,
        )
        # Non-blocking async save
        self._save_event_async(event)
        logger.error(
            f"Audit: Error logged - Type: {error_type}, Message: {error_message}"
        )

    def _save_event(self, event: AuditEvent) -> None:
        """
        Save an audit event to Redis (blocking version, only for critical operations).

        Args:
            event: The audit event to save
        """
        try:
            # Serialize event to JSON with datetime formatting
            event_json = self._serialize_event(event)

            # Build Redis key: audit:{execution_id}:{event_type}:{event_id}
            key = f"audit:{event.execution_id}:{event.event_type}:{event.event_id}"

            # Calculate TTL based on retention policy
            ttl = self.settings.audit_retention_days * 24 * 60 * 60

            # Store in Redis with timeout protection
            set_audit_data(key, event_json, ttl=ttl)
        except Exception as e:
            # Fail silently to prevent audit errors from breaking crew execution
            logger.debug(f"Failed to save audit event: {e}")

    def _save_event_async(self, event: AuditEvent) -> None:
        """
        Submit an audit event save to background thread pool (non-blocking).

        This prevents long Redis operations from blocking the LLM's Chain of Thought.

        Args:
            event: The audit event to save
        """
        if not self.settings.audit_enabled:
            return

        # Submit to thread pool - returns immediately
        _AUDIT_THREAD_POOL.submit(self._save_event, event)

    @staticmethod
    def _serialize_event(event: AuditEvent) -> str:
        """
        Serialize an audit event to JSON with pretty formatting.

        Args:
            event: Event to serialize

        Returns:
            JSON string
        """
        return json.dumps(
            json.loads(event.model_dump_json()),
            indent=2,
            default=str,
        )

    @staticmethod
    def get_execution_history(execution_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all events for a specific execution.

        Args:
            execution_id: The execution ID

        Returns:
            List of audit events in chronological order
        """
        try:
            keys = get_audit_keys(f"audit:{execution_id}:*")
            events = []
            for key in keys:
                from core.redis_client import get_audit_data

                data = get_audit_data(key)
                if data:
                    events.append(json.loads(data))
            # Sort by timestamp
            return sorted(events, key=lambda x: x.get("timestamp", ""))
        except Exception as e:
            logger.error(f"Failed to retrieve execution history: {e}")
            return []

    @staticmethod
    def clear_old_audits(days: int) -> int:
        """
        Clear audit logs older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of keys deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = cutoff_date.isoformat()

            # Get all audit keys
            keys = get_audit_keys("audit:*")
            deleted_count = 0

            for key in keys:
                from core.redis_client import get_audit_data

                data = get_audit_data(key)
                if data:
                    try:
                        event = json.loads(data)
                        if event.get("timestamp", "") < cutoff_timestamp:
                            delete_audit_keys(key)
                            deleted_count += 1
                    except (json.JSONDecodeError, KeyError):
                        pass

            logger.info(f"Cleared {deleted_count} old audit entries")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear old audits: {e}")
            return 0
