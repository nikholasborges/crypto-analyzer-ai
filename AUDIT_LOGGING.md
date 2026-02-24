# Audit Logging System Documentation

## Overview

The audit logging system captures every interaction within the CrewAI multi-agent system, including:
- Crew execution lifecycle (start/end)
- Agent steps and reasoning
- Tool calls and API responses
- Task completions
- Errors and exceptions

All audit data is persisted to Redis with automatic TTL-based cleanup based on retention policy.

## Architecture

### Components

1. **Redis Storage** (`core/redis_client.py`)
   - Connection pooling with TCP keepalive
   - Atomic operations (set, get, delete)
   - Pattern-based key searches
   - Automatic TTL handling

2. **Data Models** (`core/audit_models.py`)
   - `EventType` enum: 8 event types for different aspects of execution
   - Pydantic models for type-safe serialization
   - Automatic UUID generation for event tracking
   - UTC datetime formatting

3. **Logger** (`core/audit_logger.py`)
   - Centralized audit operations
   - Event filtering based on `audit_enabled` setting
   - Redis persistence with TTL
   - Query utilities for execution history

4. **Query Utilities** (`core/audit_queries.py`)
   - Search and filter audit events
   - Performance analysis (tool metrics, agent activity)
   - Data export as JSON
   - Cleanup of old records

5. **Integration Points**
   - `src/crew/research.py`: Crew execution wrapper with callbacks
   - `src/tools/news.py`: Tool-level audit logging
   - `src/cli.py`: Error handling and top-level audit

## Event Types

### CREW_START
Logged when crew execution begins.

**Metadata:**
- `topic`: Research topic
- `agent_names`: List of agent names
- `task_count`: Number of tasks
- `timestamp`: Execution start time

### CREW_END
Logged when crew execution completes (success or failure).

**Metadata:**
- `duration_seconds`: Execution duration
- `success`: Boolean success indicator
- `error_message`: Error message if failed
- `timestamp`: Execution end time

### AGENT_STEP
Logged for each agent reasoning step.

**Metadata:**
- `agent_name`: Name of the agent
- `step_number`: Step sequence number
- `reasoning`: Agent's reasoning/thought
- `tool_used`: Tool selected for this step
- `tool_input`: Input parameters for the tool
- `token_usage`: Token consumption metrics
- `duration_seconds`: Time taken for step

### TASK_START
Logged when a task begins execution.

**Metadata:**
- `task_name`: Name of the task
- `agent_name`: Assigned agent
- `description`: Task description
- `timestamp`: Task start time

### TASK_END
Logged when a task completes.

**Metadata:**
- `task_name`: Name of the task
- `agent_name`: Executing agent
- `output_preview`: First 500 characters of output
- `full_output_length`: Total length of output
- `token_usage`: Token metrics
- `duration_seconds`: Execution time
- `success`: Boolean success indicator

### TOOL_CALL
Logged for every tool invocation.

**Metadata:**
- `tool_name`: Name of the tool
- `tool_input`: Input parameters (dict)
- `tool_output`: Tool output/result
- `status_code`: HTTP status or error code
- `duration_seconds`: Execution time
- `error_message`: Error message if failed
- `success`: Boolean success indicator

### TOOL_ERROR
Logged when a tool encounters an error.

**Metadata:**
- `tool_name`: Tool that failed
- `error_type`: Exception type
- `error_message`: Error description
- `timestamp`: When error occurred

### CREW_ERROR
Logged when crew execution encounters an error.

**Metadata:**
- `error_type`: Exception type
- `error_message`: Error description
- `error_traceback`: Full stack trace
- `context`: Additional context dict
- `recoverable`: Whether error is recoverable

## Redis Key Structure

Keys follow this pattern:
```
audit:{execution_id}:{event_type}:{event_id}
```

Example:
```
audit:550e8400-e29b-41d4-a716-446655440000:TOOL_CALL:9a3d7c3b-28dd-4e2f-8c4a-9d8e9f4d3c5b
```

### TTL Configuration

- Default retention: 30 days (configurable via `AUDIT_RETENTION_DAYS`)
- Can be overridden per-execution
- Automatic cleanup via `cleanup_old_audits()`

## Configuration

### Environment Variables

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# Audit Configuration
AUDIT_ENABLED=true              # Toggle audit logging on/off
AUDIT_RETENTION_DAYS=30         # How long to keep audit records
```

### Settings

Located in `core/settings.py`:
```python
audit_enabled: bool = True
audit_retention_days: int = 30
redis_host: str = "localhost"
redis_port: int = 6379
redis_db: int = 0
redis_url: str = "redis://localhost:6379/0"
```

## Usage Examples

### Basic Execution with Audit Logging

```python
from src.crew.research import ResearchCrew

# Create and run crew with automatic audit logging
crew = ResearchCrew()
result = crew.kickoff_for_research({"topic": "Bitcoin analysis"})
```

### Query Execution History

```python
from core.audit_queries import (
    get_execution_summary,
    get_execution_history,
    search_events,
    get_failed_tool_calls,
)

# Get execution summary with metrics
summary = get_execution_summary("550e8400-e29b-41d4-a716-446655440000")
print(f"Duration: {summary['duration_seconds']}s")
print(f"Tools used: {summary['tools_used']}")
print(f"Success: {summary['end_event']['metadata']['success']}")

# Get detailed event history
history = get_execution_history("550e8400-e29b-41d4-a716-446655440000")

