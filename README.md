# Crypto Analyzer AI

A multi-agent AI system that researches cryptocurrency topics and generates comprehensive analysis reports. Powered by CrewAI, Google Gemini 3 Flash LLM, and mediastack News API with comprehensive audit logging.

## Features

🤖 **Multi-Agent Architecture**
- Researcher agent: Gathers and synthesizes information
- Writer agent: Produces comprehensive analysis reports

🔍 **Real-time News Integration**
- Powered by mediastack API for current news
- Structured search and retrieval

🧠 **Advanced LLM**
- Google Gemini 3 Flash for fast, efficient processing
- Prompt-based agent coordination

📊 **Comprehensive Audit Logging**
- Redis-based persistence of all interactions
- Event tracking: crew execution, agent steps, tool calls
- Performance metrics and analysis
- 30-day retention with configurable TTL

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- UV package manager
- API Keys:
  - Google Gemini API key
  - mediastack API key

### Installation

1. **Clone and setup**
```bash
git clone <repo>
cd crypto-analyzer-ai
make dev-setup  # Starts Redis and installs dependencies
```

2. **Configure environment**
```bash
cp .env.example .env  # If provided, or create from template
```

Add your API keys:
```env
GOOGLE_API_KEY=your_gemini_api_key
MEDIASTACK_API_KEY=your_mediastack_api_key
AUDIT_ENABLED=true
AUDIT_RETENTION_DAYS=30
```

3. **Verify Redis is running**
```bash
make docker-health  # Should respond with PONG
```

### Running the Analyzer

```bash
# Simple usage
python -m src.cli --research "Bitcoin market trends in 2024"

# Via Makefile
make dev-run topic="Ethereum competitors"

# Direct CLI
python -m src.cli --research "DeFi protocols and risks"
```

## Architecture

### Core Components

```
crypto-analyzer-ai/
├── config/
│   ├── agents.yaml          # Agent configurations (roles, goals, backstory)
│   └── tasks.yaml           # Task definitions
├── core/
│   ├── settings.py          # Pydantic configuration management
│   ├── logging.py           # Application logging
│   ├── redis_client.py      # Redis connection pooling
│   ├── audit_logger.py      # Central audit logging
│   ├── audit_models.py      # Pydantic audit event models
│   └── audit_queries.py     # Audit data query utilities
├── src/
│   ├── cli.py               # Command-line interface
│   ├── crew/
│   │   └── research.py      # Multi-agent crew definition
│   └── tools/
│       └── news.py          # NewsSearchTool for mediastack API
├── docker-compose.yml       # Redis service definition
├── pyproject.toml          # Python dependencies
├── Makefile                # Development commands
└── AUDIT_LOGGING.md        # Detailed audit logging documentation
```

### Execution Flow

```
1. CLI Input (topic)
   ↓
2. ResearchCrew.kickoff_for_research()
   ├─ audit_logger.start_execution() [Log crew start]
   ├─ Crew Execution (sequential process)
   │  ├─ Researcher Agent
   │  │  ├─ Reasoning step
   │  │  └─ NewsSearchTool call
   │  │     ├─ mediastack API request
   │  │     └─ audit_logger.log_tool_call() [Log tool usage]
   │  ├─ Research Task Completion
   │  │  └─ audit_logger.log_task_completion() [Log task output]
   │  └─ Writer Agent
   │     └─ Writer Task Completion
   ├─ audit_logger.end_execution() [Log crew end]
   ├─ audit_logger.log_error() [Log any errors]
   ↓
3. Output Report
```

## Audit Logging System

### What's Logged

Every interaction is captured with timestamps:

- **Crew Execution**: Start/end times, topic, success/failure
- **Agent Steps**: Reasoning process, tools selected, token usage
- **Tool Calls**: API requests, responses, status codes, duration
- **Task Completion**: Output summary, token metrics, execution time
- **Errors**: Full exceptions, tracebacks, context information

### Event Types

```
CREW_START    → Execution begins
CREW_END      → Execution completes
AGENT_STEP    → Agent reasoning step
TASK_START    → Task begins
TASK_END      → Task completes
TOOL_CALL     → Tool invocation
TOOL_ERROR    → Tool failed
CREW_ERROR    → Execution failed
```

### Querying Audit Data

