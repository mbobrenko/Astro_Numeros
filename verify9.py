import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page = await b.new_page(viewport={"width":1000,"height":1600})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto("file:///home/claude/app2/index.html")
        await page.wait_for_timeout(400)

        # basic calc already happened (default values); check tabs render
        print("page errors after load:", errors)

        # switch to Графики tab -> should show paywall, not the real chart data
        await page.get_by_role("button", name="Графики", exact=True).click()
        await page.wait_for_timeout(200)
        graphs_text = await page.locator("#tab-graphs").inner_text()
        print("\n--- Графики tab (should be paywall, not chart) ---")
        print(graphs_text[:400])
        assert "Открыть бесплатно" in graphs_text or "Войдите через Telegram" in graphs_text, "paywall not shown"
        assert "Баллы (график" not in graphs_text, "chart leaked without unlock!"
        print("OK: Графики tab is gated (paywall shown, no chart leak)")

        # authbar should show telegram widget slot (bot username not configured -> empty, that's fine)
        authbar_html = await page.locator("#authbar").inner_html()
        print("\nauthbar html (bot not configured yet, expected mostly empty):", repr(authbar_html)[:200])

        # Тарифы tab should list Free + 3 packs
        await page.get_by_role("button", name="Тарифы", exact=True).click()
        await page.wait_for_timeout(200)
        info_text = await page.locator("#tab-info").inner_text()
        print("\n--- Тарифы tab snippet ---")
        print(info_text[:600])
        for expect in ["999", "2499", "Free"]:
            assert expect in info_text, f"missing {expect} in pricing tab"
        print("OK: pricing tab shows Free + 2 packs with correct prices")

        # switch to EN, re-check graphs paywall + pricing in USD
        await page.get_by_role("button", name="EN", exact=True).click()
        await page.wait_for_timeout(300)
        await page.get_by_role("button", name="Charts", exact=True).click()
        await page.wait_for_timeout(200)
        graphs_text_en = await page.locator("#tab-graphs").inner_text()
        print("\n--- Charts tab (EN) ---")
        print(graphs_text_en[:400])
        assert "Unlock for free" in graphs_text_en or "Log in with Telegram" in graphs_text_en
        print("OK: EN paywall text correct")

        await page.get_by_role("button", name="Pricing", exact=True).click()
        await page.wait_for_timeout(200)
        info_text_en = await page.locator("#tab-info").inner_text()
        print("\n--- Pricing tab (EN) snippet ---")
        print(info_text_en[:600])
        for expect in ["14.99", "34.99"]:
            assert expect in info_text_en, f"missing {expect} in EN pricing tab"
        print("OK: EN pricing tab shows USD prices")

        print("\nfinal page errors:", errors)
        assert not errors, f"JS errors occurred: {errors}"
        await page.screenshot(path="/tmp/v9_paywall_en.png", full_page=True)
        await b.close()

asyncio.run(main())
