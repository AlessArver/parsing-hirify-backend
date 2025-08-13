import asyncio
from typing import Dict
from parsers.hirify import VacancyScraper
from utils.url_builder import build_url


async def get_filtered_vacancies(
    filters: Dict, page: int = 1, max_vacancies: int = 100, concurrency: int = 4, throttle: float = 0.15
) -> Dict:
    async with VacancyScraper(headless=True) as scraper:
        url = build_url(page=page, **filters)
        data = await scraper.get_vacancies(url)

        if page > data["pages"]:
            page = data["pages"]
            url = build_url(page=page, **filters)
            data = await scraper.get_vacancies(url)
            print("✅ Final URL used:", url)

        vacancies = data["vacancies"][:max_vacancies]

        q: asyncio.Queue[tuple[int, str]] = asyncio.Queue()
        for i, v in enumerate(vacancies):
            q.put_nowait((i, v["link"]))

        results: list[Dict | None] = [None] * len(vacancies)

        async def worker():
            page = await scraper.context.new_page()
            try:
                while True:
                    try:
                        i, link = await asyncio.wait_for(q.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        if q.empty():
                            break
                        continue
                    try:
                        results[i] = await scraper._extract_contacts_on_page(page, link)
                    except Exception as e:
                        results[i] = {"error": str(e)}
                    finally:
                        q.task_done()
                        if throttle:
                            await asyncio.sleep(throttle)
            finally:
                await page.close()

        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await q.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        for i, v in enumerate(vacancies):
            v["contacts"] = results[i] or {"error": "no result"}

    return {
        "success": True,
        "vacancies": vacancies,
        "pages": data["pages"],
        "page": page,
        "total_found": len(vacancies),
        "url_used": url,
    }

 