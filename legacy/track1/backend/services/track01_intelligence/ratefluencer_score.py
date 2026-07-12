import hashlib
from typing import Optional


class RatefluencerScoringEngine:
    """Full ML-style scoring engine for influencer analytics."""

    def calculate_score(self, metrics: dict) -> dict:
        followers = metrics.get("followers", 100000)
        engagement_rate = metrics.get("engagement_rate", 3.0)
        avg_likes = metrics.get("avg_likes", 3000)
        avg_comments = metrics.get("avg_comments", 150)
        post_frequency = metrics.get("post_frequency", 3.0)
        avg_views = metrics.get("avg_views", 25000)
        handle = metrics.get("handle", "unknown")

        # Engagement score: 6% = perfect 100
        engagement_score = min(100.0, (engagement_rate / 6.0) * 100.0)

        # Authenticity from like-to-follower ratio
        like_ratio = avg_likes / max(followers, 1)
        if like_ratio > 0.04:
            authenticity_score = 92.0 + (like_ratio - 0.04) * 100.0
        elif like_ratio >= 0.02:
            # linear interpolation 78..92
            authenticity_score = 78.0 + ((like_ratio - 0.02) / 0.02) * 14.0
        elif like_ratio >= 0.01:
            authenticity_score = 60.0 + ((like_ratio - 0.01) / 0.01) * 18.0
        else:
            authenticity_score = 40.0 + (like_ratio / 0.01) * 20.0
        authenticity_score = min(100.0, authenticity_score)

        # Growth score from post frequency (5/wk = 70 pts + 20 base)
        growth_score = min(100.0, (post_frequency / 5.0) * 70.0 + 20.0)

        # Brand score composite
        brand_score = (
            engagement_score * 0.4
            + authenticity_score * 0.35
            + growth_score * 0.25
        )

        # Master ratefluencer score
        ratefluencer_score = (
            engagement_score * 0.30
            + authenticity_score * 0.30
            + growth_score * 0.20
            + brand_score * 0.20
        )

        # Deterministic variation based on handle hash (+/- 3 pts)
        variation = (int(hashlib.md5(str(handle).encode()).hexdigest(), 16) % 7) - 3
        ratefluencer_score = max(0, min(100, ratefluencer_score + variation))

        return {
            "ratefluencer_score": round(ratefluencer_score),
            "engagement_score": round(engagement_score),
            "authenticity_score": round(authenticity_score),
            "growth_score": round(growth_score),
            "brand_score": round(brand_score),
        }

    def get_brand_matches(self, niche: str, scores: dict) -> list:
        niche_lower = (niche or "").lower()

        if any(kw in niche_lower for kw in ["fashion", "style", "beauty", "lifestyle"]):
            candidates = [
                {"name": "Nike", "match_score": 96, "reason": "Fashion-forward audience with high purchase intent"},
                {"name": "Zara", "match_score": 92, "reason": "Style-driven content aligns with fast fashion brand values"},
                {"name": "H&M", "match_score": 87, "reason": "Aspirational lifestyle content resonates with H&M demographics"},
                {"name": "L'Oreal", "match_score": 83, "reason": "Beauty and self-expression overlap with L'Oreal campaigns"},
                {"name": "Sephora", "match_score": 79, "reason": "Premium beauty audience with high brand affinity"},
            ]
        elif any(kw in niche_lower for kw in ["tech", "startup", "software", "ai", "developer"]):
            candidates = [
                {"name": "Apple", "match_score": 94, "reason": "Tech-savvy audience with premium product affinity"},
                {"name": "Microsoft", "match_score": 89, "reason": "Developer and productivity audience match"},
                {"name": "Samsung", "match_score": 85, "reason": "Broad tech consumer overlap"},
                {"name": "Google", "match_score": 82, "reason": "Digital-native audience highly engaged with Google ecosystem"},
                {"name": "Spotify", "match_score": 78, "reason": "Tech and creator culture audience alignment"},
            ]
        elif any(kw in niche_lower for kw in ["wellness", "health", "fitness", "mindful", "yoga"]):
            candidates = [
                {"name": "Lululemon", "match_score": 91, "reason": "Wellness lifestyle audience perfectly aligned"},
                {"name": "Sephora", "match_score": 88, "reason": "Self-care and beauty crossover audience"},
                {"name": "Whole Foods", "match_score": 85, "reason": "Health-conscious consumer base overlap"},
                {"name": "Nike", "match_score": 82, "reason": "Active lifestyle and fitness community"},
                {"name": "Calm", "match_score": 79, "reason": "Mindfulness and mental wellness audience match"},
            ]
        else:
            candidates = [
                {"name": "Spotify", "match_score": 88, "reason": "Mass-market creator audience with strong Spotify listener overlap"},
                {"name": "Nike", "match_score": 85, "reason": "Broad consumer appeal and aspirational brand values"},
                {"name": "Adidas", "match_score": 82, "reason": "Lifestyle and culture-forward audience alignment"},
                {"name": "Apple", "match_score": 79, "reason": "Premium consumer tech audience crossover"},
                {"name": "Samsung", "match_score": 76, "reason": "Broad tech-friendly demographics"},
            ]

        return candidates

    def predict_growth(
        self,
        followers: int,
        engagement_rate: float,
        post_frequency: float,
        months: int = 12,
    ) -> dict:
        monthly_growth_rate = (
            0.015
            + (engagement_rate / 100.0) * 0.8
            + (post_frequency / 7.0) * 0.3
        )
        monthly_growth_rate = min(0.25, monthly_growth_rate)

        # Always project at least 12 months so 3m/6m/12m are all available,
        # regardless of the requested horizon.
        horizon = max(months, 12)
        curve = [followers]
        current = followers
        for _ in range(horizon):
            current = int(current * (1 + monthly_growth_rate))
            curve.append(current)

        projected_3m = curve[3]
        projected_6m = curve[6]
        projected_12m = curve[12]
        # The visible curve respects the requested horizon.
        curve = curve[: months + 1]

        return {
            "current": followers,
            "projected_3m": projected_3m,
            "projected_6m": projected_6m,
            "projected_12m": projected_12m,
            "monthly_rate": round(monthly_growth_rate * 100, 2),
            "curve": curve,
        }

    def detect_authenticity(
        self,
        followers: int,
        avg_likes: int,
        avg_comments: int,
    ) -> dict:
        like_ratio = avg_likes / max(followers, 1)
        comment_ratio = avg_comments / max(avg_likes, 1)

        if like_ratio < 0.003:
            fake_estimate = 35
        elif like_ratio < 0.01:
            fake_estimate = 15
        elif like_ratio < 0.03:
            fake_estimate = 5
        else:
            fake_estimate = 2

        genuine_pct = 100 - fake_estimate

        # Comment quality score: high comment-to-like ratio indicates genuine engagement
        comment_quality_score = min(100, int(comment_ratio * 500))

        if fake_estimate <= 5:
            verdict = "Highly Authentic"
            pod_risk = "Low"
        elif fake_estimate <= 15:
            verdict = "Mostly Authentic"
            pod_risk = "Medium"
        else:
            verdict = "Suspicious Signals Detected"
            pod_risk = "High"

        return {
            "fake_follower_pct": fake_estimate,
            "genuine_pct": genuine_pct,
            "comment_quality_score": comment_quality_score,
            "authenticity_verdict": verdict,
            "engagement_pod_risk": pod_risk,
        }


scoring_engine = RatefluencerScoringEngine()
