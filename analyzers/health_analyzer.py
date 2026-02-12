# analyzers/health_analyzer.py
from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime, timezone

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _grade(score: int) -> str:
    if score >= 93: return "A"
    if score >= 90: return "A-"
    if score >= 87: return "B+"
    if score >= 83: return "B"
    if score >= 80: return "B-"
    if score >= 77: return "C+"
    if score >= 73: return "C"
    if score >= 70: return "C-"
    if score >= 67: return "D+"
    if score >= 63: return "D"
    return "F"

def compute_health_score(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Usa analytics ya calculado (caption_analyzer + temporal).
    Devuelve:
      - health_score 0-100
      - health_grade
      - signals (flags)
      - breakdown (por componente)
    """
    temporal = (analytics or {}).get("temporal") or {}
    language_ratio = (analytics or {}).get("language_ratio") or {}
    cta_frequency = (analytics or {}).get("cta_frequency") or {}
    dominant_topics = (analytics or {}).get("dominant_topics") or {}
    hashtag_frequency = (analytics or {}).get("hashtag_frequency") or {}
    avg_likes_est = (analytics or {}).get("avg_likes_est")
    avg_comments_est = (analytics or {}).get("avg_comments_est")

    # ---- Component 1: Recency (0-30) ----
    # usa min age_days de posts_with_dates
    posts_with_dates = temporal.get("posts_with_dates") or []
    ages = [p.get("age_days") for p in posts_with_dates if isinstance(p.get("age_days"), int)]
    min_age = min(ages) if ages else None

    if min_age is None:
        recency = 10.0  # neutral low si no hay fechas
    else:
        # 0 días => 30 pts, 90 días => 10 pts, 180+ => 0 pts
        recency = 30.0 - (min_age * 0.15)
        recency = _clamp(recency, 0.0, 30.0)

    # ---- Component 2: Activity density (0-20) ----
    # span_days vs número de posts fechados
    dated_count = len([p for p in posts_with_dates if p.get("published_at")])
    span_days = temporal.get("span_days")
    if isinstance(span_days, int) and span_days >= 0 and dated_count > 0:
        # posts por semana aproximado
        weeks = max(1.0, span_days / 7.0)
        p_per_week = dated_count / weeks
        # 3+/week => 20 pts, 1/week => 12 pts, 0.3/week => 5 pts
        activity = 6.0 + (p_per_week * 5.0)
        activity = _clamp(activity, 0.0, 20.0)
    else:
        activity = 8.0

    # ---- Component 3: CTA usage (0-15) ----
    cta_total = sum(cta_frequency.values()) if isinstance(cta_frequency, dict) else 0
    if cta_total <= 0:
        cta_score = 4.0
    else:
        # 1-2 => ok, 3-6 => good, 7+ => strong
        cta_score = 6.0 + min(9.0, cta_total * 1.5)
    cta_score = _clamp(cta_score, 0.0, 15.0)

    # ---- Component 4: Topic diversity (0-15) ----
    # cuántos topics distintos aparecen
    if isinstance(dominant_topics, dict):
        topics_used = [k for k, v in dominant_topics.items() if isinstance(v, int) and v > 0]
    else:
        topics_used = []
    diversity_n = len(topics_used)

    # 1 topic => 5, 2 => 8, 3 => 11, 4+ => 15
    diversity = {0: 3.0, 1: 5.0, 2: 8.0, 3: 11.0}.get(diversity_n, 15.0)
    diversity = _clamp(diversity, 0.0, 15.0)

    # ---- Component 5: Hashtag hygiene (0-10) ----
    # si hay hashtags y variedad
    if isinstance(hashtag_frequency, dict) and len(hashtag_frequency) > 0:
        # si top 10 tiene variedad, sube score
        uniq = len(hashtag_frequency)
        hashtag_score = 4.0 + min(6.0, uniq * 0.4)
    else:
        hashtag_score = 3.0
    hashtag_score = _clamp(hashtag_score, 0.0, 10.0)

    # ---- Component 6: Engagement signal (0-10) ----
    # solo si tenemos likes/comments estimados
    eng_score = 0.0
    if isinstance(avg_likes_est, (int, float)) and avg_likes_est is not None:
        # 100 likes => 4, 500 => 7, 1500 => 10
        eng_score = 2.0 + (avg_likes_est / 200.0)
    if isinstance(avg_comments_est, (int, float)) and avg_comments_est is not None:
        eng_score += min(3.0, avg_comments_est / 50.0)
    eng_score = _clamp(eng_score, 0.0, 10.0)

    score = int(round(recency + activity + cta_score + diversity + hashtag_score + eng_score))
    score = int(_clamp(score, 0, 100))

    # ---- Signals ----
    signals = {
        "has_dates": bool(posts_with_dates and any(p.get("published_at") for p in posts_with_dates)),
        "recent_activity": (min_age is not None and min_age <= 14),
        "stale_account": (min_age is not None and min_age >= 90),
        "low_cta_usage": (cta_total < 2),
        "low_topic_diversity": (diversity_n <= 1),
        "low_hashtag_usage": (not hashtag_frequency or len(hashtag_frequency) < 3),
        "engagement_unknown": (avg_likes_est is None and avg_comments_est is None),
    }

    breakdown = {
        "recency_0_30": round(recency, 2),
        "activity_0_20": round(activity, 2),
        "cta_0_15": round(cta_score, 2),
        "topic_diversity_0_15": round(diversity, 2),
        "hashtags_0_10": round(hashtag_score, 2),
        "engagement_0_10": round(eng_score, 2),
    }

    return {
        "health_score": score,
        "health_grade": _grade(score),
        "signals": signals,
        "breakdown": breakdown
    }
