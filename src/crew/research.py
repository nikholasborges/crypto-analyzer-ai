from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from core.audit import AuditLogger
from core.settings import get_settings
from src.tools.date import DateTool
from src.tools.duckduckgo import DuckDuckGoSearchTool
from src.tools.markdown_formatter import MarkdownFormatterTool
from src.tools.binance import BinanceMarketTool, BinanceOrderBookTool

audit_logger = AuditLogger()
settings = get_settings()

local_llm = LLM(
    base_url=settings.lm_studio_api_base,
    model="openai/deepseek/deepseek-r1-0528-qwen3-8b",
    api_key="lm-studio",
    temperature=0.1,  # Keep it low for data tasks
    timeout=300,  # Local models can be slow
)


@CrewBase
class ResearchCrew:
    """Research Crew for AI news"""

    # Paths to your YAML files - relative to the crew file location (src/crew/)
    agents_config = "../../config/agents.yaml"
    tasks_config = "../../config/tasks.yaml"

    def __init__(self):
        self._execution_id = None

    @agent
    def crypto_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["crypto_researcher"],
            tools=[
                DateTool(),
                DuckDuckGoSearchTool(),
                BinanceMarketTool(),
                BinanceOrderBookTool(),
            ],
            llm=local_llm,
            verbose=True,
            max_iter=5,
            max_retry_limit=3,
            cache=False,
            respect_context_window=True,
        )

    @agent
    def investment_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["investment_writer"],
            tools=[MarkdownFormatterTool()],
            llm=local_llm,
            verbose=True,
        )

    @task
    def crypto_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["crypto_research_task"],
        )

    @task
    def crypto_reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config["crypto_reporting_task"],
            context=[self.crypto_research_task()],
        )

    @crew
    def crew(self) -> Crew:
        def on_step_callback(step_output) -> None:
            """Callback for each agent step."""
            try:
                step_data = (
                    step_output
                    if isinstance(step_output, dict)
                    else step_output.__dict__
                )
                agent_name = step_data.get("agent", "unknown")
                thought = step_data.get("thought", "")
                action = step_data.get("action", "")

                audit_logger.log_agent_step(
                    execution_id=getattr(self, "_execution_id", "unknown"),
                    agent_name=str(agent_name),
                    step_number=0,  # Would need CrewAI step counter
                    reasoning=str(thought),
                    tool_used=str(action) if action else None,
                )
            except Exception:
                pass  # Don't break crew execution if audit fails

        def on_task_callback(task_output) -> None:
            """Callback for each task completion."""
            try:
                task_name = (
                    task_output.description
                    if hasattr(task_output, "description")
                    else str(task_output)
                )
                output = (
                    task_output.raw_output
                    if hasattr(task_output, "raw_output")
                    else str(task_output)
                )

                audit_logger.log_task_completion(
                    execution_id=getattr(self, "_execution_id", "unknown"),
                    task_name=task_name,
                    agent_name="unknown",
                    output=output,
                    success=True,
                )
            except Exception:
                pass  # Don't break crew execution if audit fails

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            task_callback=lambda output: print(
                f"Task finished with: {output.raw[:50]}..."
            ),
            step_callback=on_step_callback,
            output_log_file="logs/crew_execution.json",
        )

    def start(self, inputs: dict) -> str:
        """
        Execute the research crew with audit logging.

        Args:
            inputs: Dictionary with 'topic' key for research topic

        Returns:
            The crew output/result
        """
        import time

        start_time = time.time()

        # Log execution start
        topic = inputs.get("topic", "unknown")
        agent_names = ["researcher", "writer"]
        task_count = 2

        self._execution_id = audit_logger.start_execution(
            topic=topic, agent_names=agent_names, task_count=task_count
        )

        try:
            # Execute the crew
            result = self.crew().kickoff(inputs)

            # Log execution end (success)
            duration = time.time() - start_time
            audit_logger.end_execution(
                execution_id=self._execution_id,
                success=True,
                error_message=None,
                duration_seconds=duration,
            )

            return result

        except Exception as e:
            # Log execution end (failure)
            duration = time.time() - start_time
            audit_logger.end_execution(
                execution_id=self._execution_id,
                success=False,
                error_message=str(e),
                duration_seconds=duration,
            )

            # Log the exception
            import traceback

            audit_logger.log_error(
                execution_id=self._execution_id,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=traceback.format_exc(),
                context={"topic": topic},
                recoverable=False,
            )

            raise
