"""Decorators for audit logging of tools and functions."""

import time
import traceback
from functools import wraps
from typing import Any, Callable

from core.audit.logger import AuditLogger


def audit_tool_call(tool_name: str | None = None) -> Callable:
    """
    Decorator to automatically audit tool calls.

    Logs tool invocation, execution time, success/failure, and any errors.
    Requires audit_logger.current_execution_id to be set.

    Args:
        tool_name: Name of the tool (defaults to function name)

    Returns:
        Decorated function that logs audit events

    Example:
        @audit_tool_call(tool_name="NewsSearchTool")
        def _run(self, topic: str) -> str:
            # Regular tool logic
            return results
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            audit_logger = AuditLogger()
            execution_id = audit_logger.current_execution_id

            # Extract tool name
            actual_tool_name = tool_name or func.__name__

            # Extract input from args/kwargs
            tool_input = {}
            if args and len(args) > 1:  # First arg is self
                # Get function signature
                import inspect

                sig = inspect.signature(func)
                params = list(sig.parameters.keys())[1:]  # Skip 'self'
                for i, param in enumerate(params):
                    if i < len(args) - 1:
                        tool_input[param] = args[i + 1]
            tool_input.update(kwargs)

            start_time = time.time()

            try:
                # Execute the actual tool
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log successful tool call
                if execution_id:
                    audit_logger.log_tool_call(
                        execution_id=execution_id,
                        tool_name=actual_tool_name,
                        tool_input=tool_input,
                        tool_output=str(result)[:500],  # Preview first 500 chars
                        status_code=200,
                        duration_seconds=duration,
                        error_message=None,
                        success=True,
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                tb = traceback.format_exc()

                # Log tool error
                if execution_id:
                    # Determine if it's an HTTP error
                    status_code = 0
                    if hasattr(e, "response"):
                        status_code = e.response.status_code

                    audit_logger.log_tool_call(
                        execution_id=execution_id,
                        tool_name=actual_tool_name,
                        tool_input=tool_input,
                        tool_output=error_msg,
                        status_code=status_code,
                        duration_seconds=duration,
                        error_message=error_msg,
                        success=False,
                    )

                    # Also log as error for critical issues
                    if not isinstance(e, (ValueError, KeyError)):
                        audit_logger.log_error(
                            execution_id=execution_id,
                            error_type=type(e).__name__,
                            error_message=error_msg,
                            error_traceback=tb,
                            context={"tool": actual_tool_name, "input": tool_input},
                            recoverable=True,
                        )

                raise

        return wrapper

    return decorator


def audit_function(family: str = "function") -> Callable:
    """
    General-purpose decorator for auditing any function execution.

    Logs function start, duration, success/failure.

    Args:
        family: Category for grouping (e.g., "tool", "agent", "task")

    Example:
        @audit_function(family="preprocessing")
        def validate_input(data: dict) -> bool:
            return len(data) > 0
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            audit_logger = AuditLogger()
            execution_id = audit_logger.current_execution_id

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                if execution_id:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.debug(
                        f"[AUDIT] {family}.{func.__name__} completed in {duration:.2f}s"
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                tb = traceback.format_exc()

                if execution_id:
                    audit_logger.log_error(
                        execution_id=execution_id,
                        error_type=type(e).__name__,
                        error_message=error_msg,
                        error_traceback=tb,
                        context={"function": func.__name__, "family": family},
                        recoverable=True,
                    )

                raise

        return wrapper

    return decorator
