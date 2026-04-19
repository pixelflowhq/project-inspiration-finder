import os

import httpx

BASE_URL = "https://openapi.etsy.com/v3/application"

# Search terms that surface popular digital product categories on Etsy
SEARCH_TERMS = [
    # Productivity & planning
    "notion template",
    "spreadsheet template",
    "digital planner",
    "habit tracker template",
    "budget tracker spreadsheet",
    "meal planner template",
    "project management template",
    "study planner template",
    # Business & professional
    "invoice template",
    "business plan template",
    "pitch deck template",
    "contract template",
    "resume template",
    "media kit template",
    # Design & branding
    "branding kit template",
    "logo template",
    "lightroom preset",
    "procreate brush",
    # Platform-specific
    "airtable template",
    "google sheets template",
    "excel template",
    "trello template",
    "clickup template",
    # Education & content
    "online course template",
    "workbook template",
    "lesson plan template",
    # General digital
    "printable template",
    "canva template",
    "digital download tool",
    "ebook template",
    "website template",
]


async def fetch(client: httpx.AsyncClient) -> list[dict]:
    api_key = os.environ.get("ETSY_API_KEY")
    if not api_key:
        print("Skipping Etsy: missing ETSY_API_KEY.")
        return []

    headers = {"x-api-key": api_key}
    items = []
    seen: set[str] = set()

    for term in SEARCH_TERMS:
        r = await client.get(
            f"{BASE_URL}/listings/active",
            params={
                "keywords": term,
                "sort_on": "score",
                "limit": 10,
                "listing_type": "download",  # digital-only listings
            },
            headers=headers,
        )
        r.raise_for_status()
        for listing in r.json().get("results", []):
            url = f"https://www.etsy.com/listing/{listing['listing_id']}"
            if url in seen:
                continue
            seen.add(url)
            items.append({
                "url": url,
                "title": listing["title"],
                "score": listing.get("num_favorers", 0),
                "description": (listing.get("description") or "")[:200],
                "source": "etsy",
            })

    return items
