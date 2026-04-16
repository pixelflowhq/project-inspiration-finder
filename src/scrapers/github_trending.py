import httpx
from bs4 import BeautifulSoup

URL = "https://github.com/trending"


async def fetch(client: httpx.AsyncClient) -> list[dict]:
    r = await client.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for repo in soup.select("article.Box-row"):
        name_tag = repo.select_one("h2 a")
        if not name_tag:
            continue
        path = name_tag["href"].strip()
        desc_tag = repo.select_one("p")
        desc = desc_tag.get_text(strip=True) if desc_tag else ""
        stars_tag = repo.select_one("span.d-inline-block.float-sm-right")
        stars_today = stars_tag.get_text(strip=True) if stars_tag else "?"
        items.append({
            "url": f"https://github.com{path}",
            "title": path.lstrip("/").replace("/", " / "),
            "score": max(1, 20 - len(items)),  # rank-based score
            "description": desc,
            "stars_today": stars_today,
            "source": "github_trending",
        })
    return items[:20]
