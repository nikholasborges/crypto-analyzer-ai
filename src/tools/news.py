import requests
from crewai.tools import BaseTool
from core.settings import get_settings
from core.audit import audit_tool_call


settings = get_settings()


class NewsSearchTool(BaseTool):
    name: str = "SearchTool"
    description: str = "Searches for the latest news on a specific topic."

    @audit_tool_call(tool_name="SearchTool")
    def _run(self, topic: str) -> str:
        """
        Search for news articles on a given topic using mediastack API.

        Args:
            topic: The topic to search for (e.g., "Bitcoin", "Ethereum")

        Returns:
            A formatted string with search results
        """
        # Using mediastack API for news search
        api_key = settings.mediastack_api_key

        # Validate API key
        if not api_key or api_key == "your_mediastack_api_key_here":
            raise ValueError(
                "Invalid mediastack API key. Please update MEDIASTACK_API_KEY in .env"
            )

        url = "http://api.mediastack.com/v1/news"
        params = {
            "access_key": api_key,
            "keywords": topic,
            "limit": 10,
            "sort": "published_desc",
            "languages": "en",
        }

        response = requests.get(url, params=params, timeout=5)

        # Handle errors
        if response.status_code == 401:
            raise ValueError(
                "Mediastack API Key is invalid or expired. Please check your MEDIASTACK_API_KEY in .env"
            )
        elif response.status_code != 200:
            raise requests.RequestException(
                f"Failed to fetch news (Status {response.status_code}): {response.text}"
            )

        data = response.json()

        if not data.get("success"):
            error_info = data.get("error", {}).get("info", "Unknown error")
            raise ValueError(f"API Error: {error_info}")

        articles = data.get("data", [])

        if not articles:
            return f"No articles found for '{topic}'"

        # Format results
        results = f"Found {len(articles)} articles about '{topic}':\n\n"
        for i, article in enumerate(articles, 1):
            results += f"{i}. {article['title']}\n"
            results += f"   Source: {article['source']}\n"
            results += f"   Published: {article['published_at']}\n"
            results += f"   URL: {article['url']}\n\n"

        return results
