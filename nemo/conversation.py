"""Per-channel conversation history management."""

from nemo import config

_store: dict[str, list[dict]] = {}


def get_history(channel_id: str) -> list[dict]:
    """Return the conversation history for a channel."""
    return list(_store.get(channel_id, []))


def add_user_message(channel_id: str, text: str) -> None:
    """Append a user message and trim if needed."""
    if channel_id not in _store:
        _store[channel_id] = []
    _store[channel_id].append({"role": "user", "content": text})
    _trim(channel_id)


def add_assistant_message(channel_id: str, text: str) -> None:
    """Append the assistant's final text response and trim if needed."""
    if channel_id not in _store:
        _store[channel_id] = []
    _store[channel_id].append({"role": "assistant", "content": text})
    _trim(channel_id)


def _trim(channel_id: str) -> None:
    """Keep only the most recent messages within the configured limit."""
    max_len = config.MAX_CONVERSATION_HISTORY
    history = _store[channel_id]
    if len(history) > max_len:
        _store[channel_id] = history[-max_len:]
