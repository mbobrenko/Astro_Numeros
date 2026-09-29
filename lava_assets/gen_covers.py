"""Generates the 6 Lava.top product-card cover images (pack3/10/15 x ru/en)
by rendering a small HTML/CSS template and screenshotting it with Playwright
(no image-generation tool is available in this environment).

Size confirmed from Lava.top's own "Как создать цифровой продукт?" FAQ
article (faq.lava.top/article/53726): cover must be 1160x464px, JPG/JPEG/
PNG/WebP.

Run with: python3 gen_covers.py
Output: covers/pack{3,10,15}_{ru,en}.png (1160x464, @2x pixel density baked
in for crispness -> actual PNG pixel size 2320x928).
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "covers")
os.makedirs(OUT_DIR, exist_ok=True)

COVER_W = 1160
COVER_H = 464

# NOTE on EN pack3 price: Lava.top requires a minimum product price of $5
# (per faq.lava.top/article/53726), so the originally-suggested $4.99 is
# bumped to $5.99 here — everywhere else (product titles/descriptions/
# content.md) should use this same figure.
PACKS = {
    "pack3": {"ru": {"count": "3", "label": "разбора", "price": "399 ₽"},
              "en": {"count": "3", "label": "readings", "price": "$5.99"}},
    "pack10": {"ru": {"count": "10", "label": "разборов", "price": "999 ₽"},
               "en": {"count": "10", "label": "readings", "price": "$11.99"}},
    "pack15": {"ru": {"count": "15", "label": "разборов", "price": "1399 ₽"},
               "en": {"count": "15", "label": "readings", "price": "$15.99"}},
}

TITLE = {"ru": "Квадрат Пифагора", "en": "Pythagorean Square"}
SUBTITLE = {
    "ru": "Вкладка «Графики»: периоды жизни и график жизненных сил",
    "en": "Unlocks “Charts”: life periods & life-force chart",
}
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
    width:{w}px; height:{h}px; overflow:hidden;
    background:linear-gradient(135deg,var(--bg) 0%,var(--hi) 100%);
    font-family:'Helvetica Neue',Arial,sans-serif; color:var(--fg);
    display:flex; align-items:center; justify-content:space-between;
    padding:0 46px; position:relative;
  }}
  .grid {{
    display:grid; grid-template-columns:repeat(3,58px); grid-template-rows:repeat(3,58px);
    gap:5px; background:var(--line); border:2px solid var(--accent); border-radius:12px;
    padding:5px; box-shadow:0 14px 30px -10px rgba(138,75,45,0.35); flex:none;
  }}
  .cell {{
    background:var(--card); border-radius:7px; display:flex; align-items:center;
    justify-content:center; font-size:11px; letter-spacing:1.5px; color:var(--accent);
    font-weight:600;
  }}
  .right {{ max-width:660px; margin-left:36px; }}
  .eyebrow {{
    font-size:15px; color:var(--accent); font-weight:600; letter-spacing:0.4px;
    margin-bottom:6px;
  }}
  h1 {{ font-size:32px; margin:0 0 8px 0; font-weight:700; line-height:1.1; }}
  .subtitle {{ font-size:14px; color:var(--muted); line-height:1.35; margin-bottom:16px; }}
  .badge-row {{ display:flex; align-items:center; gap:14px; }}
  .pack-badge {{
    background:var(--accent); color:#fff; border-radius:12px; padding:10px 20px;
    font-size:19px; font-weight:700; box-shadow:0 8px 18px -6px rgba(138,75,45,0.5);
  }}
  .price {{ font-size:21px; font-weight:700; color:var(--fg); }}
  .best {{
    position:absolute; top:18px; right:46px; background:#2f6e4c; color:#fff;
    font-size:12px; font-weight:700; padding:5px 12px; border-radius:999px;
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
</body></html>
"""


def render(pack_key, lang):
    p = PACKS[pack_key][lang]
    cells_html = "".join(f'<div class="cell">{c}</div>' for c in GRID_CELLS)
    best_badge = f'<div class="best">{BEST_BADGE[lang]}</div>' if pack_key == "pack15" else ""
    html = HTML_TEMPLATE.format(
        w=COVER_W, h=COVER_H,
        title=TITLE[lang], subtitle=SUBTITLE[lang],
        count=p["count"], label=p["label"], price=p["price"],
        cells=cells_html, best_badge=best_badge,
    )
    return html


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page(viewport={"width": COVER_W, "height": COVER_H}, device_scale_factor=2)
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
