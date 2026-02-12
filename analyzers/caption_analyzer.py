# analyzers/caption_analyzer.py
import re
from collections import Counter
from typing import Dict, List, Any

# --- Heuristics dictionaries ---
CTA_PATTERNS = {
    "order": [r"\border\b", r"\borden(a|e|en)?\b", r"order\s+now", r"ordena\s+ya"],
    "visit": [r"\bvisit\b", r"\bvisita\b", r"\bcome\s+by\b", r"\bpás(a|ate)\b", r"\bven\b"],
    "call": [r"\bcall\b", r"\bllama\b", r"\btext\b", r"\bmensaje\b"],
    "dm": [r"\bdm\b", r"\bmessage us\b", r"\bmand(a|en)\s+dm\b", r"\bmand(a|en)\s+mensaje\b"],
    "link_in_bio": [r"link in bio", r"enlace en bio", r"link en bio"],
    "download": [r"\bdownload\b", r"\bdescarga\b", r"\bapp\b"],
    "pickup": [r"\bpickup\b", r"\brecog(e|er)\b", r"\bpara llevar\b"],
    "delivery": [r"\bdelivery\b", r"\bentrega\b", r"\bdomicilio\b", r"doordash", r"uber\s*eats", r"grubhub"],
}

TOPIC_KEYWORDS = {
    "delivery": ["delivery", "doordash", "uber eats", "grubhub", "pickup", "para llevar", "domicilio"],
    "prime": ["prime", "ribeye", "marbling", "angus", "choice", "brisket", "wagyu", "tomahawk", "picaña"],
    "heladas": ["helado", "ice cream", "nieves", "paleta", "paletas"],
    "game_day": ["gameday", "game day", "superbowl", "super bowl", "bbq", "grill", "asada", "parrilla", "wings"],
    "promos": ["promo", "promotion", "deal", "special", "oferta", "descuento", "2x1", "two for one"],
}

SPANISH_HINTS = {"el","la","los","las","de","del","para","con","que","por","una","un","y","en","hoy","mañana","gracias","sabor","carne","tacos"}
ENGLISH_HINTS = {"the","and","with","for","you","your","today","tomorrow","thanks","best","meat","tacos","order","visit"}

HASHTAG_RE = re.compile(r"(?:^|\s)(#\w+)", re.UNICODE)
NUMBER_RE = re.compile(r"(\d[\d,\.]*)")

def _norm_text(s: str) -> str:
    return (s or "").strip()

def _lower(s: str) -> str:
    return _norm_text(s).lower()

def _extract_hashtags(text: str) -> List[str]:
    return [h.lower() for h in HASHTAG_RE.findall(text or "")]

def _detect_language(text: str) -> str:
    t = _lower(text)
    if not t:
        return "unknown"

    # simple scoring
    es = sum(1 for w in SPANISH_HINTS if re.search(rf"\b{re.escape(w)}\b", t))
    en = sum(1 for w in ENGLISH_HINTS if re.search(rf"\b{re.escape(w)}\b", t))

    if es == 0 and en == 0:
        return "unknown"
    if es > 0 and en > 0:
        # mixed if both are present
        if abs(es - en) <= 1:
            return "mixed"
    return "es" if es > en else "en"

def _detect_ctas(text: str) -> List[str]:
    t = _lower(text)
    found = []
    for cta, patterns in CTA_PATTERNS.items():
        for p in patterns:
            if re.search(p, t):
                found.append(cta)
                break
    return found

def _detect_topics(text: str) -> List[str]:
    t = _lower(text)
    found = []
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw.lower())}\b", t):
                found.append(topic)
                break
    return found

def _parse_likes_comments_from_og(og_desc: str) -> Dict[str, int | None]:
    """
    Heurístico:
    og:description a veces trae: "X likes, Y comments - ... on Instagram: ..."
    Lo parseamos con regex.
    """
    t = _lower(og_desc)
    likes = None
    comments = None

    # likes
    m = re.search(r"([\d,\.]+)\s+likes", t)
    if m:
        likes = _to_int(m.group(1))

    # comments (a veces)
    m2 = re.search(r"([\d,\.]+)\s+comments", t)
    if m2:
        comments = _to_int(m2.group(1))

    return {"likes_est": likes, "comments_est": comments}

def _to_int(num_str: str) -> int | None:
    try:
        s = (num_str or "").replace(",", "")
        # strip decimals safely
        if "." in s:
            # "1.2" ambiguous; treat as float then int
            return int(float(s))
        return int(s)
    except:
        return None

def analyze_posts(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Input posts: [{caption, og_description(optional), post_url, image_url, ...}]
    Output analytics:
      - avg likes/comments est
      - hashtag freq
      - language ratio
      - cta freq
      - topic freq
      - per-post annotations
    """
    hashtag_counter = Counter()
    cta_counter = Counter()
    topic_counter = Counter()
    lang_counter = Counter()

    likes_vals = []
    comments_vals = []

    annotated_posts = []

    for p in posts or []:
        caption = _norm_text(p.get("caption", ""))
        og = _norm_text(p.get("og_description", ""))

        blob = (caption + "\n" + og).strip()

        # hashtags
        tags = _extract_hashtags(blob)
        hashtag_counter.update(tags)

        # language
        lang = _detect_language(blob)
        lang_counter.update([lang])

        # CTA
        ctas = _detect_ctas(blob)
        cta_counter.update(ctas)

        # topics
        topics = _detect_topics(blob)
        topic_counter.update(topics)

        # engagement (from og desc)
        eng = _parse_likes_comments_from_og(og)
        likes_est = eng["likes_est"]
        comments_est = eng["comments_est"]
        if isinstance(likes_est, int):
            likes_vals.append(likes_est)
        if isinstance(comments_est, int):
            comments_vals.append(comments_est)

        annotated_posts.append({
            **p,
            "hashtags": tags,
            "language_est": lang,
            "ctas": ctas,
            "topics": topics,
            "likes_est": likes_est,
            "comments_est": comments_est
        })

    total = sum(lang_counter.values()) or 1
    language_ratio = {k: round(v / total, 4) for k, v in lang_counter.items()}

    avg_likes_est = round(sum(likes_vals) / len(likes_vals), 2) if likes_vals else None
    avg_comments_est = round(sum(comments_vals) / len(comments_vals), 2) if comments_vals else None

    return {
        "avg_likes_est": avg_likes_est,
        "avg_comments_est": avg_comments_est,
        "hashtag_frequency": dict(hashtag_counter.most_common(20)),
        "language_ratio": language_ratio,
        "cta_frequency": dict(cta_counter.most_common(20)),
        "dominant_topics": dict(topic_counter.most_common(20)),
        "posts_annotated": annotated_posts
    }
