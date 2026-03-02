"""Google Calendar tool definitions and handlers."""

import json

from nemo.services.calendar_service import CalendarService

_service = None


def _get_service():
    global _service
    if _service is None:
        _service = CalendarService()
    return _service


CALENDAR_TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Get upcoming events from the user's Google Calendar. Use this to check schedule, find meetings, see what's coming up today or this week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Start of time range in ISO 8601 format (e.g., '2025-01-15T09:00:00-08:00'). Defaults to now.",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range in ISO 8601 format. Defaults to 7 days from now.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of events to return. Default: 10",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new event on the user's Google Calendar. Use for scheduling meetings, kids' activities, reminders, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title/summary",
                },
                "start_time": {
                    "type": "string",
                    "description": "Event start time in ISO 8601 format (e.g., '2025-01-15T09:00:00')",
                },
                "end_time": {
                    "type": "string",
                    "description": "Event end time in ISO 8601 format",
                },
                "description": {
                    "type": "string",
                    "description": "Event description. Optional.",
                },
                "location": {
                    "type": "string",
                    "description": "Event location. Optional.",
                },
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "name": "find_free_time",
        "description": "Find available free time slots on a specific date. Useful for scheduling new meetings or activities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to check in YYYY-MM-DD format",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Minimum slot duration in minutes. Default: 30",
                },
                "work_hours_only": {
                    "type": "boolean",
                    "description": "Only check 9am-5pm. Default: true",
                },
            },
            "required": ["date"],
        },
    },
]


def handle_get_events(input_data: dict) -> str:
    try:
        service = _get_service()
    except Exception as e:
        return f"Calendar unavailable: {e}"
    events = service.get_events(
        time_min=input_data.get("time_min"),
        time_max=input_data.get("time_max"),
        max_results=input_data.get("max_results", 10),
    )
    if not events:
        return "No events found in the specified time range."
    return json.dumps(events, indent=2)


def handle_create_event(input_data: dict) -> str:
    try:
        service = _get_service()
    except Exception as e:
        return f"Calendar unavailable: {e}"
    event = service.create_event(
        summary=input_data["summary"],
        start_time=input_data["start_time"],
        end_time=input_data["end_time"],
        description=input_data.get("description"),
        location=input_data.get("location"),
    )
    return f"Event created: {event['summary']} at {event['start']}. Link: {event.get('htmlLink', 'N/A')}"


def handle_find_free_time(input_data: dict) -> str:
    try:
        service = _get_service()
    except Exception as e:
        return f"Calendar unavailable: {e}"
    slots = service.find_free_time(
        date=input_data["date"],
        duration_minutes=input_data.get("duration_minutes", 30),
        work_hours_only=input_data.get("work_hours_only", True),
    )
    if not slots:
        return "No free time slots found for the specified criteria."
    return "Available slots:\n" + "\n".join(
        f"  {s['start']} - {s['end']}" for s in slots
    )
