import os

import httpx

SUBREDDITS = [
    "SideProject",
    "InternetIsBeautiful",
    "SomebodyMakeThis",
    "buildinpublic",
    "AppBusiness",
    "microsaas",
    "micro_saas",
    "scaleinpublic",
    "SaasDevelopers",
    "Entrepreneur",
    "productivity",
    "business",
    "smallbusiness",
    "startups",
    "passive_income",
    "EntrepreneurRideAlong",
    "Business_Ideas",
    "SaaS",
    "startup",
    "Startup_Ideas",
    "thesidehustle",
    "juststart",
    "ycombinator",
    "Entrepreneurs",
    "indiehackers",
    "GrowthHacking",
    "AppIdeas",
    "growmybusiness",
    "Solopreneur",
    "vibecoding",
    "startup_resources",
    "indiebiz",
    "AlphaandBetaUsers",
]
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
BASE_URL = "https://oauth.reddit.com"


async def get_access_token(client: httpx.AsyncClient) -> str | None:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT")
    if not client_id or not client_secret or not user_agent:
        return None

    r = await client.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        headers={"User-Agent": user_agent},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def fetch(client: httpx.AsyncClient, min_score: int = 50) -> list[dict]:
    token = await get_access_token(client)
    if not token:
        print("Skipping Reddit: missing OAuth credentials.")
        return []

    user_agent = os.environ["REDDIT_USER_AGENT"]
    items = []
    for sub in SUBREDDITS:
        r = await client.get(
            f"{BASE_URL}/r/{sub}/top",
            params={"limit": 25, "t": "day", "raw_json": 1},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": user_agent,
            },
        )
        # Log rate-limit headers for visibility during early runs
        for header in ("x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-used"):
            if header in r.headers:
                print(f"Reddit rate-limit [{sub}] {header}: {r.headers[header]}")
        r.raise_for_status()
        for post in r.json()["data"]["children"]:
            d = post["data"]
            if d["score"] < min_score:
                continue
            items.append({
                "url": f"https://reddit.com{d['permalink']}",
                "title": d["title"],
                "score": d["score"],
                "num_comments": d["num_comments"],
                "source": f"reddit/r/{sub}",
            })
    return items
