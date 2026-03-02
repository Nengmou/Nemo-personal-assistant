"""Tool registry: aggregates all tool definitions and provides dispatch."""

import logging
import os

from nemo import config
from nemo.tools.task_tool import (
    TASK_TOOLS,
    handle_complete_task,
    handle_create_task,
    handle_delete_task,
    handle_list_tasks,
)
from nemo.tools.web_search import (
    SEARCH_TOOLS,
    handle_web_search,
)

logger = logging.getLogger(__name__)

# All tool definitions for the Claude API
TOOL_DEFINITIONS = TASK_TOOLS + SEARCH_TOOLS

# Map tool names to handler functions
_HANDLERS = {
    "create_task": handle_create_task,
    "list_tasks": handle_list_tasks,
    "complete_task": handle_complete_task,
    "delete_task": handle_delete_task,
    "web_search": handle_web_search,
}

# Only register calendar tools if Google credentials file exists
if os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
    from nemo.tools.calendar_tool import (
        CALENDAR_TOOLS,
        handle_create_event,
        handle_find_free_time,
        handle_get_events,
    )
    TOOL_DEFINITIONS = CALENDAR_TOOLS + TOOL_DEFINITIONS
    _HANDLERS.update({
        "get_calendar_events": handle_get_events,
        "create_calendar_event": handle_create_event,
        "find_free_time": handle_find_free_time,
    })
else:
    logger.warning(
        "Google credentials not found at %s — calendar tools disabled.",
        config.GOOGLE_CREDENTIALS_PATH,
    )


def execute_tool(name: str, input_data: dict) -> str:
    """Look up and execute a tool by name. Returns result as string."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    return handler(input_data)
