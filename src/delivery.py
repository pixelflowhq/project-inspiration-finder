import os
from html import escape
from pathlib import Path

import resend

DIGEST_DIR = Path("digests")
DIGEST_DIR.mkdir(exist_ok=True)


def write_digest(content: str, date: str) -> None:
    path = DIGEST_DIR / f"{date}.md"
    path.write_text(
        f"---\nlayout: post\ntitle: Inspiration Digest — {date}\ndate: {date}\n---\n\n{content}\n"
    )
    print(f"Digest written to {path}")


def render_html_email(content: str, date: str) -> str:
    blocks = [block.strip() for block in content.strip().split("\n\n") if block.strip()]
    rendered_blocks: list[str] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        if len(lines) == 1 and not lines[0].startswith(("- ", "* ")):
            line = lines[0]
            if line.endswith(":"):
                rendered_blocks.append(
                    f"<h2 style=\"margin:24px 0 12px;font-size:20px;line-height:1.3;\">{escape(line[:-1])}</h2>"
                )
            else:
                rendered_blocks.append(
                    f"<p style=\"margin:0 0 16px;line-height:1.6;\">{escape(line)}</p>"
                )
            continue

        list_items = []
        for line in lines:
            if line.startswith("- "):
                text = line[2:]
            elif line.startswith("* "):
                text = line[2:]
            else:
                text = line
            list_items.append(f"<li style=\"margin:0 0 10px;\">{escape(text)}</li>")

        rendered_blocks.append(
            "<ul style=\"margin:0 0 18px;padding-left:20px;line-height:1.6;\">"
            + "".join(list_items)
            + "</ul>"
        )

    body = "".join(rendered_blocks) or f"<p style=\"line-height:1.6;\">{escape(content)}</p>"
    return (
        "<!doctype html>"
        "<html><body style=\"margin:0;padding:0;background:#f6f3ee;color:#1f2937;\">"
        "<div style=\"max-width:680px;margin:0 auto;padding:32px 20px;font-family:Georgia,'Times New Roman',serif;\">"
        f"<h1 style=\"margin:0 0 8px;font-size:28px;line-height:1.2;\">Inspiration Digest</h1>"
        f"<p style=\"margin:0 0 28px;color:#6b7280;font-size:14px;\">{escape(date)}</p>"
        "<div style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:24px;\">"
        f"{body}"
        "</div>"
        "</div></body></html>"
    )


def send_email(content: str, date: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("No RESEND_API_KEY set, skipping email.")
        return
    resend.api_key = api_key
    resend.Emails.send({
        "from": os.environ["EMAIL_FROM"],
        "to": [os.environ["EMAIL_TO"]],
        "subject": f"Inspiration Digest — {date}",
        "text": content,
        "html": render_html_email(content, date),
    })
    print("Email sent.")
