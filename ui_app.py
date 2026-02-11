# ui_app.py
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="RSSS Analyzer UI", layout="wide")

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def normalize_ig_profile(profile_url_or_handle: str) -> str:
    s = (profile_url_or_handle or "").strip()
    if s.startswith("http"):
        return s if s.endswith("/") else s + "/"
    handle = s.lstrip("@").strip().strip("/")
    return f"https://www.instagram.com/{handle}/"

def _try_click(page, selectors):
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=1500)
            return True
        except:
            pass
    return False

def _auto_scroll(page, steps=6, pause_ms=900):
    for _ in range(steps):
        try:
            page.mouse.wheel(0, 1400)
        except:
            pass
        page.wait_for_timeout(pause_ms)
        
def extract_instagram_public(profile_url_or_handle: str, max_posts: int, profile_dir: str) -> dict:
    """
    Extrae posts del perfil IG usando Playwright con un perfil persistente propio (NO tu Chrome real).
    Versión robusta: saca links via JS (document.querySelectorAll) en vez de locators frágiles.
    """
    profile_url = normalize_ig_profile(profile_url_or_handle)

    out = {"profile_url": profile_url, "posts": [], "warnings": []}
    Path(profile_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            locale="en-US",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        page = context.new_page()

        # 1) Ir al perfil
        page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        # 2) Cerrar popups comunes
        _try_click(page, [
            'button:has-text("Only allow essential cookies")',
            'button:has-text("Allow all cookies")',
            'button:has-text("Accept")',
            'button:has-text("Not Now")',
            'button:has-text("Not now")',
            'div[role="dialog"] button:has-text("Not Now")',
            'div[role="dialog"] button:has-text("Not now")',
        ])
        page.wait_for_timeout(1200)

        # 3) Esperar main y hacer scroll para que cargue el grid
        try:
            page.wait_for_selector("main", timeout=15000)
        except:
            out["warnings"].append("No apareció <main>. Puede ser bloqueo/captcha o carga incompleta.")

        _auto_scroll(page, steps=8, pause_ms=900)

        # 4) SACAR LINKS via JS (más robusto que locators)
        hrefs = page.evaluate("""
            () => Array.from(document.querySelectorAll('a'))
                .map(a => a.getAttribute('href') || a.href)
                .filter(Boolean)
        """)

        links = []
        for h in hrefs or []:
            # normalizar
            if h.startswith("/"):
                url = "https://www.instagram.com" + h
            else:
                url = h
            url = url.split("?")[0]

            if ("/p/" in url or "/reel/" in url) and url not in links:
                links.append(url)
            if len(links) >= max_posts:
                break

        if not links:
            out["warnings"].append("Veo el grid pero no pude leer links de posts. IG cambió markup o hay render dinámico raro.")
            out["warnings"].append("Prueba subir el scroll steps (ahorita son 8) o abre un post manualmente y re-run.")
            context.close()
            return out

        # 5) Visitar cada post y extraer caption + imagen (usamos og: para estabilidad)
        for url in links[:max_posts]:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1800)

                caption = ""
                # og:description suele traer texto (a veces con user + “likes”, pero sirve)
                try:
                    caption = page.locator("meta[property='og:description']").get_attribute("content") or ""
                    caption = _clean(caption)
                except:
                    caption = ""

                image_url = ""
                try:
                    image_url = page.locator("meta[property='og:image']").get_attribute("content") or ""
                except:
                    image_url = ""

                if not image_url:
                    try:
                        img = page.locator("article img").first
                        image_url = img.get_attribute("src") or ""
                    except:
                        image_url = ""

                out["posts"].append({
                    "post_url": url,
                    "image_url": image_url,
                    "caption": caption
                })
            except Exception as e:
                out["warnings"].append(f"Fallo extrayendo post {url}: {e}")

        context.close()

    return out


def build_report_json(platform: str, handle_or_url: str, max_posts: int, runtime_s: float, ig_data: dict):
    now = datetime.now(timezone.utc).isoformat()

    raw = {
        "platform": platform,
        "handle_or_url": handle_or_url,
        "max_posts": max_posts,
        "instagram_public": ig_data
    }

    top_posts = []
    for p in ig_data.get("posts", [])[:max_posts]:
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
            "run_time_seconds": runtime_s
        },
        "profiles": [
            {
                "platform": platform,
                "handle": handle_or_url,
                "profile_url": ig_data.get("profile_url",""),
                "bio": "",
                "website": "",
                "avatar_url": ""
            }
        ],
        "content": {"top_posts": top_posts},
        "warnings": ig_data.get("warnings", [])
    }

    return raw, report

def report_to_markdown(report: dict) -> str:
    meta = report.get("meta", {})
    top_posts = report.get("content", {}).get("top_posts", [])
    warnings = report.get("warnings", [])

    lines = []
    lines.append(f"# Social Report — {meta.get('platform','')} | {meta.get('handle','')}")
    lines.append(f"Generated: {meta.get('generated_at','')}")
    lines.append(f"Runtime: {meta.get('run_time_seconds','')}s")
    lines.append("")
    if warnings:
        lines.append("## Warnings")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Top posts")
    if not top_posts:
        lines.append("- (sin posts todavía)")
    for post in top_posts:
        img = post.get("image_url","")
        if img:
            lines.append(f"![]({img})")
        lines.append(f"- URL: {post.get('post_url','')}")
        cap = post.get("caption","")
        if cap:
            lines.append(f"- Caption: {cap}")
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
st.title("RSSS Analyzer — UI (Instagram Público)")
st.caption("Mete @handle o URL, elige N posts, y genera Markdown/JSON con imágenes por URL.")

with st.sidebar:
    st.header("Inputs")
    handle_or_url = st.text_input("Instagram @handle o URL", value="lacarniceriameatmarkettX".lower())
    max_posts = st.number_input("Posts a extraer", min_value=1, max_value=50, value=12, step=1)

    st.divider()
    st.write("Perfil persistente (para guardar login)")
    profile_dir = st.text_input(
        "Ruta del perfil (no toques si no quieres)",
        value=str(Path.cwd() / ".pw_ig_profile")
    )
    st.caption("Tip: la 1ra vez te abre Chrome del bot. Te logueas y ya queda guardado en esa carpeta.")

run = st.button("🚀 Extraer + Generar reporte", type="primary", use_container_width=True)

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
    progress = st.progress(0, text="Iniciando...")

    progress.progress(20, text="Abriendo Instagram y cargando grid...")
    ig_data = extract_instagram_public(handle_or_url, int(max_posts), profile_dir)

    progress.progress(85, text="Construyendo reporte...")
    elapsed = time.time() - t0
    raw, report = build_report_json("instagram", handle_or_url, int(max_posts), round(elapsed, 2), ig_data)
    md = report_to_markdown(report)

    save_outputs(raw, report, md)

    st.session_state.raw = raw
    st.session_state.report = report
    st.session_state.md = md
    st.session_state.elapsed = elapsed

    progress.progress(100, text="Listo ✅")

if st.session_state.report:
    st.success(f"Listo ✅ Tiempo: {st.session_state.elapsed:.2f}s")

    c1, c2 = st.columns(2)
    with c1:
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

    with c2:
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
    st.info("Pon un @handle o URL y presiona el botón para generar el reporte.")
