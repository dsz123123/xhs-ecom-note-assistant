from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.config import DB_FILE


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    main_image TEXT NOT NULL DEFAULT '',
    product_id TEXT NOT NULL DEFAULT '',
    selling_points TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    storage_state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publish_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    account_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    images TEXT NOT NULL DEFAULT '[]',
    style TEXT NOT NULL DEFAULT '',
    is_product_note INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'draft',
    scheduled_at TEXT,
    published_at TEXT,
    hang_status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_schedule
ON publish_tasks(status, scheduled_at);
"""


class Database:
    def __init__(self, path: Path | str = DB_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)
            connection.execute(
                "UPDATE publish_tasks SET status='failed', error_message='程序异常退出，任务状态已恢复'"
                " WHERE status='publishing'"
            )

    @staticmethod
    def now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def fetchall(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]

    def fetchone(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.connection() as connection:
            cursor = connection.execute(sql, tuple(params))
            return int(cursor.lastrowid or 0)

    def list_products(self) -> list[dict]:
        return self.fetchall("SELECT * FROM products ORDER BY id DESC")

    def get_product(self, row_id: int) -> dict | None:
        return self.fetchone("SELECT * FROM products WHERE id=?", (row_id,))

    def save_product(self, data: dict, row_id: int | None = None) -> int:
        now = self.now()
        values = (
            data.get("name", "").strip(),
            data.get("main_image", "").strip(),
            data.get("product_id", "").strip(),
            data.get("selling_points", "").strip(),
            data.get("tags", "").strip(),
        )
        if row_id is not None:
            self.execute(
                """UPDATE products SET
                   name=?, main_image=?, product_id=?, selling_points=?, tags=?, updated_at=?
                   WHERE id=?""",
                values + (now, row_id),
            )
            return row_id
        return self.execute(
            """INSERT INTO products
               (name, main_image, product_id, selling_points, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            values + (now, now),
        )

    def delete_product(self, row_id: int) -> None:
        self.execute("DELETE FROM products WHERE id=?", (row_id,))

    def list_accounts(self) -> list[dict]:
        return self.fetchall("SELECT * FROM accounts ORDER BY id DESC")

    def get_account(self, row_id: int) -> dict | None:
        return self.fetchone("SELECT * FROM accounts WHERE id=?", (row_id,))

    def save_account(self, name: str, storage_state: str) -> int:
        return self.execute(
            "INSERT INTO accounts(name, storage_state, created_at) VALUES (?, ?, ?)",
            (name.strip(), storage_state.strip(), self.now()),
        )

    def delete_account(self, row_id: int) -> None:
        self.execute("DELETE FROM accounts WHERE id=?", (row_id,))

    def create_task(self, data: dict) -> int:
        now = self.now()
        return self.execute(
            """INSERT INTO publish_tasks
               (product_id, account_id, title, content, tags, images, style,
                is_product_note, status, scheduled_at, hang_status,
                error_message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '', ?, ?)""",
            (
                data.get("product_id"),
                data["account_id"],
                data["title"].strip(),
                data["content"].strip(),
                json.dumps(data.get("tags", []), ensure_ascii=False),
                json.dumps(data.get("images", []), ensure_ascii=False),
                data.get("style", ""),
                1 if data.get("is_product_note", True) else 0,
                data.get("status", "pending"),
                data.get("scheduled_at"),
                now,
                now,
            ),
        )

    def list_tasks(self) -> list[dict]:
        return self.fetchall(
            """SELECT t.*, p.name AS product_name, p.product_id AS platform_product_id,
                      a.name AS account_name, a.storage_state
               FROM publish_tasks t
               LEFT JOIN products p ON p.id=t.product_id
               JOIN accounts a ON a.id=t.account_id
               ORDER BY t.id DESC"""
        )

    def get_task(self, row_id: int) -> dict | None:
        return self.fetchone(
            """SELECT t.*, p.name AS product_name, p.product_id AS platform_product_id,
                      p.selling_points, a.name AS account_name, a.storage_state
               FROM publish_tasks t
               LEFT JOIN products p ON p.id=t.product_id
               JOIN accounts a ON a.id=t.account_id
               WHERE t.id=?""",
            (row_id,),
        )

    def due_task_ids(self) -> list[int]:
        rows = self.fetchall(
            """SELECT id FROM publish_tasks
               WHERE status='pending' AND scheduled_at IS NOT NULL AND scheduled_at<=?
               ORDER BY scheduled_at ASC""",
            (self.now(),),
        )
        return [int(row["id"]) for row in rows]

    def update_task_status(
        self,
        row_id: int,
        status: str,
        *,
        hang_status: str | None = None,
        error_message: str = "",
        published_at: str | None = None,
    ) -> None:
        task = self.get_task(row_id)
        if task is None:
            return
        self.execute(
            """UPDATE publish_tasks
               SET status=?, hang_status=?, error_message=?, published_at=?, updated_at=?
               WHERE id=?""",
            (
                status,
                hang_status if hang_status is not None else task["hang_status"],
                error_message,
                published_at if published_at is not None else task["published_at"],
                self.now(),
                row_id,
            ),
        )

    def retry_task(self, row_id: int) -> None:
        self.execute(
            """UPDATE publish_tasks
               SET status='pending', hang_status='pending', error_message='',
                   published_at=NULL, updated_at=?
               WHERE id=?""",
            (self.now(), row_id),
        )

    def cancel_task(self, row_id: int) -> None:
        self.execute(
            "UPDATE publish_tasks SET status='cancelled', updated_at=? WHERE id=?",
            (self.now(), row_id),
        )

    def delete_task(self, row_id: int) -> None:
        self.execute("DELETE FROM publish_tasks WHERE id=?", (row_id,))
