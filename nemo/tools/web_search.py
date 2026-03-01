"""Web search tool definition and handler."""

import json

from nemo.services.search_service import SearchService

_service = None


def _get_service():
    global _service
    if _service is None:
        _service = SearchService()
    return _service


SEARCH_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information, news, articles, and facts. Use this for AI/ML industry news, parenting advice, career tips, and any information that may be more current than your training data. Returns search results with snippets and an AI-generated answer summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default: 5",
                },
                "include_answer": {
                    "type": "boolean",
                    "description": "Whether to include an AI-generated answer summary. Default: true",
                },
            },
            "required": ["query"],
        },
    },
]


def handle_web_search(input_data: dict) -> str:
    service = _get_service()
    results = service.search(
        query=input_data["query"],
        max_results=input_data.get("max_results", 5),
        include_answer=input_data.get("include_answer", True),
    )
    return json.dumps(results, indent=2)