```python
from core.audit_queries import (
    get_execution_summary,      # Overview of execution
    get_execution_history,      # All events in order
    search_events,              # Filter by type, tool, agent
    get_tool_performance,       # Tool usage metrics
    get_agent_activity,         # Agent step analysis
    get_failed_tool_calls,      # Troubleshoot failures
    export_execution_as_json,   # Export audit trail
)

# Example: Analyze an execution
summary = get_execution_summary(execution_id)
print(f"Duration: {summary['duration_seconds']}s")
print(f"Tools used: {summary['tools_used']}")
print(f"Success: {summary['end_event']['metadata']['success']}")

# Get tool metrics
perf = get_tool_performance(execution_id)
for tool, metrics in perf['tools'].items():
    print(f"{tool}: {metrics['count']} calls, avg {metrics['avg_duration_seconds']}s")
```

### Redis Management

```bash
# Start Redis
make docker-up

# Check Redis health
make docker-health

# View recent executions
make audit-recent

# Cleanup old records
make audit-cleanup

# Direct Redis access
make audit-redis  # Opens redis-cli
```

### Configuration

```env
# Enable/disable audit logging
AUDIT_ENABLED=true

# How long to keep records (days)
AUDIT_RETENTION_DAYS=30

# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0
```

## API Keys Setup

### Google Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create new API key
3. Add to `.env`:
```env
GOOGLE_API_KEY=your_key_here
```

### mediastack API

1. Sign up at [mediastack.com](https://mediastack.com/)
2. Get your free or paid API key
3. Add to `.env`:
```env
MEDIASTACK_API_KEY=your_key_here
```

## Development

### Commands

```bash
# Setup development environment
make dev-setup

# Run analysis
make dev-run topic="topic name"

# Direct CLI
python -m src.cli --research "topic"

# Docker management
make docker-up        # Start Redis
make docker-down      # Stop Redis
make docker-logs      # View Redis logs
make docker-clean     # Remove Redis volume

# Audit utilities
make audit-cleanup    # Delete old records
make audit-recent     # Show recent executions
make audit-redis      # Open redis-cli
```

### Project Structure Best Practices

- **YAML configs** for agent/task definitions
- **Pydantic models** for type-safe configuration
- **Redis connection pooling** for efficiency
- **Try-except wrapping** for non-intrusive audit logging
- **Audit_enabled flag** for easy enable/disable

## Troubleshooting

### Redis Connection Error
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```
**Solution**: Start Redis with `make docker-up`

### Invalid API Key Error
```
ERROR: Mediastack API Key is invalid or expired
```
**Solution**: Verify your MEDIASTACK_API_KEY in `.env` and restart

### No News Results
```
No articles found for 'topic'
```
**Solution**: Try broader topic terms, mediastack may have limited coverage

### Audit Logging Not Working
**Solution**: 
1. Verify `AUDIT_ENABLED=true` in `.env`
2. Check Redis is running: `make docker-health`
3. View logs: `make docker-logs`

## Performance

### Typical Execution

- **Research phase**: 15-30 seconds (depends on API response)
- **Writing phase**: 10-20 seconds (depends on LLM response)
- **Total**: ~30-50 seconds end-to-end

### Feature Performance Impact

- **Audit logging**: <5% overhead (asynchronous, non-blocking)
- **Tool calls**: Limited by mediastack API latency (~2-3 seconds per request)
- **LLM processing**: Gemini 3 Flash is optimized for speed

### Storage

- **Redis memory**: ~1-5 MB for 30 days of daily executions
- **Automatic cleanup**: Managed by TTL expiration
- **Query speed**: <100ms for execution retrieval

## Documentation

- [AUDIT_LOGGING.md](./AUDIT_LOGGING.md) - Comprehensive audit system documentation
- [config/agents.yaml](./config/agents.yaml) - Agent configurations
- [config/tasks.yaml](./config/tasks.yaml) - Task definitions

## Dependencies

Key libraries:

- **crewai**: Multi-agent orchestration framework
- **langchain-google-genai**: Google Gemini integration
- **pydantic**: Data validation and configuration
- **redis**: Distributed cache/log store
- **requests**: HTTP client for mediastack API

See [pyproject.toml](./pyproject.toml) for complete dependency list.

## Future Enhancements

- [ ] Web dashboard for audit visualization
- [ ] Multiple cryptocurrency analyzer agents
- [ ] Alert system for failed executions
- [ ] Performance optimization caching
- [ ] Webhook integration for notifications
- [ ] Multi-user support with execution isolation

## License

[Your License Here]

## Support

For issues or questions:
1. Check [AUDIT_LOGGING.md](./AUDIT_LOGGING.md) for audit-related questions
2. Review error messages in `logs/app.log`
3. Inspect audit trail with `make audit-recent`

---

**Built with ❤️ using CrewAI, Google Gemini, and Redis**
