# extractors/instagram_public.py
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def extract_instagram_profile_posts(profile_url: str, max_posts: int = 12) -> Dict:
    """
    Extrae posts públicos de un perfil de Instagram (sin login), usando Playwright.
    Devuelve:
      - profile_url
      - posts: [{post_url, image_url, caption}]
    Nota: Instagram cambia seguido; esto es MVP y puede requerir ajustes.
    """
    if not profile_url.startswith("http"):
        profile_url = f"https://www.instagram.com/{profile_url.strip().lstrip('@').strip('/')}/"

    result = {
        "profile_url": profile_url,
        "posts": [],
        "warnings": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        page.goto(profile_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # Cerrar popups comunes (cookies/login)
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

        page.wait_for_timeout(1500)

        # Tomar links de posts desde el grid del perfil
        post_links = []
        # Instagram suele usar /p/ o /reel/
        anchors = page.locator('a[href^="/p/"], a[href^="/reel/"]')
        count = anchors.count()
        for i in range(min(count, max_posts * 3)):
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

        if not post_links:
            result["warnings"].append("No se encontraron posts en el grid (puede haber bloqueo o cambio de UI).")

        # Visitar cada post para sacar caption + imagen
        for url in post_links[:max_posts]:
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Caption: suele estar en el primer article
                caption = ""
                try:
                    # Esto es heurístico; a veces cambia
                    caption_el = page.locator("article").locator("h1, span").first
                    caption = _clean(caption_el.inner_text(timeout=2000))
                except:
                    caption = ""

                # Imagen: tomar la primera imagen visible
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

        ctx.close()
        browser.close()

    return result