# Search for specific events
tool_calls = search_events(
    execution_id="550e8400-e29b-41d4-a716-446655440000",
    event_type="TOOL_CALL",
    tool_name="SearchTool"
)

# Get failed tool calls
failures = get_failed_tool_calls("550e8400-e29b-41d4-a716-446655440000")
```

### Performance Analysis

```python
from core.audit_queries import (
    get_tool_performance,
    get_agent_activity,
)

# Analyze tool performance
perf = get_tool_performance("550e8400-e29b-41d4-a716-446655440000")
print(f"Total tool calls: {perf['total_tool_calls']}")
for tool, metrics in perf['tools'].items():
    print(f"{tool}: {metrics['count']} calls, avg {metrics['avg_duration_seconds']}s")

# Analyze agent activity
activity = get_agent_activity("550e8400-e29b-41d4-a716-446655440000")
for agent, metrics in activity['agents'].items():
    print(f"{agent}: {metrics['step_count']} steps, tools: {metrics['tools_used']}")
```

### Export and Cleanup

```python
from core.audit_queries import (
    export_execution_as_json,
    cleanup_old_audits,
)

# Export execution as JSON
json_export = export_execution_as_json("550e8400-e29b-41d4-a716-446655440000", pretty=True)
with open("execution_audit.json", "w") as f:
    f.write(json_export)

# Cleanup old records
deleted = cleanup_old_audits(days=30)
print(f"Deleted {deleted} old audit records")
```

### Recent Executions

```python
from core.audit_queries import get_recent_executions

# Get last 5 executions
recent = get_recent_executions(limit=5)
for exec_event in recent:
    meta = exec_event.get('metadata', {})
    print(f"Topic: {meta.get('topic')}")
    print(f"Timestamp: {meta.get('timestamp')}")
    print(f"Agents: {meta.get('agent_names')}")
```

## Redis Commands for Manual Inspection

### View all audit keys
```bash
redis-cli keys "audit:*"
```

### Get a specific event
```bash
redis-cli HGETALL "audit:550e8400-e29b-41d4-a716-446655440000:TOOL_CALL:9a3d7c3b-28dd-4e2f-8c4a-9d8e9f4d3c5b"
```

### Search for tool calls
```bash
redis-cli keys "audit:*:TOOL_CALL:*"
```

### Check expiration
```bash
redis-cli TTL "audit:550e8400-e29b-41d4-a716-446655440000:CREW_END:*"
```

### Manual cleanup
```bash
redis-cli DEL $(redis-cli keys "audit:*" | head -10)
```

## Docker Setup

### Start Redis

```bash
# Start in background
docker-compose up -d

# Verify health
redis-cli ping
# Output: PONG

# View logs
docker-compose logs redis

# Stop
docker-compose down
```

### Access Redis

```bash
# Via CLI
redis-cli

# Via Python
from core.redis_client import get_redis_client
client = get_redis_client()
client.set("test", "value")
print(client.get("test"))  # b'value'
```

## Error Handling

The audit system is designed to be non-intrusive:
- All audit operations are wrapped in try-except blocks
- Failures in audit logging don't affect crew execution
- Graceful degradation if Redis is unavailable
- Settings.audit_enabled can disable logging entirely

```python
try:
    audit_logger.log_tool_call(...)
except Exception:
    pass  # Audit failure doesn't break execution
```

## Debugging

### Check if audit logging is working

```python
from core.audit_logger import AuditLogger
from core.settings import get_settings

settings = get_settings()
print(f"Audit enabled: {settings.audit_enabled}")

# Try logging a test event
logger = AuditLogger()
exec_id = logger.start_execution("test", ["test-agent"], 1)
print(f"Execution ID: {exec_id}")

# Check Redis
from core.redis_client import get_redis_client
client = get_redis_client()
keys = client.keys(f"audit:{exec_id}:*")
print(f"Events logged: {len(keys)}")
```

### Enable verbose logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("core.audit_logger")
logger.setLevel(logging.DEBUG)
```

### Monitor Redis in real-time

```bash
# Watch Redis keys in real-time
redis-cli MONITOR
```

## Performance Considerations

1. **Redis Memory**: Each event stores metadata as JSON
   - Typical event size: 500-2000 bytes
   - 30-day retention with daily executions: ~1-5 MB

2. **Network**: Local Redis connections highly efficient
   - Minimal latency impact
   - Batching operations when possible

3. **TTL Cleanup**: Automatic via Redis expiration
   - No manual maintenance needed
   - Consider running `cleanup_old_audits()` periodically

## Troubleshooting

### Connection Errors
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```
- Ensure Redis is running: `docker-compose up -d`
- Check Redis health: `redis-cli ping`

### Memory Issues
```bash
# Check Redis memory usage
redis-cli INFO memory

# Clear old audit data
python -c "from core.audit_queries import cleanup_old_audits; print(cleanup_old_audits())"
```

### Missing Execution ID in Tools
- Ensure `kickoff_for_research()` is used instead of direct `crew().kickoff()`
- Check that `audit_logger.current_execution_id` is set before calling tools

## Future Enhancements

- [ ] Web dashboard for audit visualiza​tion
- [ ] Alert system for failed executions
- [ ] Audit log aggregation for multiple crew instances
- [ ] Analytics and reporting
- [ ] Webhook integration for external monitoring
- [ ] Sampling strategy for high-frequency executions
