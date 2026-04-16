import os
from datetime import date, timedelta

import httpx

PH_API = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
{
  posts(order: VOTES, postedAfter: "%s") {
    edges {
      node {
        name
        tagline
        url
        votesCount
        topics { edges { node { name } } }
      }
    }
  }
}
"""


async def fetch(client: httpx.AsyncClient) -> list[dict]:
    token = os.environ.get("PRODUCT_HUNT_TOKEN")
    if not token:
        print("Skipping Product Hunt: missing PRODUCT_HUNT_TOKEN.")
        return []
    since = (date.today() - timedelta(days=1)).isoformat() + "T00:00:00Z"
    r = await client.post(
        PH_API,
        json={"query": QUERY % since},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    r.raise_for_status()
    items = []
    for edge in r.json()["data"]["posts"]["edges"]:
        n = edge["node"]
        items.append({
            "url": n["url"],
            "title": n["name"],
            "tagline": n.get("tagline", ""),
            "score": n["votesCount"],
            "source": "producthunt",
        })
    return items[:20]
