from crewai.tools import BaseTool
from core.audit import audit_tool_call
from langchain_community.tools import DuckDuckGoSearchResults


class DuckDuckGoSearchTool(BaseTool):
    name: str = "SearchTool"  # Keep this name to match your agents.yaml config
    description: str = (
        "Search the internet for the latest information on a topic using DuckDuckGo."
    )

    @audit_tool_call(tool_name="DuckDuckGoSearchTool")
    def _run(self, query: str) -> str:
        try:
            # We use DuckDuckGoSearchResults to get links and snippets
            # rather than just a text blob.
            search = DuckDuckGoSearchResults(num_results=5)
            results = search.run(query)

            # DuckDuckGoSearchResults typically returns a formatted string.
            # If it's empty, we handle it gracefully.
            if not results or "No results" in results:
                return "No results found for that query."

            return results

        except Exception as e:
            return f"Error during search: {str(e)}"
