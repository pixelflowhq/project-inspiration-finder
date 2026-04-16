import json

import anthropic

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

DIGEST_SYSTEM = """You are writing a daily inspiration digest for a software developer
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
            "content": f"Extract structured data for these items:\n\n{json.dumps(items, indent=2)}",
        }],
    )
    extracted_text = extraction_response.content[0].text
    # Strip markdown code fences if present
    if "```" in extracted_text:
        extracted_text = extracted_text.split("```")[1].lstrip("json").strip()
    try:
        extracted = json.loads(extracted_text)
    except json.JSONDecodeError:
        # Fallback for unattended runs: still produce a digest from raw items
        extracted = items

    # Pass 2: digest compilation
    digest_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=DIGEST_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Write the digest for {date}. Items:\n\n{json.dumps(extracted, indent=2)}",
        }],
    )
    return digest_response.content[0].text
