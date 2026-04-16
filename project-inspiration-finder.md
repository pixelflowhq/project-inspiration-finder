# Project Inspiration Finder — Chat Transcript

---

## User

Start planning for a research agent that I want to build. I want to find sources that can give inspiration for side projects to build, e.g. reddit.com/r/sideproject, hacker news etc. So find me a list of good sources to use. Then create a plan for developing an autonomous agent (or multiple agents working together) that carries out the research, summarises and sends me the summaries.

---

## Assistant

### Sources

**Tier 1 — high signal, active, developer-focused:**
- `reddit.com/r/SideProject` — projects people are actually building/sharing
- `reddit.com/r/InternetIsBeautiful` — launched tools, lots of "I built this" posts
- `reddit.com/r/webdev` + `r/programming` — pain points → project ideas
- **Hacker News** (`news.ycombinator.com`) — "Show HN" posts are gold: real builders sharing what they made
- **Indie Hackers** (`indiehackers.com`) — products with revenue numbers, very structured
- **Product Hunt** (`producthunt.com`) — daily launches, trending categories
- **GitHub Trending** — what developers are actually starring and building right now

**Tier 2 — good supplementary signal:**
- `dev.to` — "what I built" posts, tutorials that reveal gaps
- `X/Twitter` — `#buildinpublic` hashtag, lots of builders sharing progress
- **Lobste.rs** — HN-style but more curated, has `show` tag
- `reddit.com/r/SomebodyMakeThis` — explicit problem statements from users
- **Levels.io / Nomad List blog** — indie maker philosophy, real examples

### Agent Architecture

The recommended approach is three agents working in sequence:

**Orchestrator agent** (scheduler)
Runs on a cron (e.g. daily 8am). Fans out scrape tasks to source agents, then waits for results before passing to the summariser.
Steps: Trigger → Dispatch scrapers → Collect results → Dedup + rank → Summarise → Deliver

**Scraper agents** (parallel)
- *Reddit agent* — Uses Reddit JSON API. Pulls top posts from each sub, filters by score threshold and age (<48h). Extracts title, URL, score, comment count.
- *HN agent* — Uses official Algolia HN API. Queries `Show HN` tag, last 24h, sorts by points. Fetches top 20.
- *Product Hunt agent* — Uses PH GraphQL API. Fetches today's top posts with tagline, vote count, and topic tags.
- *GitHub Trending agent* — Scrapes github.com/trending (no auth needed). Extracts repo name, description, stars today, language.

**Summariser agent** (LLM)
- *Dedup + filter* — Remove duplicates across sources. Score each item: upvotes × recency × novelty (not seen in last 7 days).
- *Per-item summary* — Claude call per item: extract the core idea, problem it solves, tech stack mentioned, and feasibility estimate (1–3 person project?).
- *Digest compilation* — Second Claude call: take the top 10 items, write a cohesive digest grouped by theme (AI tools, dev utilities, consumer apps, etc.).
- *Novelty memory* — Persist seen item IDs to a simple store (SQLite / KV). Skip items already included in a prior digest.

**Delivery layer**
- *Email digest* — Resend / Mailgun. HTML email with 3 sections: hot today, trending this week, wild cards. Links back to originals.
- *Slack / Discord bot* — Post digest to a personal channel. Threaded: one message per item. React 🔖 to bookmark.
- *Markdown archive* — Write each digest to a dated .md file in a git repo. Full searchable history over time.
- *Optional: web UI* — Simple Next.js or Astro site reading from the archive. Filterable by source, date, theme.

### Key Design Decisions

**Two LLM calls in the summariser** rather than one: first a per-item extraction pass (cheap, structured JSON output), then a single digest compilation call that groups the best 10 into a readable narrative. Much cheaper and more reliable than one giant prompt.

**Novelty memory** — a SQLite table of seen item URLs with a timestamp, planned from day one. Without it the digest gets repetitive within a week.

**Recommended tech stack:** Python with `asyncio` + `httpx` for scrapers, Anthropic SDK for the summariser, `resend` for email delivery, `schedule` or a cron job for the trigger. Fits in a single repo and runs cheaply on a small VPS or GitHub Actions scheduled workflow.

---

## User

For sources that have official APIs, are they free or require a paid subscription?

---

## Assistant

### API Pricing Breakdown

**Hacker News — fully free, no key needed.**
Both the official Firebase API and the Algolia search API are completely open, requiring no API keys or auth. Best situation of any source on the list.

**Reddit — technically free for personal/non-commercial use, but complicated.**
The Reddit API uses a freemium model. Non-commercial personal projects can use it for free, though with significant limitations. The paid tier runs $0.24 per 1,000 API calls for large-scale use. For a personal research agent running once a day across a handful of subreddits, 100 requests per minute for OAuth applications is more than enough — you'd stay well within the free tier. The main nuance is that Reddit's terms distinguish personal from commercial use, so as long as this is for your own inspiration digest and not a product you're selling, you're fine.

**Product Hunt — free but restricted.**
The API is accessible with a free OAuth access token, but must not be used for commercial purposes. Fine for a personal agent. One catch: there are rate limits and PH reserves the right to throttle without much notice.

**GitHub Trending — no API, but free to scrape.**
GitHub doesn't have an official trending API. The trending page at `github.com/trending` is plain HTML, no auth needed, freely scrapeable.

**Indie Hackers — no official API.**
No public API. You'd need to scrape it directly, which is possible but fragile.

**X/Twitter `#buildinpublic` — now pay-per-use, but affordable at small scale.**
X replaced its fixed-tier plans with pay-per-use pricing — post reads cost $0.005 each. At that rate, reading 1,000 posts/month costs $5. For a daily digest grabbing 20–30 posts, you're looking at pennies. That said, X has changed its API terms aggressively since 2023, so it's a calculated risk to build on.

### Summary Table

| Source | API? | Cost | Recommendation |
|---|---|---|---|
| Hacker News | ✅ Official (Firebase + Algolia) | Free, no key | Use it — best option |
| Reddit | ✅ Official | Free (personal use) | Use it — stay non-commercial |
| Product Hunt | ✅ Official GraphQL | Free (non-commercial) | Use it — register an app |
| GitHub Trending | ❌ Scrape HTML | Free | Use it — very stable page |
| Indie Hackers | ❌ Scrape HTML | Free | Lower priority — fragile |
| X `#buildinpublic` | ✅ Official | ~$5/month at low volume | Optional — treat as risk |

You could realistically run the whole agent for **£0/month** by sticking to HN, Reddit, Product Hunt, and GitHub Trending.

---

## User

Save this chat transcript to a file named project-inspiration-finder.md

---

*Transcript saved on 2026-04-15*
