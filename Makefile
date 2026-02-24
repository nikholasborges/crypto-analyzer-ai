run-cli:
	python -m app.cli $(args)

# Docker targets for Redis management
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f redis

docker-health:
	redis-cli ping

docker-clean:
	docker-compose down -v

docker-restart:
	docker-compose restart redis

# Redis audit utilities
audit-cleanup:
	python -c "from core.audit_queries import cleanup_old_audits; deleted = cleanup_old_audits(); print(f'Deleted {deleted} old audit records')"

audit-recent:
	python -c "from core.audit_queries import get_recent_executions; execs = get_recent_executions(5); import json; print(json.dumps([e.get('metadata', {}) for e in execs], indent=2, default=str))"

audit-redis:
	redis-cli

# Development
dev-setup:
	docker-compose up -d
	uv sync

dev-run:
	python -m app.cli --research $(topic)

.PHONY: run-cli docker-up docker-down docker-logs docker-health docker-clean docker-restart audit-cleanup audit-recent audit-redis dev-setup dev-run
