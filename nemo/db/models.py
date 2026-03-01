"""Task data model with CRUD operations."""

from datetime import datetime

from nemo.db.database import get_connection


class TaskModel:
    def create(self, title: str, category: str = "work",
               priority: str = "medium", due_date: str = None) -> dict:
        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO tasks (title, category, priority, due_date) VALUES (?, ?, ?, ?)",
            (title, category, priority, due_date),
        )
        conn.commit()
        return self._get_by_id(cursor.lastrowid)

    def list_tasks(self, category: str = None, status: str = "pending",
                   limit: int = 20) -> list[dict]:
        conn = get_connection()
        query = "SELECT * FROM tasks WHERE status = ?"
        params: list = [status]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"
        query += " LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def complete(self, task_id: int) -> bool:
        conn = get_connection()
        cursor = conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ? AND status = 'pending'",
            (datetime.now().isoformat(), task_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete(self, task_id: int) -> bool:
        conn = get_connection()
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0

    def _get_by_id(self, task_id: int) -> dict | None:
        conn = get_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
