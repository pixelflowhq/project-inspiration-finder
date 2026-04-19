# Project Inspiration Finder

A daily digest agent that scrapes developer and maker communities, deduplicates across runs, summarises with Claude, and delivers a markdown digest + optional email. Runs automatically on GitHub Actions every morning.

## What it does

1. Scrapes five sources in parallel each day
2. Filters out anything seen in a previous digest
3. Ranks and sends the top 20 items to Claude for a two-pass summary
4. Writes a dated markdown file to `digests/` and optionally emails it via Resend
5. Commits `seen_items.json` and the new digest back to the repo

## Sources

| Source | Method | Auth |
|---|---|---|
| Hacker News (Show HN) | Algolia API | None |
| GitHub Trending | HTML scrape | None |
| Reddit (33 subreddits) | Data API — OAuth | Client credentials |
| Product Hunt | GraphQL API | Token |
| Etsy digital products | REST API | API key |

Reddit subreddits include: `SideProject`, `SomebodyMakeThis`, `microsaas`, `SaaS`, `startups`, `Entrepreneur`, `buildinpublic`, `indiehackers`, `AppIdeas`, `vibecoding`, and more.

Etsy searches 31 digital product categories: Notion templates, spreadsheet tools, planners, pitch decks, branding kits, Airtable templates, course templates, and more.

## Setup

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys. Only `ANTHROPIC_API_KEY` is required to run locally — all other sources skip cleanly if their credentials are absent.

### 3. Run locally

```bash
python -m src.main
```

Output: `digests/YYYY-MM-DD.md` and an updated `seen_items.json`.

## GitHub Actions setup

The workflow at [.github/workflows/digest.yml](.github/workflows/digest.yml) runs daily at 8am UTC.

Add these secrets under **Settings → Secrets and variables → Actions**:

| Secret | Required | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | console.anthropic.com |
| `REDDIT_CLIENT_ID` | Optional | reddit.com/prefs/apps (web app, redirect `https://example.com`) |
| `REDDIT_CLIENT_SECRET` | Optional | Same Reddit app |
| `REDDIT_USER_AGENT` | Optional | e.g. `server:project-inspiration-finder:v1 (by /u/yourname)` |
| `PRODUCT_HUNT_TOKEN` | Optional | producthunt.com/v2/oauth/applications |
| `ETSY_API_KEY` | Optional | developers.etsy.com |
| `RESEND_API_KEY` | Optional | resend.com |
| `EMAIL_FROM` | Optional | Verified sender in Resend |
| `EMAIL_TO` | Optional | Your email address |

After adding secrets, trigger a test run manually: **Actions → Daily Inspiration Digest → Run workflow**.

## Repository structure

```
├── .github/workflows/digest.yml   # cron job — runs daily, commits results
├── src/
│   ├── scrapers/
│   │   ├── hackernews.py          # Algolia HN API
│   │   ├── reddit.py              # Reddit OAuth Data API
│   │   ├── github_trending.py     # HTML scrape
│   │   ├── producthunt.py         # GraphQL API
│   │   └── etsy.py                # REST API — digital listings
│   ├── memory.py                  # Read/write seen_items.json
│   ├── summariser.py              # Two-pass Claude summarisation
│   ├── delivery.py                # Write .md digest + Resend email
│   └── main.py                    # Orchestrator
├── digests/                       # One .md file per run, committed to repo
├── seen_items.json                # Novelty memory — persisted via git commit
├── requirements.txt
└── .env.example
```

## Cost

| Item | Cost |
|---|---|
| GitHub Actions | Free |
| Anthropic API (~2 calls/day) | ~$2–5/month |
| Resend (1 email/day) | Free |
| All data sources | Free |
| **Total** | **~$2–5/month** |
