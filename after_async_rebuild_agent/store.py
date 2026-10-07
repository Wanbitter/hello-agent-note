import json
import sqlite3

DB_PATH = "sessions.db"


def init_db():
    """建表（如果还没有）。启动时调一次。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                history    TEXT NOT NULL,
                updated_at TEXT
            )
        """)


def load_history(session_id: str, system_prompt: str) -> list:
    """读出这个会话的历史；没有就新开一份。"""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT history FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

    if row is None:
        return [{"role": "system", "content": system_prompt}]
    return json.loads(row[0])          # ★ 从 JSON 字符串还原成 list


def save_history(session_id: str, history: list):
    """把会话历史写回数据库（有就覆盖，没有就插入）。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, history, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                history    = excluded.history,
                updated_at = excluded.updated_at
            """,
            (session_id, json.dumps(history, ensure_ascii=False)),   # ★ 存成 JSON 字符串
        )


if __name__ == "__main__":
    init_db()
    h = load_history("test", "你是助手")
    print("初次:", h)
    h.append({"role": "user", "content": "你好"})
    save_history("test", h)
    print("重读:", load_history("test", "你是助手"))