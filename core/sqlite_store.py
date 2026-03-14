import json
import os
import sqlite3
import threading
import time
from typing import Any, Dict

from core.常量与路径 import 取运行根目录


DB_FILENAME = "runtime_state.sqlite3"

SCOPE_SELECT_SETTINGS = "select_settings"
SCOPE_LOADING_PAYLOAD = "loading_payload"
SCOPE_GAME_ESC_MENU_SETTINGS = "game_esc_menu_settings"

_LOCK = threading.RLock()

_LEGACY_JSON_FILES = {
    SCOPE_SELECT_SETTINGS: ("选歌设置.json",),
    SCOPE_LOADING_PAYLOAD: ("加载页.json",),
    SCOPE_GAME_ESC_MENU_SETTINGS: ("游戏esc菜单设置.json", "电视跟跳设置.json"),
}


def get_runtime_store_path() -> str:
    return os.path.join(取运行根目录(), "json", DB_FILENAME)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def _connect() -> sqlite3.Connection:
    path = get_runtime_store_path()
    _ensure_parent_dir(path)
    conn = sqlite3.connect(path, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS store_kv (
            scope TEXT NOT NULL,
            key TEXT NOT NULL,
            value_json TEXT NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (scope, key)
        )
        """
    )
    conn.commit()


def _read_legacy_json(scope: str) -> Dict[str, Any]:
    filenames = _LEGACY_JSON_FILES.get(str(scope or "").strip(), ())
    if isinstance(filenames, str):
        filenames = (filenames,)
    if not filenames:
        return {}
    for filename in filenames:
        path = os.path.join(取运行根目录(), "json", str(filename or "").strip())
        if not os.path.isfile(path):
            continue
        for encoding in ("utf-8-sig", "utf-8", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    data = json.load(handle)
                return dict(data) if isinstance(data, dict) else {}
            except Exception:
                continue
    return {}


def _scope_has_rows(conn: sqlite3.Connection, scope: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM store_kv WHERE scope = ? LIMIT 1",
        (str(scope),),
    ).fetchone()
    return row is not None


def _write_rows(conn: sqlite3.Connection, scope: str, data: Dict[str, Any]) -> None:
    now = float(time.time())
    for key, value in dict(data or {}).items():
        conn.execute(
            """
            INSERT INTO store_kv (scope, key, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(scope, key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (
                str(scope),
                str(key),
                json.dumps(value, ensure_ascii=False),
                now,
            ),
        )


def _maybe_migrate_scope(conn: sqlite3.Connection, scope: str) -> None:
    if _scope_has_rows(conn, scope):
        return
    legacy = _read_legacy_json(scope)
    if not legacy:
        return
    _write_rows(conn, scope, legacy)
    conn.commit()


def read_scope(scope: str) -> Dict[str, Any]:
    scope_name = str(scope or "").strip()
    if not scope_name:
        return {}
    with _LOCK:
        conn = _connect()
        try:
            _ensure_schema(conn)
            _maybe_migrate_scope(conn, scope_name)
            rows = conn.execute(
                "SELECT key, value_json FROM store_kv WHERE scope = ?",
                (scope_name,),
            ).fetchall()
        finally:
            conn.close()
    result: Dict[str, Any] = {}
    for key, value_json in rows:
        try:
            result[str(key)] = json.loads(str(value_json))
        except Exception:
            result[str(key)] = value_json
    return result


def write_scope_patch(scope: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    scope_name = str(scope or "").strip()
    if not scope_name:
        return {}
    patch_data = dict(patch or {})
    with _LOCK:
        conn = _connect()
        try:
            _ensure_schema(conn)
            _maybe_migrate_scope(conn, scope_name)
            if patch_data:
                _write_rows(conn, scope_name, patch_data)
                conn.commit()
        finally:
            conn.close()
    return read_scope(scope_name)


def replace_scope(scope: str, data: Dict[str, Any]) -> Dict[str, Any]:
    scope_name = str(scope or "").strip()
    if not scope_name:
        return {}
    replace_data = dict(data or {})
    with _LOCK:
        conn = _connect()
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM store_kv WHERE scope = ?", (scope_name,))
            if replace_data:
                _write_rows(conn, scope_name, replace_data)
            conn.commit()
        finally:
            conn.close()
    return read_scope(scope_name)


def clear_scope(scope: str) -> None:
    scope_name = str(scope or "").strip()
    if not scope_name:
        return
    with _LOCK:
        conn = _connect()
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM store_kv WHERE scope = ?", (scope_name,))
            conn.commit()
        finally:
            conn.close()
