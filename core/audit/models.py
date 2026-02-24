"""Pydantic models for audit events in the multi-agent system."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of audit events."""

    CREW_START = "crew_start"
    CREW_END = "crew_end"
    AGENT_STEP = "agent_step"
    TASK_START = "task_start"
    TASK_END = "task_end"
    TOOL_CALL = "tool_call"
    TOOL_ERROR = "tool_error"
    CREW_ERROR = "crew_error"


class AuditEvent(BaseModel):
    """Base audit event model."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event ID"
    )
    event_type: EventType = Field(description="Type of audit event")
    execution_id: str = Field(
        description="ID linking all events from a single crew execution"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )

    class Config:
        use_enum_values = True


class CrewExecution(AuditEvent):
    """Crew execution tracking."""

    event_type: EventType = EventType.CREW_START
    topic: str = Field(description="Research topic or input")
    agent_names: list[str] = Field(
        default_factory=list, description="Agents in the crew"
    )
    task_count: int = Field(description="Number of tasks")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


class AgentStep(AuditEvent):
    """Agent step during execution."""

    event_type: EventType = EventType.AGENT_STEP
    agent_name: str = Field(description="Name of the agent")
    step_number: int = Field(description="Step number in agent's execution")
    reasoning: str = Field(description="Agent's reasoning for this step")
    tool_used: Optional[str] = Field(None, description="Tool name if used")
    tool_input: Optional[dict[str, Any]] = Field(None, description="Input to the tool")
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="Token usage if available"
    )
    duration_seconds: Optional[float] = None


class ToolCall(AuditEvent):
    """Tool call tracking."""

    event_type: EventType = EventType.TOOL_CALL
    tool_name: str = Field(description="Name of the tool called")
    tool_input: dict[str, Any] = Field(description="Input parameters to the tool")
    tool_output: Optional[str] = Field(None, description="Output from the tool")
    status_code: Optional[int] = Field(
        None, description="HTTP status code if applicable"
    )
    duration_seconds: float = Field(description="Tool execution duration")
    error_message: Optional[str] = Field(None, description="Error if tool call failed")
    success: bool = Field(description="Whether tool call succeeded")


class TaskCompletion(AuditEvent):
    """Task completion tracking."""

    event_type: EventType = EventType.TASK_END
    task_name: str = Field(description="Name of the completed task")
    agent_name: str = Field(description="Agent that executed the task")
    output_preview: str = Field(description="Preview of task output (first 500 chars)")
    full_output_length: int = Field(description="Length of full output")
    token_usage: dict[str, int] = Field(default_factory=dict, description="Token usage")
    duration_seconds: float = Field(description="Task execution duration")
    success: bool = Field(description="Whether task succeeded")
    error_message: Optional[str] = Field(None, description="Error if task failed")


class ExecutionError(AuditEvent):
    """Error during execution."""

    event_type: EventType = EventType.CREW_ERROR
    error_type: str = Field(description="Type of error (e.g., ValueError, APIError)")
    error_message: str = Field(description="Error message")
    error_traceback: Optional[str] = Field(None, description="Full traceback")
    context: Optional[dict[str, Any]] = Field(
        None, description="Context of error (agent, task, tool)"
    )
    recoverable: bool = Field(False, description="Whether error was recoverable")
