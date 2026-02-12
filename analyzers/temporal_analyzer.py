# analyzers/temporal_analyzer.py
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional

# Month maps (English + Spanish short/basic)
MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,

    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "sep": 9, "setiembre": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}

# Example: "... on February 20, 2018 ..."
RE_ON_MONTH_DAY_YEAR = re.compile(
    r"\bon\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+(\d{1,2}),\s*(\d{4})\b",
    re.IGNORECASE
)

# Spanish-ish: "20 de febrero de 2018"
RE_DAY_DE_MONTH_DE_YEAR = re.compile(
    r"\b(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})\b",
    re.IGNORECASE
)

def _norm(s: str) -> str:
    return (s or "").strip()

def _lower(s: str) -> str:
    return _norm(s).lower()

def _month_to_num(m: str) -> Optional[int]:
    if not m:
        return None
    return MONTHS.get(_lower(m))

def parse_post_date(text: str) -> Optional[datetime]:
    """
    Intenta sacar fecha de un blob de texto (caption + og_description).
    Regresa datetime UTC (00:00) si encuentra.
    """
    t = _norm(text)
    if not t:
        return None

    m = RE_ON_MONTH_DAY_YEAR.search(t)
    if m:
        month_name, day, year = m.group(1), m.group(2), m.group(3)
        month = _month_to_num(month_name)
        if month:
            return datetime(int(year), month, int(day), tzinfo=timezone.utc)

    m2 = RE_DAY_DE_MONTH_DE_YEAR.search(t)
    if m2:
        day, month_name, year = m2.group(1), m2.group(2), m2.group(3)
        month = _month_to_num(month_name)
        if month:
            return datetime(int(year), month, int(day), tzinfo=timezone.utc)

    return None

def analyze_temporal(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Input: posts_annotated (ideal) o top_posts.
    Espera campos:
      - caption
      - og_description
      - likes_est (opcional)
      - comments_est (opcional)
    Output:
      - min_date / max_date
      - span_days
      - posts_per_year
      - avg_likes_est_per_year (si hay)
      - avg_comments_est_per_year (si hay)
      - era_guess (3 buckets por terciles)
      - posts_with_dates (misma lista con published_at + year/month)
    """
    now = datetime.now(timezone.utc)

    posts_with_dates = []
    dates = []

    per_year = Counter()
    likes_by_year = defaultdict(list)
    comments_by_year = defaultdict(list)

    for p in posts or []:
        caption = _norm(p.get("caption", ""))
        og = _norm(p.get("og_description", ""))
        blob = (caption + "\n" + og).strip()

        dt = parse_post_date(blob)
        year = dt.year if dt else None
        month = dt.month if dt else None

        if dt:
            dates.append(dt)
            per_year[year] += 1

            likes_est = p.get("likes_est")
            comments_est = p.get("comments_est")
            if isinstance(likes_est, int):
                likes_by_year[year].append(likes_est)
            if isinstance(comments_est, int):
                comments_by_year[year].append(comments_est)

        item = dict(p)
        item["published_at"] = dt.isoformat() if dt else None
        item["year"] = year
        item["month"] = month
        if dt:
            item["age_days"] = (now - dt).days
        else:
            item["age_days"] = None

        posts_with_dates.append(item)

    if not dates:
        return {
            "min_date": None,
            "max_date": None,
            "span_days": None,
            "posts_per_year": dict(per_year),
            "avg_likes_est_per_year": {},
            "avg_comments_est_per_year": {},
            "era_guess": [],
            "posts_with_dates": posts_with_dates,
            "note": "No pude detectar fechas en los textos."
        }

    min_dt = min(dates)
    max_dt = max(dates)
    span_days = (max_dt - min_dt).days

    avg_likes_per_year = {}
    for y, vals in likes_by_year.items():
        if vals:
            avg_likes_per_year[str(y)] = round(sum(vals) / len(vals), 2)

    avg_comments_per_year = {}
    for y, vals in comments_by_year.items():
        if vals:
            avg_comments_per_year[str(y)] = round(sum(vals) / len(vals), 2)

    # Era guess: divide por fecha en 3 “eras” (viejo/medio/reciente)
    sorted_dates = sorted(dates)
    n = len(sorted_dates)
    cut1 = sorted_dates[int(n * 0.33)] if n > 2 else sorted_dates[0]
    cut2 = sorted_dates[int(n * 0.66)] if n > 2 else sorted_dates[-1]

    def era_for(dt: datetime) -> str:
        if dt <= cut1:
            return "era_1_old"
        if dt <= cut2:
            return "era_2_middle"
        return "era_3_recent"

    era_counts = Counter()
    for dt in dates:
        era_counts[era_for(dt)] += 1

    return {
        "min_date": min_dt.isoformat(),
        "max_date": max_dt.isoformat(),
        "span_days": span_days,
        "posts_per_year": {str(k): v for k, v in sorted(per_year.items())},
        "avg_likes_est_per_year": avg_likes_per_year,
        "avg_comments_est_per_year": avg_comments_per_year,
        "era_guess": dict(era_counts),
        "posts_with_dates": posts_with_dates
    }
