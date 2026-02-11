# runner.py
import json
import os
from datetime import datetime, timezone

import requests

def build_report_md(report: dict) -> str:
    """Convierte el reporte JSON a Markdown simple."""
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
        lines.append(f"- Bio: {p.get('bio','')}")
        lines.append(f"- Website: {p.get('website','')}")
        avatar = p.get("avatar_url","")
        if avatar:
            lines.append(f"- Avatar: ![]({avatar})")
        lines.append("")

    lines.append("## 2) Top posts (muestra)")
    if not top_posts:
        lines.append("- (sin posts disponibles en MVP)")
    for post in top_posts:
        lines.append(f"### Post — {post.get('post_id','')}")
        img = post.get("image_url","")
        if img:
            lines.append(f"![]({img})")
        lines.append(f"- URL: {post.get('post_url','')}")
        lines.append(f"- Fecha: {post.get('published_at','')}")
        lines.append(f"- Likes: {post.get('likes')} | Comments: {post.get('comments')}")
        lines.append(f"- Caption: {post.get('caption','')}")
        lines.append("")

    lines.append("## 3) Plan de acción (MVP)")
    if not action_plan:
        lines.append("- (pendiente)")
    for a in action_plan:
        lines.append(f"- **{a.get('priority','')}** — {a.get('title','')}")
        lines.append(f"  - Why: {a.get('why','')}")
        lines.append(f"  - How: {a.get('how','')}")
        lines.append(f"  - KPI: {a.get('kpi','')}")
        lines.append("")

    return "\n".join(lines)

def main():
    # --------- Inputs (MVP) ----------
    platform = "instagram"
    handle_or_url = "https://www.instagram.com/"  # cámbialo luego
    max_posts = 12

    # --------- MVP: solo “esqueleto” ----------
    # Nota: Instagram/TikTok/FB no dan datos completos sin APIs o scraping avanzado.
    # Aquí creamos el pipeline y outputs estables desde ya.

    started = datetime.now(timezone.utc)
    run_time_seconds = 0.0

    raw = {
        "platform": platform,
        "handle_or_url": handle_or_url,
        "max_posts": max_posts,
        "note": "MVP skeleton (sin extracción real todavía)."
    }

    report = {
        "meta": {
            "platform": platform,
            "handle": handle_or_url,
            "generated_at": started.isoformat(),
            "run_time_seconds": run_time_seconds
        },
        "profiles": [
            {
                "platform": platform,
                "handle": handle_or_url,
                "profile_url": handle_or_url,
                "bio": "",
                "website": "",
                "avatar_url": ""
            }
        ],
        "content": {
            "top_posts": []
        },
        "action_plan": [
            {
                "priority": "alta",
                "title": "Define 3 pilares de contenido",
                "why": "para que el feed sea consistente",
                "how": "Producto / Promos / Behind-the-scenes",
                "kpi": "posts por pilar/semana"
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
