# Implementation Plan — Project Inspiration Finder

**Stack:** Python 3.12, GitHub Actions (cron), Anthropic SDK, Resend (email)
**State:** JSON file committed back to the repo after each successful digest write
**Delivery:** Markdown digest files + email via Resend

---

## Reddit Access Decision

Use Reddit's official Data API with OAuth. Do not rely on unauthenticated
`reddit.com/*.json` endpoints for this project.

Why:
- Reddit's current Data API help docs require authentication with a registered
  OAuth token for Data API use.
- The same docs say free access is rate-limited to 100 queries per minute per
  OAuth client id, averaged over a 10-minute window.
- That means a small personal daily digest is comfortably within the free tier,
  but it still needs app registration and token handling.

Practical setup for this project:
- Create a Reddit app at `https://www.reddit.com/prefs/apps`
- Use a confidential app for this server-side cron job
- Store the client id, client secret, and a descriptive User-Agent in secrets
- Acquire an OAuth token before calling `oauth.reddit.com`
- Start with read-only subreddit listing access only

Implementation stance:
- Keep Reddit in the MVP
- Treat missing Reddit credentials as a cleanly skipped source
- Do not describe Reddit as "no-auth public JSON" in the implementation plan

---

## Repository Structure

```
project-inspiration-finder/
├── .github/
│   └── workflows/
│       └── digest.yml          # cron trigger + job definition
├── src/
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── hackernews.py       # Algolia HN API
│   │   ├── reddit.py           # Reddit Data API via OAuth
│   │   ├── producthunt.py      # PH GraphQL API
│   │   └── github_trending.py  # HTML scrape of github.com/trending
│   ├── summariser.py           # Two-pass Anthropic SDK calls
│   ├── delivery.py             # Write .md digest + send email via Resend
│   ├── memory.py               # Read/write seen_items.json
│   └── main.py                 # Orchestrator: run all scrapers → summarise → deliver
├── digests/                    # Output: one .md file per run, committed to repo
├── seen_items.json             # Novelty memory: persisted between runs via git commit
├── requirements.txt
└── .env.example
```

---

## Phase 1 — Scaffold and scrapers (Day 1)

### 1.1 Repo setup

```bash
git init project-inspiration-finder
cd project-inspiration-finder
python -m venv .venv && source .venv/bin/activate
pip install httpx anthropic resend python-dotenv beautifulsoup4
pip freeze > requirements.txt
```

### 1.2 `seen_items.json` schema

A flat JSON object. Key is the item URL (canonical dedup key). Value is metadata.

```json
{
  "https://news.ycombinator.com/item?id=12345": {
    "title": "Show HN: I built a thing",
    "source": "hackernews",
    "first_seen": "2026-04-16",
    "digest_dates": ["2026-04-16"],
    "last_delivery": "markdown"
  }
}
```

### 1.3 `src/memory.py`

```python
import json
from pathlib import Path

MEMORY_PATH = Path("seen_items.json")

def load() -> dict:
    if not MEMORY_PATH.exists():
        return {}
    return json.loads(MEMORY_PATH.read_text())

def save(memory: dict) -> None:
    MEMORY_PATH.write_text(json.dumps(memory, indent=2))

def is_new(url: str, memory: dict) -> bool:
    return url not in memory

def mark_seen(url: str, title: str, source: str, date: str, memory: dict) -> None:
    if url in memory:
        memory[url]["digest_dates"].append(date)
    else:
        memory[url] = {
            "title": title,
            "source": source,
            "first_seen": date,
            "digest_dates": [date],
            "last_delivery": "markdown",
        }
```

### 1.4 Scraper: `src/scrapers/hackernews.py`

Uses the Algolia HN API — no auth, no key.

```python
import httpx

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"

async def fetch(client: httpx.AsyncClient, hours_back: int = 24) -> list[dict]:
    import time
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
```

### 1.5 Scraper: `src/scrapers/reddit.py`

Uses Reddit's official Data API with OAuth. This remains viable for a personal,
non-commercial digest in the free tier, but it requires app registration and a
token exchange.

Setup involved:
- Create a Reddit app at `https://www.reddit.com/prefs/apps`
- Use a confidential app for this server-side cron job
- Add `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT` to secrets
- Acquire an OAuth token before calling `https://oauth.reddit.com`
- Keep the scope/read surface minimal

For this project, missing Reddit credentials should not fail the full run. The
scraper should return an empty list and log that Reddit was skipped.

Implementation note:
- Start with application-only OAuth for read-only fetching
- If Reddit's current endpoint behavior requires user-context auth for the
  chosen listing endpoints, switch the Reddit scraper to a script-style user
  token flow without changing the rest of the pipeline design

