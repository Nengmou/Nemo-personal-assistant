"""Task management tool definitions and handlers."""

import json

from nemo.db.models import TaskModel

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = TaskModel()
    return _model


TASK_TOOLS = [
    {
        "name": "create_task",
        "description": "Create a new task/to-do item. Use this when the user mentions something they need to do, or explicitly asks to create a task. Supports work, personal, and kids categories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The task title/description",
                },
                "category": {
                    "type": "string",
                    "enum": ["work", "personal", "kids"],
                    "description": "Task category. Default: work",
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Task priority. Default: medium",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format. Optional.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks/to-do items. Can filter by category (work/personal/kids) and status (pending/completed). Returns tasks sorted by priority then creation date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["work", "personal", "kids"],
                    "description": "Filter by category. Omit to show all categories.",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "completed"],
                    "description": "Filter by status. Default: pending",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of tasks to return. Default: 20",
                },
            },
            "required": [],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The ID of the task to complete",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task permanently by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The ID of the task to delete",
                },
            },
            "required": ["task_id"],
        },
    },
]


def handle_create_task(input_data: dict) -> str:
    model = _get_model()
    task = model.create(
        title=input_data["title"],
        category=input_data.get("category", "work"),
        priority=input_data.get("priority", "medium"),
        due_date=input_data.get("due_date"),
    )
    return f"Task created (ID: {task['id']}): {task['title']} [{task['category']}/{task['priority']}]"


def handle_list_tasks(input_data: dict) -> str:
    model = _get_model()
    tasks = model.list_tasks(
        category=input_data.get("category"),
        status=input_data.get("status", "pending"),
        limit=input_data.get("limit", 20),
    )
    if not tasks:
        return "No tasks found matching the criteria."
    lines = []
    for t in tasks:
        due = f" (due: {t['due_date']})" if t.get("due_date") else ""
        lines.append(f"  [{t['id']}] {t['title']} — {t['category']}/{t['priority']}{due}")
    return f"Tasks ({len(tasks)}):\n" + "\n".join(lines)


def handle_complete_task(input_data: dict) -> str:
    model = _get_model()
    success = model.complete(input_data["task_id"])
    if success:
        return f"Task {input_data['task_id']} marked as completed."
    return f"Task {input_data['task_id']} not found or already completed."


def handle_delete_task(input_data: dict) -> str:
    model = _get_model()
    success = model.delete(input_data["task_id"])
    if success:
        return f"Task {input_data['task_id']} deleted."
    return f"Task {input_data['task_id']} not found."
