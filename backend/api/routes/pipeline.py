"""Landing / Autopilot live-pipeline routes.

POST /api/v1/pipeline/preview          → JSON (runs full pipeline, returns final result)
POST /api/v1/pipeline/preview/stream   → text/event-stream (one SSE event per real stage)
GET  /api/v1/pipeline/preview/stream   → same, query-param form for EventSource
"""
import json
import sys, os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.pipeline.preview import run_preview, stream_preview

router = APIRouter()


class PreviewRequest(BaseModel):
    query: str = ""


@router.post("/preview")
async def preview(req: PreviewRequest):
    return await run_preview(req.query)


def _sse(query: str) -> StreamingResponse:
    async def gen():
        try:
            async for event in stream_preview(query):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # never leak a stack trace to the browser
            err = {"stage": "FAILED", "status": "failed",
                   "label": "The pipeline hit an unexpected error.",
                   "warnings": [{"code": "INTERNAL", "message": type(exc).__name__}]}
            yield f"data: {json.dumps(err)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


@router.post("/preview/stream")
async def preview_stream_post(req: PreviewRequest):
    return _sse(req.query)


@router.get("/preview/stream")
async def preview_stream_get(query: str = ""):
    return _sse(query)