```python
import httpx
import os

SUBREDDITS = ["SideProject", "InternetIsBeautiful", "SomebodyMakeThis"]
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
        r.raise_for_status()
        for post in r.json()["data"]["children"]:
            d = post["data"]
            if d["score"] < min_score or d.get("is_self") is False and not d.get("url"):
                continue
            items.append({
                "url": f"https://reddit.com{d['permalink']}",
                "title": d["title"],
                "score": d["score"],
                "num_comments": d["num_comments"],
                "source": f"reddit/r/{sub}",
            })
    return items
```

### 1.6 Scraper: `src/scrapers/github_trending.py`

Scrapes the plain HTML trending page — no auth needed.

```python
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
            "score": max(1, 20 - len(items)),  # derive a rank-based score
            "description": desc,
            "stars_today": stars_today,
            "source": "github_trending",
        })
    return items[:20]
```

### 1.7 Scraper: `src/scrapers/producthunt.py`

Uses Product Hunt's GraphQL API — requires a free API token (register at
producthunt.com/v2/oauth/applications).

```python
import httpx
import os

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
    from datetime import date, timedelta
    token = os.environ.get("PRODUCT_HUNT_TOKEN")
    if not token:
        return []
    since = (date.today() - timedelta(days=1)).isoformat() + "T00:00:00Z"
    r = await client.post(
        PH_API,
        json={"query": QUERY % since},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
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
```

---

## Phase 2 — Orchestrator and dedup (Day 1–2)

### 2.1 `src/main.py`

```python
import asyncio
import httpx
from datetime import date
from src.scrapers import hackernews, reddit, github_trending, producthunt
from src import memory, summariser, delivery

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
            print(f"Scraper failed: {result}")  # log and continue
            continue
        all_items.extend(result)

    # Dedup by URL, filter already-seen items
    seen_urls = set()
    new_items = []
    for item in all_items:
        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if memory.is_new(url, mem):
            new_items.append(item)

    if not new_items:
        print("No new items today.")
        return

    def rank(item: dict) -> tuple[int, int]:
        source_boost = {
            "hackernews": 3,
            "producthunt": 3,
            "github_trending": 2,
        }
        if item["source"].startswith("reddit/"):
            boost = 3
        else:
            boost = source_boost.get(item["source"], 1)
        return (boost, int(item.get("score", 0)))

    new_items.sort(key=rank, reverse=True)
    top_items = new_items[:20]  # send top 20 to summariser

    digest = await summariser.summarise(top_items, today)

    delivery.write_digest(digest, today)
    delivery.send_email(digest, today)  # best-effort delivery

    # Persist memory only after the markdown archive succeeds
    for item in top_items:
        memory.mark_seen(item["url"], item["title"], item["source"], today, mem)
    memory.save(mem)

if __name__ == "__main__":
    asyncio.run(run())
```

---

## Phase 3 — Summariser (Day 2)

### 3.1 `src/summariser.py`

Two-pass approach: per-item extraction → digest compilation.

```python
import anthropic
import json

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

EXTRACT_SYSTEM = """You are a research assistant. Given a list of projects/posts,
extract structured data for each. Return a JSON array. Each object must have:
- title (str)
- url (str)
- source (str)
- core_idea (str, 1 sentence: what does it do?)
- problem_solved (str, 1 sentence: what pain does it address?)
- tech_stack (str, comma-separated or "unknown")
- feasibility (str: "solo weekend" | "1-2 weeks" | "1-3 months" | "large team")
- theme (str: one of "AI/ML" | "Dev tools" | "Consumer" | "Productivity" | "Data" | "Other")
"""

DIGEST_SYSTEM = """You are writing a weekly inspiration digest for a software developer
looking for side project ideas. Write in a clean, direct style. No fluff.
Group items by theme. For each item: one punchy sentence on the idea, one on why it's
interesting, and a link. End with a "Wild cards" section for the most unusual items.
"""

async def summarise(items: list[dict], date: str) -> str:
    # Pass 1: structured extraction (one call, all items)
    extraction_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=EXTRACT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Extract structured data for these items:\n\n{json.dumps(items, indent=2)}"
        }],
    )
    extracted_text = extraction_response.content[0].text
    # Strip markdown code fences if present
    if "```" in extracted_text:
        extracted_text = extracted_text.split("```")[1].lstrip("json").strip()
    try:
        extracted = json.loads(extracted_text)
    except json.JSONDecodeError:
        # Fallback for unattended runs: still produce a digest from raw items.
        extracted = items

    # Pass 2: digest compilation
    digest_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=DIGEST_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Write the digest for {date}. Items:\n\n{json.dumps(extracted, indent=2)}"
        }],
    )
    return digest_response.content[0].text
```

---

## Phase 4 — Delivery (Day 2)

### 4.1 `src/delivery.py`

```python
import os
import resend
from pathlib import Path

DIGEST_DIR = Path("digests")
DIGEST_DIR.mkdir(exist_ok=True)

