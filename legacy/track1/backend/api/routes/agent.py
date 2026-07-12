import sys
import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agent.viranava_agent import ViraNovaAgent

router = APIRouter()


class AgentRequest(BaseModel):
    task: str = "full_analysis"
    input: str
    platform: str = "instagram"


@router.post("/run")
async def run_agent(request: AgentRequest):
    agent = ViraNovaAgent()
    return StreamingResponse(
        agent.stream_workflow(request.task, request.input, request.platform),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
