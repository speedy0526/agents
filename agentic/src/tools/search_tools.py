"""
Minimal Agent Tools - Search
"""

from .base import BaseTool, ToolResult
import requests
from readability import Document


class SearchGoogleTool(BaseTool):
    """Search using DuckDuckGo (free, no API key)"""

    @property
    def name(self) -> str:
        return "search_google"

    @property
    def description(self) -> str:
        return "Search the web for information"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "number",
                    "description": "Max results (default: 10)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute search"""
        try:
            from ddgs import DDGS

            query = kwargs.get("query", "")
            max_results = kwargs.get("max_results", 10)

            if not query:
                return self.error("Missing query", "Query required")

            with DDGS() as ddgs:
                results = []
                print(f"\n{'=' * 60}")
                for r in ddgs.text(query, max_results=max_results):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")
                        }
                    )

                return self.success(
                    {"query": query, "results": results},
                    f"Found {len(results)} results",
                )

        except Exception as e:
            return self.error(str(e), f"Search failed: {str(e)}")
