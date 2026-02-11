# ui_app.py
import json
import os
import time
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(page_title="RSSS Analyzer UI", layout="wide")

# ----------------------------
# Helpers: build report objects
# ----------------------------
def build_report_json(platform: str, handle_or_url: str, max_posts: int, runtime_s: float):
    now = datetime.now(timezone.utc).isoformat()

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
            "generated_at": now,
            "run_time_seconds": runtime_s
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

    return raw, report

def report_to_markdown(report: dict) -> str:
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

def save_outputs(raw: dict, report: dict, md: str):
    os.makedirs("outputs", exist_ok=True)

    with open("outputs/raw.json", "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    with open("outputs/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open("outputs/report.md", "w", encoding="utf-8") as f:
        f.write(md)

# ----------------------------
# UI
# ----------------------------
st.title("RSSS Analyzer — UI")
st.caption("Genera reportes Social en JSON + Markdown (MVP).")

with st.sidebar:
    st.header("Inputs")
    platform = st.selectbox("Plataforma", ["instagram", "tiktok", "youtube", "facebook"], index=0)
    handle_or_url = st.text_input("Handle o URL", value="https://www.instagram.com/")
    max_posts = st.number_input("Posts a analizar (MVP)", min_value=1, max_value=100, value=12, step=1)

run = st.button("🚀 Generar reporte", type="primary", use_container_width=True)

if "raw" not in st.session_state:
    st.session_state.raw = None
if "report" not in st.session_state:
    st.session_state.report = None
if "md" not in st.session_state:
    st.session_state.md = None
if "elapsed" not in st.session_state:
    st.session_state.elapsed = None

if run:
    t0 = time.time()
    raw, report = build_report_json(platform, handle_or_url, int(max_posts), 0.0)
    md = report_to_markdown(report)

    elapsed = time.time() - t0
    report["meta"]["run_time_seconds"] = round(elapsed, 4)

    st.session_state.raw = raw
    st.session_state.report = report
    st.session_state.md = md
    st.session_state.elapsed = elapsed

    save_outputs(raw, report, md)

# Render results
if st.session_state.report:
    st.success(f"Listo ✅ Tiempo: {st.session_state.elapsed:.2f}s")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Report JSON")
        st.json(st.session_state.report)
        st.download_button(
            "⬇ Descargar report.json",
            data=json.dumps(st.session_state.report, ensure_ascii=False, indent=2),
            file_name="report.json",
            mime="application/json",
            key="dl_report"
        )

        st.subheader("Raw JSON")
        st.json(st.session_state.raw)
        st.download_button(
            "⬇ Descargar raw.json",
            data=json.dumps(st.session_state.raw, ensure_ascii=False, indent=2),
            file_name="raw.json",
            mime="application/json",
            key="dl_raw"
        )

    with col2:
        st.subheader("Markdown")
        st.text_area("report.md", value=st.session_state.md, height=520)
        st.download_button(
            "⬇ Descargar report.md",
            data=st.session_state.md,
            file_name="report.md",
            mime="text/markdown",
            key="dl_md"
        )
else:
    st.info("Presiona “Generar reporte” para ver resultados.")
