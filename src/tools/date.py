from crewai.tools import BaseTool
from core.settings import get_settings
from core.audit import audit_tool_call
from datetime import datetime


settings = get_settings()


class DateTool(BaseTool):
    name: str = "DateTool"
    description: str = "Returns the current timestamp."

    @audit_tool_call(tool_name="DateTool")
    def _run(self) -> str:
        """
        Return the current date and time in ISO format.

        Args:
            query: Optional input (ignored)

        Returns:
            Current date and time as a string
        """
        return datetime.now().isoformat()
