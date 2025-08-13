from playwright.async_api import async_playwright

async def launch_browser(headless: bool = False):
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    return p, browser, page