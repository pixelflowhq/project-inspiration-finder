import os

import httpx

BASE_URL = "https://api.etsy.com/v3/application"

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
    shared_secret = os.environ.get("ETSY_SHARED_SECRET")
    if not api_key:
        print("Skipping Etsy: missing ETSY_API_KEY.")
        return []
    if not shared_secret:
        print("Skipping Etsy: missing ETSY_SHARED_SECRET.")
        return []

    # Etsy's v3 docs currently specify x-api-key as "keystring:shared_secret".
    etsy_auth = f"{api_key}:{shared_secret}"
    headers = {"x-api-key": etsy_auth}

    ping = await client.get(f"{BASE_URL}/openapi-ping", headers=headers)
    try:
        ping.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.strip()
        if len(body) > 500:
            body = f"{body[:500]}..."
        print(
            "Etsy auth check failed at /openapi-ping "
            f"(status={exc.response.status_code}): {body or '<empty response>'}"
        )
        print(
            "Check that your Etsy app is approved and that ETSY_API_KEY / "
            "ETSY_SHARED_SECRET exactly match the keystring and shared secret from Etsy."
        )
        raise

    items = []
    seen: set[str] = set()

    for term in SEARCH_TERMS:
        r = await client.get(
            f"{BASE_URL}/listings/active",
            params={
                "keywords": term,
                "sort_on": "score",
                "limit": 10,
            },
            headers=headers,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text.strip()
            if len(body) > 500:
                body = f"{body[:500]}..."
            print(
                "Etsy request failed "
                f"(status={exc.response.status_code}, term={term!r}): {body or '<empty response>'}"
            )
            raise
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

    print(f"Etsy: {len(items)} items fetched across {len(SEARCH_TERMS)} search terms.")
    return items
