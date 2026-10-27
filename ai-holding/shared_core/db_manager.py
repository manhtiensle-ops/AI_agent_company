import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from shared_core.config import RESOURCES_DB_PATH, MESSAGES_DB_PATH


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode & performance settings
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_databases() -> None:
    # 1. Initialize resources.db
    with get_db_connection(RESOURCES_DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS service_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            account_email TEXT NOT NULL,
            vault_secret_ref TEXT NOT NULL,
            status TEXT DEFAULT 'AVAILABLE',
            locked_by_company TEXT,
            locked_by_agent TEXT,
            quota_remaining REAL DEFAULT 100.0,
            cooldown_until DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()

    # 2. Initialize messages.db
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_path TEXT NOT NULL,
            receiver_path TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_runtime_state (
            agent_path TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            status TEXT DEFAULT 'IDLE',
            current_step_summary TEXT,
            token_used INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_num INTEGER NOT NULL,
            agent_path TEXT NOT NULL,
            thought TEXT,
            tool_call TEXT,
            tool_output TEXT,
            memory_snapshot TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()


# --- RESOURCE LOCK FUNCTIONS (ATOMIC ROW LOCKING) ---

def register_service_account(
    provider: str,
    account_email: str,
    vault_secret_ref: str,
    quota_remaining: float = 100.0
) -> int:
    with get_db_connection(RESOURCES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO service_accounts (provider, account_email, vault_secret_ref, quota_remaining)
            VALUES (?, ?, ?, ?)
        """, (provider, account_email, vault_secret_ref, quota_remaining))
        conn.commit()
        return int(cursor.lastrowid or 0)


def acquire_resource_lock(
    provider: str,
    company_id: str,
    agent_id: str
) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(RESOURCES_DB_PATH)
    try:
        # Use BEGIN IMMEDIATE for exclusive write locking
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, provider, account_email, vault_secret_ref, quota_remaining
            FROM service_accounts
            WHERE provider = ? AND status = 'AVAILABLE'
            ORDER BY id ASC
            LIMIT 1
        """, (provider,))
        row = cursor.fetchone()
        if not row:
            conn.commit()
            return None

        account_id = row["id"]
        cursor.execute("""
            UPDATE service_accounts
            SET status = 'IN_USE',
                locked_by_company = ?,
                locked_by_agent = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (company_id, agent_id, account_id))
        conn.commit()

        return {
            "id": row["id"],
            "provider": row["provider"],
            "account_email": row["account_email"],
            "vault_secret_ref": row["vault_secret_ref"],
            "quota_remaining": row["quota_remaining"],
            "locked_by_company": company_id,
            "locked_by_agent": agent_id
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def release_resource_lock(account_id: int, agent_id: str, quota_remaining: Optional[float] = None) -> bool:
    with get_db_connection(RESOURCES_DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            UPDATE service_accounts
            SET status = 'AVAILABLE',
                locked_by_company = NULL,
                locked_by_agent = NULL,
                updated_at = CURRENT_TIMESTAMP
        """
        params: List[Any] = []
        if quota_remaining is not None:
            query += ", quota_remaining = ?"
            params.append(quota_remaining)
        query += " WHERE id = ? AND locked_by_agent = ?"
        params.extend([account_id, agent_id])

        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0


# --- MESSAGES & EXECUTION STEP FUNCTIONS ---

def post_message(
    sender_path: str,
    receiver_path: str,
    channel_type: str,
    payload: Dict[str, Any]
) -> int:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (sender_path, receiver_path, channel_type, payload_json)
            VALUES (?, ?, ?, ?)
        """, (sender_path, receiver_path, channel_type, json.dumps(payload, ensure_ascii=False)))
        conn.commit()
        return int(cursor.lastrowid or 0)


def get_pending_messages(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sender_path, receiver_path, channel_type, payload_json, status, created_at
            FROM messages
            WHERE status = 'PENDING'
            ORDER BY id ASC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "sender_path": r["sender_path"],
                "receiver_path": r["receiver_path"],
                "channel_type": r["channel_type"],
                "payload": json.loads(r["payload_json"]),
                "status": r["status"],
                "created_at": r["created_at"]
            })
        return results


def update_message_status(message_id: int, status: str) -> None:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        conn.execute("""
            UPDATE messages
            SET status = ?
            WHERE id = ?
        """, (status, message_id))
        conn.commit()


def update_agent_runtime_state(
    agent_path: str,
    mode: str,
    status: str,
    current_step_summary: Optional[str] = None,
    token_used_delta: int = 0
) -> None:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runtime_state (agent_path, mode, status, current_step_summary, token_used, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(agent_path) DO UPDATE SET
                mode = excluded.mode,
                status = excluded.status,
                current_step_summary = COALESCE(excluded.current_step_summary, agent_runtime_state.current_step_summary),
                token_used = agent_runtime_state.token_used + excluded.token_used,
                updated_at = CURRENT_TIMESTAMP
        """, (agent_path, mode, status, current_step_summary, token_used_delta))
        conn.commit()


def record_execution_step(
    step_num: int,
    agent_path: str,
    thought: Optional[str],
    tool_call: Optional[str],
    tool_output: Optional[str],
    memory_snapshot: Optional[str]
) -> int:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO execution_steps (step_num, agent_path, thought, tool_call, tool_output, memory_snapshot)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (step_num, agent_path, thought, tool_call, tool_output, memory_snapshot))
        conn.commit()
        return int(cursor.lastrowid or 0)


def rollback_execution_steps(agent_path: str, target_step_num: int) -> Optional[str]:
    with get_db_connection(MESSAGES_DB_PATH) as conn:
        cursor = conn.cursor()
        # Find memory snapshot at target_step_num
        cursor.execute("""
            SELECT memory_snapshot
            FROM execution_steps
            WHERE agent_path = ? AND step_num = ?
            ORDER BY id DESC
            LIMIT 1
        """, (agent_path, target_step_num))
        row = cursor.fetchone()
        snapshot = row["memory_snapshot"] if row else None

        # Delete steps after target_step_num
        cursor.execute("""
            DELETE FROM execution_steps
            WHERE agent_path = ? AND step_num > ?
        """, (agent_path, target_step_num))
        conn.commit()
        return snapshot
