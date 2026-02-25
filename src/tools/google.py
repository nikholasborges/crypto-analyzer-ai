from crewai.tools import BaseTool
from core.settings import get_settings
from core.audit import audit_tool_call
from googleapiclient.discovery import build


settings = get_settings()


class GoogleSearchTool(BaseTool):
    name: str = "SearchTool"  # Keep this name to match your existing config
    description: str = "Search the internet for the latest information on a topic."

    @audit_tool_call(tool_name="GoogleSearchTool")
    def _run(self, query: str) -> str:
        try:
            service = build("customsearch", "v1", developerKey=settings.google_api_key)
            res = (
                service.cse()
                .list(q=query, cx=settings.google_search_engine_id, num=5)
                .execute()
            )

            results = res.get("items", [])
            output = []
            for item in results:
                output.append(
                    f"Title: {item['title']}\nLink: {item['link']}\nSnippet: {item['snippet']}\n---"
                )

            return "\n".join(output) if output else "No results found."
        except Exception as e:
            if "403" in str(e):
                return (
                    f"Google Search API is not enabled in the Cloud Console. Please enable it."
                    f"Error: {str(e)}"
                )
            return f"Error during search: {str(e)}"
