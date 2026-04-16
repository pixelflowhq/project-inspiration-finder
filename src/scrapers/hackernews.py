import time

import httpx

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


async def fetch(client: httpx.AsyncClient, hours_back: int = 24) -> list[dict]:
    since = int(time.time()) - (hours_back * 3600)
    params = {
        "tags": "show_hn",
        "numericFilters": f"created_at_i>{since},points>10",
        "hitsPerPage": 30,
    }
    r = await client.get(ALGOLIA_URL, params=params)
    r.raise_for_status()
    items = []
    for hit in r.json()["hits"]:
        items.append({
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "title": hit["title"],
            "score": hit["points"],
            "source": "hackernews",
        })
    return items
