# extractors/instagram_public.py
import re
from typing import Dict
from playwright.sync_api import sync_playwright

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _normalize_profile_url(profile_url_or_handle: str) -> str:
    s = (profile_url_or_handle or "").strip()
    if s.startswith("http"):
        return s if s.endswith("/") else s + "/"
    handle = s.lstrip("@").strip().strip("/")
    return f"https://www.instagram.com/{handle}/"

def extract_instagram_profile_posts(profile_url_or_handle: str, max_posts: int = 12) -> Dict:
    """
    Extrae posts de un perfil de Instagram usando Playwright.
    Modo: usa tu PERFIL REAL de Chrome (sesión logueada).
    Devuelve:
      - profile_url
      - posts: [{post_url, image_url, caption}]
      - warnings: []
    """
    profile_url = _normalize_profile_url(profile_url_or_handle)

    result = {
        "profile_url": profile_url,
        "posts": [],
        "warnings": []
    }

    chrome_profile_dir = "/Users/tonym/Library/Application Support/Google/Chrome"

    with sync_playwright() as p:
        # 🔥 Usa tu perfil real de Chrome (persistente)
        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_profile_dir,
            headless=False,
            locale="en-US",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        page = context.new_page()

        # Ir al perfil
        page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        # Cerrar popups comunes
        for sel in [
            'button:has-text("Only allow essential cookies")',
            'button:has-text("Allow all cookies")',
            'button:has-text("Accept")',
            'button:has-text("Not Now")',
            'button:has-text("Not now")',
        ]:
            try:
                page.locator(sel).first.click(timeout=1500)
            except:
                pass

        page.wait_for_timeout(1200)

        # Tomar links de posts desde el grid del perfil
        post_links = []
        anchors = page.locator('a[href^="/p/"], a[href^="/reel/"]')

        # a veces tarda en cargar; reintento suave
        try:
            page.wait_for_selector('a[href^="/p/"], a[href^="/reel/"]', timeout=8000)
        except:
            pass

        count = anchors.count()
        if count == 0:
            result["warnings"].append("No se encontraron posts en el grid (posible bloqueo, cuenta privada o UI cambió).")

        for i in range(min(count, max_posts * 5)):
            try:
                href = anchors.nth(i).get_attribute("href")
                if href and href.startswith("/"):
                    url = "https://www.instagram.com" + href
                    if url not in post_links:
                        post_links.append(url)
                if len(post_links) >= max_posts:
                    break
            except:
                continue

        # Visitar cada post para sacar caption + imagen
        for url in post_links[:max_posts]:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1800)

                # caption (heurístico)
                caption = ""
                try:
                    # intenta agarrar el texto del primer bloque de caption
                    # Nota: Instagram cambia mucho, esto es MVP
                    caption_el = page.locator("article").locator("h1, span").first
                    caption = _clean(caption_el.inner_text(timeout=3000))
                except:
                    caption = ""

                # imagen (primer img visible)
                image_url = ""
                try:
                    img = page.locator("article img").first
                    image_url = img.get_attribute("src") or ""
                except:
                    image_url = ""

                result["posts"].append({
                    "post_url": url,
                    "image_url": image_url,
                    "caption": caption
                })
            except Exception as e:
                result["warnings"].append(f"Fallo extrayendo post {url}: {e}")

        context.close()

    return result
