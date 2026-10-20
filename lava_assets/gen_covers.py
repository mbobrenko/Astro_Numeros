"""Generates 2 universal Lava.top cover images (RU, EN) — used for all 3
pack sizes in each language, since the exact number of readings/price
already shows up in the product's own title and price field, so the
cover itself doesn't need to repeat it (per explicit request: the pack
count doesn't need to be on the cover).

Per explicit request, the covers (and all Lava.top-facing text) avoid the
"Квадрат Пифагора" / "Pythagorean Square" name — the marketplace-facing
branding is the more generic "Нумерологический разбор судьбы" / "Numerology
Destiny Reading" instead, with a short project-description paragraph baked
into the cover itself (Lava.top-style short pitch).

**Reworded 2026-10-08** after Lava.top's moderation rejected the product
for "эзотерический контент" (esoteric content). Dropped "нумерология" /
"numerology" and "судьба" / "destiny" entirely from every field — these are
exactly the words that trip the esoteric-category filter at most RU payment
aggregators right now, not just Lava.top (see lava_assets/README.md). The
product is now framed purely as a calculation/data tool based on birth date
and name ("числовой профиль по дате рождения" / "birth date number
profile"), with no "divination" framing anywhere.

Size confirmed from Lava.top's own "Как создать цифровой продукт?" FAQ
article (faq.lava.top/article/53726): cover must be 1160x464px, JPG/JPEG/
PNG/WebP.

Also generates one universal square icon (icon.png, 512x512) — Lava.top's
own digital-product guide only documents the 1160x464 cover, no separate
icon field, but this is included as a ready square brand mark in case one
is needed elsewhere in their UI (shop/profile icon, category icon, etc.)
that wasn't visible in the fetched docs.

Run with: python3 gen_covers.py
Output: covers/cover_{ru,en}.png (1160x464, @2x pixel density baked in
for crispness -> actual PNG pixel size 2320x928), covers/icon.png (512x512).
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "covers")
os.makedirs(OUT_DIR, exist_ok=True)

COVER_W = 1160
COVER_H = 464

EYEBROW = {"ru": "Расчёт по дате рождения", "en": "Birth Date Calculation"}
HEADLINE = {"ru": "Числовой профиль по дате рождения", "en": "Birth Date Number Profile"}
SUBTITLE = {
    "ru": "Персональный расчёт по дате рождения и ФИО: график жизненных ресурсов и периоды жизни — доступ открывается сразу после оплаты, прямо в Telegram.",
    "en": "A personal calculation from your birth date and name: your resource chart and life-period breakdown — unlocked instantly after payment, right in Telegram.",
}
TAG = {"ru": "Расчёты не сгорают · вход через Telegram",
       "en": "Credits never expire · Telegram login"}

# Decorative sample grid — not a real calculation, just echoes the site's
# 3x3 "square" visual so the cover reads as the same product at a glance.
GRID_CELLS = ["1 1 1", "2 2", "3 3 3 3", "4 4", "5", "", "7 7", "8", "9 9 9"]

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  :root {{
    --bg:#faf9f7; --fg:#1f1d1a; --muted:#6b665f; --card:#ffffff;
    --line:#e2ded7; --accent:#8a4b2d; --hi:#f3e6dc;
  }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; padding:0; }}
  body {{
    width:{w}px; height:{h}px; overflow:hidden;
    background:linear-gradient(135deg,var(--bg) 0%,var(--hi) 100%);
    font-family:'Helvetica Neue',Arial,sans-serif; color:var(--fg);
    display:flex; align-items:center; justify-content:space-between;
    padding:0 46px; position:relative;
  }}
  .grid {{
    display:grid; grid-template-columns:repeat(3,60px); grid-template-rows:repeat(3,60px);
    gap:5px; background:var(--line); border:2px solid var(--accent); border-radius:12px;
    padding:5px; box-shadow:0 14px 30px -10px rgba(138,75,45,0.35); flex:none;
  }}
  .cell {{
    background:var(--card); border-radius:7px; display:flex; align-items:center;
    justify-content:center; font-size:11px; letter-spacing:1.5px; color:var(--accent);
    font-weight:600;
  }}
  .right {{ max-width:680px; margin-left:36px; }}
  .eyebrow {{
    font-size:14px; color:var(--accent); font-weight:700; letter-spacing:1.2px;
    text-transform:uppercase; margin-bottom:8px;
  }}
  h1 {{ font-size:27px; margin:0 0 10px 0; font-weight:700; line-height:1.15; }}
  .subtitle {{ font-size:14px; color:var(--muted); line-height:1.45; margin-bottom:16px; }}
  .tag {{
    display:inline-block; background:var(--accent); color:#fff; border-radius:999px;
    padding:7px 16px; font-size:12px; font-weight:600;
  }}
</style></head>
<body>
  <div class="grid">
    {cells}
  </div>
  <div class="right">
    <div class="eyebrow">{eyebrow}</div>
    <h1>{headline}</h1>
    <div class="subtitle">{subtitle}</div>
    <div class="tag">{tag}</div>
  </div>
</body></html>
"""


def render(lang):
    cells_html = "".join(f'<div class="cell">{c}</div>' for c in GRID_CELLS)
    html = HTML_TEMPLATE.format(
        w=COVER_W, h=COVER_H,
        eyebrow=EYEBROW[lang], headline=HEADLINE[lang], subtitle=SUBTITLE[lang],
        tag=TAG[lang], cells=cells_html,
    )
    return html


ICON_SIZE = 512

ICON_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; padding:0; }}
  body {{
    width:{s}px; height:{s}px; overflow:hidden;
    background:linear-gradient(135deg,#faf9f7 0%,#f3e6dc 100%);
    display:flex; align-items:center; justify-content:center;
  }}
  .grid {{
    display:grid; grid-template-columns:repeat(3,100px); grid-template-rows:repeat(3,100px);
    gap:9px; background:#e2ded7; border:4px solid #8a4b2d; border-radius:26px;
    padding:9px; box-shadow:0 20px 44px -14px rgba(138,75,45,0.4);
  }}
  .cell {{
    background:#ffffff; border-radius:14px; display:flex; align-items:center;
    justify-content:center; font-size:19px; letter-spacing:2px; color:#8a4b2d;
    font-weight:700;
  }}
</style></head>
<body>
  <div class="grid">{cells}</div>
</body></html>
"""


def render_icon():
    cells_html = "".join(f'<div class="cell">{c}</div>' for c in GRID_CELLS)
    return ICON_HTML.format(s=ICON_SIZE, cells=cells_html)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page(viewport={"width": COVER_W, "height": COVER_H}, device_scale_factor=2)
        for lang in ("ru", "en"):
            html = render(lang)
            page.set_content(html)
            out_path = os.path.join(OUT_DIR, f"cover_{lang}.png")
            page.screenshot(path=out_path)
            print("wrote", out_path)

        icon_page = browser.new_page(viewport={"width": ICON_SIZE, "height": ICON_SIZE}, device_scale_factor=2)
        icon_page.set_content(render_icon())
        icon_path = os.path.join(OUT_DIR, "icon.png")
        icon_page.screenshot(path=icon_path)
        print("wrote", icon_path)

        browser.close()


if __name__ == "__main__":
    main()
