import asyncio
from datetime import date

import httpx
from dotenv import load_dotenv

from src import delivery, memory, summariser
from src.scrapers import github_trending, hackernews, producthunt, reddit

load_dotenv()

MIN_NEW_ITEMS = 3


async def run():
    today = date.today().isoformat()
    mem = memory.load()

    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(
            hackernews.fetch(client),
            reddit.fetch(client),
            github_trending.fetch(client),
            producthunt.fetch(client),
            return_exceptions=True,  # partial failure: don't abort if one scraper fails
        )

    all_items = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Scraper failed: {result}")
            continue
        all_items.extend(result)

    # Deduplicate within this run by URL, then filter against seen memory
    seen_urls: set[str] = set()
    new_items = []
    for item in all_items:
        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if memory.is_new(url, mem):
            new_items.append(item)

    if len(new_items) < MIN_NEW_ITEMS:
        print(f"Only {len(new_items)} new item(s) — below threshold of {MIN_NEW_ITEMS}. Skipping digest.")
        return

    def rank(item: dict) -> tuple[int, int]:
        if item["source"].startswith("reddit/"):
            boost = 3
        else:
            boost = {"hackernews": 3, "producthunt": 3, "github_trending": 2}.get(item["source"], 1)
        return (boost, int(item.get("score", 0)))

    new_items.sort(key=rank, reverse=True)
    top_items = new_items[:20]

    digest = await summariser.summarise(top_items, today)

    delivery.write_digest(digest, today)
    delivery.send_email(digest, today)  # best-effort; skips if no key

    # Persist memory only after the markdown archive succeeds
    for item in top_items:
        memory.mark_seen(item["url"], item["title"], item["source"], today, mem)
    memory.save(mem)


if __name__ == "__main__":
    asyncio.run(run())
