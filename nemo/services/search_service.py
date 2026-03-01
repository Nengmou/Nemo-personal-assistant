"""Tavily web search service."""

from tavily import TavilyClient

from nemo import config


class SearchService:
    def __init__(self):
        self.client = TavilyClient(api_key=config.TAVILY_API_KEY)

    def search(self, query: str, max_results: int = 5,
               include_answer: bool = True) -> dict:
        """Search the web using Tavily API."""
        response = self.client.search(
            query=query,
            max_results=max_results,
            include_answer="basic" if include_answer else False,
            search_depth="basic",
        )

        results = {
            "answer": response.get("answer", ""),
            "results": [],
        }
        for r in response.get("results", []):
            results["results"].append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:500],
            })
        return results
