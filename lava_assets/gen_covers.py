"""Generates the 6 Lava.top product-card cover images (pack3/10/15 x ru/en)
by rendering a small HTML/CSS template and screenshotting it with Playwright
(no image-generation tool is available in this environment, and Lava.top's
own cover-size guide page returned HTTP 403 on every fetch attempt while
building this, so 1200x630 was chosen as a safe default: it's the standard
"link preview / cover" size used across most platforms, and Lava.top's own
product editor lets you re-crop an uploaded image on their side anyway).

Run with: python3 gen_covers.py
Output: covers/pack{3,10,15}_{ru,en}.png (1200x630, @2x pixel density baked
in for crispness -> actual PNG pixel size 2400x1260).
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "covers")
os.makedirs(OUT_DIR, exist_ok=True)

PACKS = {
    "pack3": {"ru": {"count": "3", "label": "разбора", "price": "399 ₽"},
              "en": {"count": "3", "label": "readings", "price": "$4.99"}},
    "pack10": {"ru": {"count": "10", "label": "разборов", "price": "999 ₽"},
               "en": {"count": "10", "label": "readings", "price": "$11.99"}},
    "pack15": {"ru": {"count": "15", "label": "разборов", "price": "1399 ₽"},
               "en": {"count": "15", "label": "readings", "price": "$15.99"}},
}

TITLE = {"ru": "Квадрат Пифагора", "en": "Pythagorean Square"}
SUBTITLE = {
    "ru": "Открывает вкладку «Графики»: периоды жизни и график жизненных сил",
    "en": "Unlocks the “Charts” tab: life periods and the life-force chart",
}
FOOTER = {"ru": "по дате рождения и ФИО · @AstroNumeros_bot",
          "en": "from birth date and full name · @AstroNumeros_bot"}
BEST_BADGE = {"ru": "Выгоднее", "en": "Best value"}

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
    width:1200px; height:630px; overflow:hidden;
    background:linear-gradient(135deg,var(--bg) 0%,var(--hi) 100%);
    font-family:'Helvetica Neue',Arial,sans-serif; color:var(--fg);
    display:flex; align-items:center; justify-content:space-between;
    padding:0 70px; position:relative;
  }}
  .grid {{
    display:grid; grid-template-columns:repeat(3,84px); grid-template-rows:repeat(3,84px);
    gap:6px; background:var(--line); border:2px solid var(--accent); border-radius:14px;
    padding:6px; box-shadow:0 18px 40px -12px rgba(138,75,45,0.35);
  }}
  .cell {{
    background:var(--card); border-radius:8px; display:flex; align-items:center;
    justify-content:center; font-size:15px; letter-spacing:2px; color:var(--accent);
    font-weight:600;
  }}
  .right {{ max-width:640px; }}
  .eyebrow {{
    font-size:20px; color:var(--accent); font-weight:600; letter-spacing:0.5px;
    margin-bottom:10px;
  }}
  h1 {{ font-size:46px; margin:0 0 14px 0; font-weight:700; line-height:1.1; }}
  .subtitle {{ font-size:21px; color:var(--muted); line-height:1.4; margin-bottom:30px; }}
  .badge-row {{ display:flex; align-items:center; gap:18px; }}
  .pack-badge {{
    background:var(--accent); color:#fff; border-radius:16px; padding:16px 30px;
    font-size:30px; font-weight:700; box-shadow:0 10px 24px -8px rgba(138,75,45,0.5);
  }}
  .price {{ font-size:34px; font-weight:700; color:var(--fg); }}
  .best {{
    position:absolute; top:36px; right:70px; background:#2f6e4c; color:#fff;
    font-size:16px; font-weight:700; padding:8px 16px; border-radius:999px;
  }}
  .footer {{
    position:absolute; bottom:30px; left:70px; right:70px; font-size:16px;
    color:var(--muted); display:flex; justify-content:space-between;
  }}
</style></head>
<body>
  {best_badge}
  <div class="grid">
    {cells}
  </div>
  <div class="right">
    <div class="eyebrow">{title}</div>
    <h1>{count} {label}</h1>
    <div class="subtitle">{subtitle}</div>
    <div class="badge-row">
      <div class="pack-badge">{count} {label}</div>
      <div class="price">{price}</div>
    </div>
  </div>
  <div class="footer"><span>{footer}</span><span>Квадрат Пифагора</span></div>
</body></html>
"""


def render(pack_key, lang):
    p = PACKS[pack_key][lang]
    cells_html = "".join(f'<div class="cell">{c}</div>' for c in GRID_CELLS)
    best_badge = f'<div class="best">{BEST_BADGE[lang]}</div>' if pack_key == "pack15" else ""
    html = HTML_TEMPLATE.format(
        title=TITLE[lang], subtitle=SUBTITLE[lang], footer=FOOTER[lang],
        count=p["count"], label=p["label"], price=p["price"],
        cells=cells_html, best_badge=best_badge,
    )
    return html


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        for pack_key in PACKS:
            for lang in ("ru", "en"):
                html = render(pack_key, lang)
                page.set_content(html)
                out_path = os.path.join(OUT_DIR, f"{pack_key}_{lang}.png")
                page.screenshot(path=out_path)
                print("wrote", out_path)
        browser.close()


if __name__ == "__main__":
    main()
