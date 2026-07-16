"""Tiny SQLite history so past evaluations are saved and re-viewable."""
import sqlite3
import json
import pathlib
import datetime

DB = pathlib.Path(__file__).parent / "history.db"


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS evaluations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT, mode TEXT, provider TEXT, grounding TEXT,
                input_json TEXT, result_json TEXT, total_score INTEGER, grade TEXT)"""
        )


def save(mode, provider, grounding, inputs, result):
    with _conn() as c:
        c.execute(
            "INSERT INTO evaluations(created_at,mode,provider,grounding,input_json,result_json,total_score,grade) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (datetime.datetime.utcnow().isoformat(timespec="seconds"), mode, provider, grounding,
             json.dumps(inputs), json.dumps(result),
             result.get("total_score"), result.get("grade", {}).get("grade")),
        )


def get(evaluation_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM evaluations WHERE id=?", (evaluation_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"], "created_at": r["created_at"], "mode": r["mode"],
        "provider": r["provider"], "grounding": r["grounding"],
        "inputs": json.loads(r["input_json"]), "result": json.loads(r["result_json"]),
    }


def recent(limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT id,created_at,mode,provider,total_score,grade,input_json "
            "FROM evaluations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for r in rows:
        inp = json.loads(r["input_json"])
        title = inp.get("idea") or inp.get("core_problem") or next((v for v in inp.values() if v), "Untitled")
        items.append({
            "id": r["id"], "created_at": r["created_at"], "mode": r["mode"],
            "provider": r["provider"], "total_score": r["total_score"], "grade": r["grade"],
            "title": str(title)[:80],
        })
    return items
