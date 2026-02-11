# runner.py
import json
import os
from datetime import datetime, timezone

from extractors.instagram_public import extract_instagram_profile_posts

def build_report_md(report: dict) -> str:
    meta = report.get("meta", {})
    profiles = report.get("profiles", [])
    top_posts = report.get("content", {}).get("top_posts", [])
    action_plan = report.get("action_plan", [])

    lines = []
    lines.append(f"# Social Report — {meta.get('platform','')} | {meta.get('handle','')}")
    lines.append(f"Generated: {meta.get('generated_at','')}")
    lines.append(f"Runtime: {meta.get('run_time_seconds','')}s")
    lines.append("")
    lines.append("## 1) Perfil")
    for p in profiles:
        lines.append(f"### {p.get('platform','')} — {p.get('handle','')}")
        lines.append(f"- URL: {p.get('profile_url','')}")
        bio = p.get("bio","")
        if bio:
            lines.append(f"- Bio: {bio}")
        website = p.get("website","")
        if website:
            lines.append(f"- Website: {website}")
        avatar = p.get("avatar_url","")
        if avatar:
            lines.append(f"- Avatar: ![]({avatar})")
        lines.append("")

    lines.append("## 2) Top posts (muestra)")
    if not top_posts:
        lines.append("- (sin posts disponibles)")
    for post in top_posts:
        lines.append(f"### Post")
        img = post.get("image_url","")
        if img:
            lines.append(f"![]({img})")
        lines.append(f"- URL: {post.get('post_url','')}")
        lines.append(f"- Caption: {post.get('caption','')}")
        lines.append("")

    lines.append("## 3) Plan de acción (MVP)")
    for a in action_plan:
        lines.append(f"- **{a.get('priority','')}** — {a.get('title','')}")
        lines.append(f"  - Why: {a.get('why','')}")
        lines.append(f"  - How: {a.get('how','')}")
        lines.append(f"  - KPI: {a.get('kpi','')}")
        lines.append("")

    return "\n".join(lines)

def main():
    # -------- Inputs (MVP) --------
    platform = "instagram"
    handle_or_url = "instagram"  # pon aquí @handle o URL, ej: "lacarniceria" o "https://www.instagram.com/lacarniceria/"
    max_posts = 12

    started = datetime.now(timezone.utc)
    t0 = datetime.now(timezone.utc)

    raw = {
        "platform": platform,
        "handle_or_url": handle_or_url,
        "max_posts": max_posts,
    }

    # -------- Extract (PUBLIC MODE) --------
    ig = extract_instagram_profile_posts(handle_or_url, max_posts=max_posts)

    raw["instagram_public"] = ig

    # -------- Build report --------
    now = datetime.now(timezone.utc).isoformat()
    run_time_seconds = (datetime.now(timezone.utc) - t0).total_seconds()

    top_posts = []
    for p in ig.get("posts", [])[:max_posts]:
        top_posts.append({
            "post_url": p.get("post_url",""),
            "image_url": p.get("image_url",""),
            "caption": p.get("caption",""),
        })

    report = {
        "meta": {
            "platform": platform,
            "handle": handle_or_url,
            "generated_at": now,
            "run_time_seconds": round(run_time_seconds, 2)
        },
        "profiles": [
            {
                "platform": platform,
                "handle": handle_or_url,
                "profile_url": ig.get("profile_url",""),
                "bio": "",
                "website": "",
                "avatar_url": ""
            }
        ],
        "content": {
            "top_posts": top_posts
        },
        "warnings": ig.get("warnings", []),
        "action_plan": [
            {
                "priority": "alta",
                "title": "3 posts por semana (constancia)",
                "why": "Instagram premia actividad constante y reduce caídas de alcance",
                "how": "Calendario simple: Lun=producto, Mié=behind-the-scenes, Vie=promo",
                "kpi": "3 posts/semana por 4 semanas"
            },
            {
                "priority": "media",
                "title": "Mejorar captions con CTA",
                "why": "Más comentarios = más distribución",
                "how": "Termina captions con pregunta (ej. “¿Cuál corte prefieres?”)",
                "kpi": "comentarios/post +20%"
            }
        ]
    }

    md = build_report_md(report)

    os.makedirs("outputs", exist_ok=True)

    with open("outputs/raw.json", "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    with open("outputs/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open("outputs/report.md", "w", encoding="utf-8") as f:
        f.write(md)

    print("✅ Listo. Archivos generados:")
    print("- outputs/raw.json")
    print("- outputs/report.json")
    print("- outputs/report.md")

if __name__ == "__main__":
    main()
