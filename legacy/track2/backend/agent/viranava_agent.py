import sys
import os
import json
import asyncio
from typing import AsyncGenerator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.track01_intelligence.ratefluencer_score import RatefluencerScoringEngine
from services.track02_content.script_generator import ScriptGenerator
from services.ai_providers.gemini_client import GeminiClient
from services.metrics_resolver import resolve_metrics

# ── Optional LangGraph import ────────────────────────────────────────────────
try:
    from typing import TypedDict, Annotated
    from langgraph.graph import StateGraph, END

    class AgentState(TypedDict):
        task: str
        handle: str
        platform: str
        trend: str
        influencer_data: dict
        trend_data: dict
        script: dict
        virality: dict
        logs: list
        final_result: dict

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False
    AgentState = dict  # type: ignore


class ViraNovaAgent:
    def __init__(self):
        self.engine = RatefluencerScoringEngine()
        self.generator = ScriptGenerator()
        self.gemini = GeminiClient()

    async def stream_workflow(
        self, task: str, handle: str, platform: str
    ) -> AsyncGenerator[str, None]:
        """
        Runs a 5-step agentic workflow and yields SSE events for each step.
        Each event: data: {step, message, data, progress}\n\n
        """
        logs = []
        state: dict = {
            "task": task,
            "handle": handle,
            "platform": platform,
            "trend": "",
            "influencer_data": {},
            "trend_data": {},
            "script": {},
            "virality": {},
            "logs": logs,
            "final_result": {},
        }

        # ── Step 1: data_scout ───────────────────────────────────────────
        # Resolve metrics through the SAME shared resolver the /analyze
        # dashboard uses, so the Ratefluencer Score the agent streams is
        # identical to the score shown on the dashboard for this handle.
        await asyncio.sleep(0.3)
        metrics = await resolve_metrics(handle, platform)
        state["influencer_data"] = metrics
        source = "live" if metrics.get("is_real") else "sample"
        msg1 = (
            f"Scouting {source} data for {handle} on {platform}. "
            f"Found {metrics['followers']:,} followers."
        )
        logs.append(msg1)
        yield _sse(
            step="data_scout",
            message=msg1,
            data={"followers": metrics["followers"], "engagement_rate": metrics["engagement_rate"]},
            progress=20,
        )

        # ── Step 2: scorer ───────────────────────────────────────────────
        await asyncio.sleep(0.4)
        scores = self.engine.calculate_score(metrics)
        state["virality"] = scores
        brands = self.engine.get_brand_matches(metrics.get("niche", "general"), scores)
        state["trend_data"]["brands"] = brands
        msg2 = (
            f"Ratefluencer Score™ calculated: {scores['ratefluencer_score']}/100. "
            f"Authenticity: {scores['authenticity_score']}."
        )
        logs.append(msg2)
        yield _sse(
            step="scorer",
            message=msg2,
            data=scores,
            progress=40,
        )

        # ── Step 3: script_gen ───────────────────────────────────────────
        await asyncio.sleep(0.4)
        trend_topic = f"creator intelligence and influencer analytics for {platform}"
        script = await self.generator.generate(
            topic=trend_topic, duration=30, style="hooks"
        )
        state["script"] = script
        msg3 = f"Viral script generated for topic: '{trend_topic}'."
        logs.append(msg3)
        yield _sse(
            step="script_gen",
            message=msg3,
            data={"hook": script.get("hook", ""), "cta": script.get("cta", "")},
            progress=65,
        )

        # ── Step 4: virality_predictor ───────────────────────────────────
        await asyncio.sleep(0.4)
        hook_text = script.get("hook", "")
        virality = await self.generator.predict_virality(hook_text, platform)
        state["virality"] = {**scores, **virality}
        msg4 = (
            f"Virality prediction complete: {virality.get('virality_score', 'N/A')}/100. "
            f"Grade: {virality.get('grade', 'B')}."
        )
        logs.append(msg4)
        yield _sse(
            step="virality_predictor",
            message=msg4,
            data=virality,
            progress=85,
        )

        # ── Step 5: synthesizer ──────────────────────────────────────────
        await asyncio.sleep(0.3)
        growth = self.engine.predict_growth(
            followers=metrics["followers"],
            engagement_rate=metrics["engagement_rate"],
            post_frequency=metrics["post_frequency"],
        )
        authenticity = self.engine.detect_authenticity(
            followers=metrics["followers"],
            avg_likes=metrics["avg_likes"],
            avg_comments=metrics["avg_comments"],
        )
        final_result = {
            "status": "success",
            "handle": handle,
            "platform": platform,
            "scores": scores,
            "brands": brands[:3],
            "script": script,
            "virality": virality,
            "growth": growth,
            "authenticity": authenticity,
            "logs": logs,
        }
        state["final_result"] = final_result
        msg5 = (
            f"Analysis complete for {handle}. "
            f"Ratefluencer Score: {scores['ratefluencer_score']}/100. "
            f"Projected followers in 6 months: {growth['projected_6m']:,}."
        )
        logs.append(msg5)
        yield _sse(
            step="synthesizer",
            message=msg5,
            data=final_result,
            progress=100,
        )


def _sse(step: str, message: str, data: dict, progress: int) -> str:
    payload = json.dumps(
        {"step": step, "message": message, "data": data, "progress": progress}
    )
    return f"data: {payload}\n\n"


viranava_agent = ViraNovaAgent()
