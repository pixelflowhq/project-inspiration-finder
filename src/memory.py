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
