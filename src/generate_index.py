"""Regenerate index.md listing all digests in reverse chronological order."""
from pathlib import Path

DIGEST_DIR = Path("digests")
INDEX_PATH = Path("index.md")


def generate() -> None:
    digest_files = sorted(
        [f for f in DIGEST_DIR.glob("????-??-??.md")],
        reverse=True,
    )

    lines = [
        "---",
        "layout: home",
        "title: Project Inspiration Digest",
        "---",
        "",
        "A daily digest of side project ideas scraped from Hacker News, Reddit, GitHub Trending, Product Hunt, and Etsy.",
        "",
        "## Digests",
        "",
    ]

    for f in digest_files:
        date = f.stem
        lines.append(f"- [{date}](digests/{date})")

    if not digest_files:
        lines.append("_No digests yet — check back after the first run._")

    INDEX_PATH.write_text("\n".join(lines) + "\n")
    print(f"index.md updated ({len(digest_files)} digest(s) listed)")


if __name__ == "__main__":
    generate()
