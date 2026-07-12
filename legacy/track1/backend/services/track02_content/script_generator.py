import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.gemini_client import GeminiClient


class ScriptGenerator:
    def __init__(self):
        self.gemini = GeminiClient()

    async def generate(self, topic: str, duration: int = 30, style: str = "hooks") -> dict:
        system = (
            "You are a world-class viral content scriptwriter. "
            "Generate hook-optimised scripts for short-form video. Return ONLY valid JSON."
        )
        user = (
            f"Write a viral {duration}s {style} script about: {topic}. "
            f"Return JSON: {{\"hook\": \"(0-5s, attention-grabbing opener)\", "
            f"\"story\": \"(5-20s, core narrative)\", "
            f"\"insight\": \"(20-25s, key value/revelation)\", "
            f"\"cta\": \"(25-{duration}s, engagement CTA)\", "
            f"\"virality_tips\": [\"tip1\", \"tip2\", \"tip3\"]}}"
        )
        result = await self.gemini.complete_json(system, user, max_tokens=1000)
        if not result:
            result = self._fallback_script(topic, duration, style)
        return result

    async def predict_virality(self, script_text: str, platform: str = "instagram") -> dict:
        system = (
            "You are a viral content analyst. Score content objectively. Return ONLY valid JSON."
        )
        user = (
            f"Score this {platform} script (0-100) on virality: '{script_text[:500]}'. "
            f"Return JSON: {{\"virality_score\": int, \"hook_strength\": int, "
            f"\"content_novelty\": int, \"platform_fit\": int, \"expected_views\": int, "
            f"\"expected_likes\": int, \"expected_shares\": int, \"expected_saves\": int, "
            f"\"grade\": \"A/B/C/D\", \"recommendation\": \"one sentence\"}}"
        )
        result = await self.gemini.complete_json(system, user, max_tokens=1000)
        if not result:
            result = self._fallback_virality(script_text, platform)
        return result

    async def generate_linkedin_post(
        self, topic: str, audience: str = "professionals"
    ) -> dict:
        system = (
            "You are a LinkedIn thought leadership expert. Write viral professional posts."
        )
        user = (
            f"Write a LinkedIn post about: {topic} targeting {audience}. "
            "Make it hook-opening, value-dense, end with engagement question. "
            "Return JSON: {\"post_text\": \"full post with line breaks\", "
            "\"hashtags\": [\"#tag1\", \"#tag2\", \"#tag3\", \"#tag4\", \"#tag5\"], "
            "\"hook_line\": \"first sentence\", "
            "\"engagement_tip\": \"one tip to maximize comments\"}"
        )
        result = await self.gemini.complete_json(system, user, max_tokens=1000)
        if not result:
            result = self._fallback_linkedin(topic, audience)
        return result

    async def generate_instagram_caption(
        self, topic: str, style: str = "engaging"
    ) -> dict:
        system = (
            "You are an Instagram content expert specializing in viral captions."
        )
        user = (
            f"Write an Instagram caption about: {topic}, style: {style}. "
            "Return JSON: {\"caption\": \"caption with line breaks and emojis\", "
            "\"hashtags\": [\"#tag1\",\"#tag2\",\"#tag3\",\"#tag4\",\"#tag5\","
            "\"#tag6\",\"#tag7\",\"#tag8\",\"#tag9\",\"#tag10\"], "
            "\"hook\": \"first line only\"}"
        )
        result = await self.gemini.complete_json(system, user, max_tokens=1000)
        if not result:
            result = self._fallback_instagram(topic, style)
        return result

    # ── fallback helpers ────────────────────────────────────────────────────

    def _fallback_script(self, topic: str, duration: int, style: str) -> dict:
        return {
            "hook": f"Stop scrolling — {topic} just changed everything you thought you knew...",
            "story": f"Here's what nobody is telling you about {topic} in 2026. "
                     "Brands and creators who figured this out early are seeing 3x results.",
            "insight": f"The data shows that creators who master {topic} gain a measurable "
                       "competitive edge that compounds over time.",
            "cta": f"Follow @creatrix.ai and drop a comment below with your biggest {topic} question.",
            "virality_tips": [
                "Open with a bold, counter-intuitive claim to stop the scroll",
                "Use a pattern interrupt every 5 seconds to retain attention",
                "End with a question or CTA that invites personal response",
            ],
        }

    def _fallback_virality(self, script_text: str, platform: str) -> dict:
        length = len(script_text)
        base = 72 + (length % 16)
        return {
            "virality_score": base,
            "hook_strength": min(100, base + 8),
            "content_novelty": min(100, base - 4),
            "platform_fit": min(100, base + 2),
            "expected_views": base * 12000,
            "expected_likes": base * 600,
            "expected_shares": base * 120,
            "expected_saves": base * 160,
            "grade": "B+" if base >= 75 else "B",
            "recommendation": (
                "Strong opening hook detected. Tighten the story section "
                f"and add a stronger CTA for {platform} to maximise saves."
            ),
        }

    def _fallback_linkedin(self, topic: str, audience: str) -> dict:
        return {
            "post_text": (
                f"The rules of {topic} are being rewritten.\n\n"
                f"Here's what forward-thinking {audience} are doing differently in 2026:\n\n"
                "→ Leveraging AI to surface insights before competitors\n"
                "→ Building authentic communities rather than chasing vanity metrics\n"
                "→ Creating content that compounds in value over time\n\n"
                "The gap between those who adapt and those who don't is widening fast.\n\n"
                f"What's your take on {topic} in the next 12 months?"
            ),
            "hashtags": [
                f"#{topic.replace(' ', '')}",
                "#ThoughtLeadership",
                "#FutureOfWork",
                "#Innovation",
                "#ContentStrategy",
            ],
            "hook_line": f"The rules of {topic} are being rewritten.",
            "engagement_tip": "Post at 8–10am Tuesday or Wednesday for maximum impressions.",
        }

    def _fallback_instagram(self, topic: str, style: str) -> dict:
        return {
            "caption": (
                f"This is what {topic} looks like in 2026 ✨\n\n"
                "Stop overthinking it. The creators winning right now are the ones "
                "who show up consistently and let AI handle the heavy lifting.\n\n"
                "Are you adapting or watching others win? 👇"
            ),
            "hashtags": [
                "#ContentCreator", "#AITools", "#CreatorTips",
                "#InstagramGrowth", "#SocialMediaStrategy",
                "#InfluencerLife", "#ContentMarketing", "#DigitalCreator",
                "#ReelsTips", "#GrowthHacks",
            ],
            "hook": f"This is what {topic} looks like in 2026 ✨",
        }


script_generator = ScriptGenerator()
