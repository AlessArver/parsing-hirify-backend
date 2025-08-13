import asyncio
import os
import random
from typing import List, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Page

BASE_URL = "https://hirify.me"
STORAGE_FILE = "storage.json"


class VacancyScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def __aenter__(self):
        self.p = await async_playwright().start()
        browser_args = ["--disable-blink-features=AutomationControlled"]
        self.browser = await self.p.chromium.launch(headless=self.headless, args=browser_args)

        if os.path.exists(STORAGE_FILE):
            print("📂 Загружаем cookies из storage.json")
            self.context = await self.browser.new_context(
                storage_state=STORAGE_FILE,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        else:
            print("🆕 storage.json не найден, создаём новую сессию")
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        print("💾 Сохраняем cookies в storage.json")
        await self.context.storage_state(path=STORAGE_FILE)
        await self.browser.close()
        await self.p.stop()

    async def safe_goto(self, page: Page, url: str, timeout: int = 45000, retries: int = 3) -> bool:
        for attempt in range(1, retries + 1):
            print(f"\U0001f310 Переход во вкладке {id(page)}: {url} (попытка {attempt + 1})")
            try:
                await page.goto(url, wait_until="commit", timeout=timeout)
                await asyncio.sleep(random.uniform(1.0, 2.5))
                if page.url == "about:blank":
                    print(f"⚠️ Страница осталась на about:blank, пробуем снова...")
                    continue
                return True
            except PlaywrightTimeoutError:
                print(f"❌ Timeout при загрузке {url}")
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(random.uniform(1.5, 3))
        return False

    async def human_scroll(self, page: Page):
        # Эмулируем плавную прокрутку
        print("🖱️ Прокрутка страницы")
        for _ in range(random.randint(3, 7)):
            await page.mouse.wheel(0, random.randint(100, 500))
            await asyncio.sleep(random.uniform(0.2, 0.5))

    async def get_vacancies(self, url: str) -> List[Dict]:
        page = await self.context.new_page()
        vacancies = []

        await page.bring_to_front()

        try:
            if not await self.safe_goto(page, url):
                return {"pages": 1, "vacancies": []}

            await self.human_scroll(page)

            await page.wait_for_selector("nav[data-slot='pagination']", timeout=15000)
            await page.wait_for_selector("div.vacancy-card", state="attached", timeout=20000)
            await asyncio.sleep(2)

            # Пагинация
            try:
                pagination_buttons = await page.query_selector_all("button[data-type='page']")
                pages = [
                    int(await b.get_attribute("value"))
                    for b in pagination_buttons
                    if await b.get_attribute("value") and (await b.get_attribute("value")).isdigit()
                ]
                pages = max(pages) if pages else 1
            except Exception as e:
                pages = 1
                print(f"⚠️ Ошибка при сборе пагинации: {str(e)}")

            # Сбор карточек вакансий
            vacancy_cards = await page.query_selector_all("div.vacancy-card")
            print("\U0001f7e0 Загружено карточек:", len(vacancy_cards))

            for card in vacancy_cards:
                title = await (await card.query_selector("h2.title")).inner_text()
                link = await (await card.query_selector("a.vacancy-card-link")).get_attribute("href")

                company_el = await card.query_selector("div.company")
                company = (await company_el.inner_text()).strip() if company_el else None

                date_el = await card.query_selector("div.date")
                date = (await date_el.inner_text()).strip() if date_el else None

                salary_div = await card.query_selector("div.salary")
                salary = None
                if salary_div:
                    amount_el = await salary_div.query_selector("span:nth-child(1)")
                    currency_el = await salary_div.query_selector("span:nth-child(2)")
                    salary = {
                        "amount": await amount_el.inner_text(),
                        "currency": await currency_el.inner_text(),
                    }

                if title and link:
                    vacancies.append(
                        {
                            "title": title.strip(),
                            "company": company,
                            "link": BASE_URL + link,
                            "contacts": {},
                            "salary": salary,
                            "date": date,
                        }
                    )
                else:
                    print("⚠️ Не найдена ссылка/заголовок в карточке:\n")

            return {
                "pages": pages,
                "vacancies": vacancies,
            }
        except PlaywrightTimeoutError:
            return {"pages": 1, "vacancies": []}
        finally:
            await page.close()

    async def _extract_contacts_on_page(self, page: Page, vacancy_link: str) -> Dict:
        if not await self.safe_goto(page, vacancy_link):
            return {"error": f"timeout for {vacancy_link}"}

        btn1 = page.locator("button.contact-placeholder-btn")
        if await btn1.count() > 0:
            print("✅ Нашли contact-placeholder-btn, вызываем handleVacancyApply() напрямую")
            await page.evaluate("window.handleVacancyApply()")
        else:
            btn2 = page.locator("div.vacancy-header .apply button")
            if await btn2.count() < 0:
                print("❌ Кнопка для показа контактов не найдена")
                return {"error": "contacts button not found"}
            print("⚠️ Нашли .apply button, пробуем кликнуть")
            await btn2.click(force=True)

        await page.wait_for_timeout(1000)
        modal = await page.wait_for_selector("div[role='dialog']", state="visible", timeout=5000)
        if not modal:
            return {"error": "modal not appeared after click"}

        contacts = {}
        items = await modal.query_selector_all("a.application-channel-item")
        for item in items:
            label_el = await item.query_selector("b")
            val_el = await item.query_selector("span")
            if label_el and val_el:
                label = (await label_el.inner_text()).lower().strip().rstrip(":")
                value = await val_el.inner_text()

                contacts[label] = value

        return contacts if contacts else {"info": "dialog opened, but no contacts"}

    async def extract_contacts(self, vacancy_link: str) -> Dict:
        page = await self.context.new_page()
        await page.bring_to_front()

        try:
            return await self._extract_contacts_on_page(page, vacancy_link)
        finally:
            await page.close()
