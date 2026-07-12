"""
In-memory reports & content library store.
Uses SQLite for persistence across restarts when running locally.
"""
import sys
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "creatrix.db")


def _get_db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT, platform TEXT, scores TEXT,
            summary TEXT, created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, content TEXT, virality_score INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


class SaveReportRequest(BaseModel):
    handle: str
    platform: str = "instagram"
    scores: dict = {}
    summary: str = ""


class SaveContentRequest(BaseModel):
    type: str = "script"
    content: dict = {}
    virality_score: int = 0


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=50),
    platform: str = Query("all"),
):
    conn = _get_db()
    offset = (page - 1) * limit
    if platform.lower() == "all":
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    else:
        rows = conn.execute(
            "SELECT * FROM reports WHERE platform=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (platform, limit, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE platform=?", (platform,)
        ).fetchone()[0]
    conn.close()
    reports = []
    for r in rows:
        reports.append({
            "id": r["id"],
            "handle": r["handle"],
            "platform": r["platform"],
            "scores": json.loads(r["scores"] or "{}"),
            "summary": r["summary"],
            "created_at": r["created_at"],
        })
    return {"status": "success", "reports": reports, "total": total, "page": page}


@router.post("/save")
async def save_report(req: SaveReportRequest):
    conn = _get_db()
    cursor = conn.execute(
        "INSERT INTO reports (handle, platform, scores, summary, created_at) VALUES (?,?,?,?,?)",
        (req.handle, req.platform, json.dumps(req.scores), req.summary, datetime.utcnow().isoformat()),
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return {"status": "success", "saved": True, "report_id": report_id}


@router.get("/library")
async def get_library(
    type: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    conn = _get_db()
    offset = (page - 1) * limit
    if type.lower() == "all":
        rows = conn.execute(
            "SELECT * FROM library ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM library").fetchone()[0]
    else:
        rows = conn.execute(
            "SELECT * FROM library WHERE type=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (type, limit, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM library WHERE type=?", (type,)
        ).fetchone()[0]
    conn.close()
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "type": r["type"],
            "content": json.loads(r["content"] or "{}"),
            "virality_score": r["virality_score"],
            "created_at": r["created_at"],
        })
    return {"status": "success", "items": items, "total": total, "page": page}


@router.post("/library/save")
async def save_content(req: SaveContentRequest):
    conn = _get_db()
    cursor = conn.execute(
        "INSERT INTO library (type, content, virality_score, created_at) VALUES (?,?,?,?)",
        (req.type, json.dumps(req.content), req.virality_score, datetime.utcnow().isoformat()),
    )
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return {"status": "success", "saved": True, "content_id": content_id}
