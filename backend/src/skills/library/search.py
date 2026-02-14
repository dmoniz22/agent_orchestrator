"""Web search tool using DuckDuckGo."""

from typing import Any
import urllib.parse
import urllib.request
import json

from src.skills.base import (
    BaseTool,
    ToolDangerLevel,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class SearchTool(BaseTool):
    """Tool for searching the web via DuckDuckGo.
    
    Provides web search functionality without requiring API keys.
    Uses DuckDuckGo's instant answer API.
    """
    
    def __init__(self) -> None:
        """Initialize search tool."""
        super().__init__(
            tool_id="search.web",
            name="Web Search",
            description="Search the web for information using DuckDuckGo",
            danger_level=ToolDangerLevel.SAFE,
            timeout_seconds=15
        )
    
    async def execute(
        self,
        query: str,
        num_results: int = 5
    ) -> ToolResult:
        """Execute web search.
        
        Args:
            query: Search query.
            num_results: Number of results to return (max 10).
            
        Returns:
            Tool result with search results.
        """
        logger.info(
            "Searching web",
            tool_id=self.tool_id,
            query=query[:100],
            num_results=num_results
        )
        
        try:
            # Limit results
            num_results = min(num_results, 10)
            
            # Use DuckDuckGo HTML version
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Make request
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            # Execute in thread to not block
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
            )
            
            # Parse results
            results = self._parse_results(response, num_results)
            
            return ToolResult(
                success=True,
                result={
                    "query": query,
                    "results": results,
                    "count": len(results)
                },
                metadata={"source": "duckduckgo"}
            )
            
        except Exception as e:
            logger.error(
                "Search failed",
                tool_id=self.tool_id,
                error=str(e)
            )
            return ToolResult(
                success=False,
                error=f"Search failed: {e}",
                metadata={"query": query}
            )
    
    def _parse_results(self, html: str, limit: int) -> list[dict[str, Any]]:
        """Parse search results from HTML.
        
        Args:
            html: HTML response.
            limit: Maximum number of results.
            
        Returns:
            List of result dictionaries.
        """
        results = []
        
        # Simple parsing - look for result links
        import re
        
        # Find all result blocks
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
        
        links = re.findall(result_pattern, html, re.DOTALL)
        snippets = re.findall(snippet_pattern, html, re.DOTALL)
        
        for i, (href, title) in enumerate(links[:limit]):
            # Clean up title (remove HTML tags)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            
            # Get snippet if available
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            
            results.append({
                "title": title_clean,
                "url": href,
                "snippet": snippet[:200] if snippet else "No description available"
            })
        
        return results
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results to return (max 10)",
                    required=False,
                    default=5
                )
            ]
        )
