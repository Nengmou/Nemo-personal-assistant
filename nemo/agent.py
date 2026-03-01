"""Core agent: Claude API integration with tool-use dispatch loop."""

import logging

import anthropic

from nemo import config
from nemo.system_prompt import get_system_prompt
from nemo.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def process_message(conversation_history: list[dict]) -> str:
    """
    Send conversation to Claude with tools. Run the tool-use loop.
    Return the final text response.
    """
    messages = list(conversation_history)

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=get_system_prompt(),
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )

    iterations = 0
    while response.stop_reason == "tool_use" and iterations < config.MAX_TOOL_ITERATIONS:
        iterations += 1
        logger.info(f"Tool loop iteration {iterations}")

        # Append assistant response (contains tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        # Execute all tool calls in this response
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info(f"Calling tool: {block.name} with input: {block.input}")
                try:
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
                except Exception as e:
                    logger.exception(f"Tool {block.name} failed")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

        # Send tool results back to Claude
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=get_system_prompt(),
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

    # Extract final text from response
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)

    return "\n".join(text_parts) if text_parts else "I processed your request but have nothing to add."