def write_digest(content: str, date: str) -> None:
    path = DIGEST_DIR / f"{date}.md"
    path.write_text(f"# Inspiration Digest — {date}\n\n{content}\n")
    print(f"Digest written to {path}")

def send_email(content: str, date: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("No RESEND_API_KEY set, skipping email.")
        return
    resend.api_key = api_key
    resend.Emails.send({
        "from": os.environ["EMAIL_FROM"],      # e.g. digest@yourdomain.com
        "to": [os.environ["EMAIL_TO"]],
        "subject": f"Inspiration Digest — {date}",
        "text": content,
    })
    print("Email sent.")
```

---

## Phase 5 — GitHub Actions workflow (Day 3)

### 5.1 `.github/workflows/digest.yml`

```yaml
name: Daily Inspiration Digest

on:
  schedule:
    - cron: '0 8 * * *'   # 8am UTC every day
  workflow_dispatch:        # manual trigger for testing

jobs:
  run-digest:
    runs-on: ubuntu-latest
    permissions:
      contents: write       # needed to commit seen_items.json and digests/

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}
          PRODUCT_HUNT_TOKEN: ${{ secrets.PRODUCT_HUNT_TOKEN }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          EMAIL_FROM: ${{ secrets.EMAIL_FROM }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
        run: python -m src.main

      - name: Commit state and digest
        run: |
          git config user.name "digest-bot"
          git config user.email "bot@noreply.github.com"
          git add seen_items.json digests/
          git diff --staged --quiet || git commit -m "chore: digest $(date -u +%Y-%m-%d) [skip ci]"
          git push
```

The `[skip ci]` tag in the commit message prevents the push from re-triggering the workflow.

---

## Phase 6 — Secrets setup

In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `REDDIT_CLIENT_ID` | From the Reddit app you create at `reddit.com/prefs/apps` |
| `REDDIT_CLIENT_SECRET` | From the same Reddit app |
| `REDDIT_USER_AGENT` | Unique descriptive string, e.g. `server:project-inspiration-finder:v1 (by /u/yourname)` |
| `PRODUCT_HUNT_TOKEN` | From producthunt.com/v2/oauth/applications |
| `RESEND_API_KEY` | From resend.com (free tier: 3,000 emails/month) |
| `EMAIL_FROM` | Verified sender address in Resend |
| `EMAIL_TO` | Your personal email address |

Product Hunt and Resend are optional for an initial test run. Reddit is also
optional in the sense that the pipeline should skip that source cleanly when its
credentials are not configured, but the intended production path is OAuth-backed
Data API access rather than unauthenticated JSON fetching.

---

## `.env.example`

```
ANTHROPIC_API_KEY=sk-ant-...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=server:project-inspiration-finder:v1 (by /u/yourname)
PRODUCT_HUNT_TOKEN=...
RESEND_API_KEY=re_...
EMAIL_FROM=digest@yourdomain.com
EMAIL_TO=you@youremail.com
```

---

## Implementation Order

1. **Day 1 — working scrapers**
   - Set up repo and venv
   - Implement `memory.py`
   - Implement HN, GitHub Trending, and Product Hunt scrapers
   - Register the Reddit app and implement OAuth-backed Reddit access
   - Test each scraper locally: `python -c "import asyncio; from src.scrapers import hackernews; ..."`

2. **Day 2 — pipeline end to end**
   - Implement `main.py` orchestrator
   - Implement `summariser.py` (test with a hardcoded list of 5 items first)
   - Implement `delivery.py` (markdown write first, email second)
   - Run the full pipeline locally: `python -m src.main`
   - Verify `seen_items.json` is written and `digests/YYYY-MM-DD.md` exists

3. **Day 3 — GitHub Actions**
   - Push repo to GitHub (private)
   - Add all secrets
   - Add `digest.yml` workflow
   - Trigger manually with `workflow_dispatch` to verify end-to-end in CI
   - Check the Actions log for any scraper failures
   - Confirm the bot commit appears in the repo history

4. **Day 4 — hardening**
   - Add `return_exceptions=True` handling with per-scraper logging (already in plan)
   - Add a minimum threshold: if fewer than 3 new items, skip the LLM call and send nothing
   - Add retry/backoff for Reddit token fetch and 429 responses
   - Log Reddit rate-limit headers for visibility during early runs
   - Test what happens when `seen_items.json` grows large (it won't — URLs are short strings,
     1 year of daily digests ≈ a few hundred KB)

---

## Cost estimate (monthly)

| Item | Cost |
|---|---|
| GitHub Actions | Free (well under 2,000 min/month) |
| Anthropic API (2 calls/day × 30) | ~$2–5/month depending on item count |
| Resend (1 email/day) | Free (under 3,000/month) |
| Product Hunt API | Free |
| Reddit / HN / GitHub Trending | Free |
| **Total** | **~$2–5/month** |
