import asyncio, os
from playwright.async_api import async_playwright

svgs = {
    "arquitetura_iam":     "app/static/report-assets/arquitetura_iam.svg",
    "evidencias_dashboard":"app/static/report-assets/evidencias_dashboard.svg",
    "fluxo_jml":           "app/static/report-assets/fluxo_jml.svg",
    "matriz_rbac":         "app/static/report-assets/matriz_rbac.svg",
}
os.makedirs("docs/imagens", exist_ok=True)

async def convert():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 700})
        for name, src in svgs.items():
            svg_content = open(src, encoding="utf-8").read()
            html = (
                "<!DOCTYPE html><html><body style='margin:0;padding:0;background:white'>"
                + svg_content
                + "</body></html>"
            )
            await page.set_content(html)
            await page.wait_for_timeout(800)
            out = f"docs/imagens/{name}.png"
            await page.screenshot(path=out, timeout=15000)
            print(f"OK: {out}")
        await browser.close()

asyncio.run(convert())
