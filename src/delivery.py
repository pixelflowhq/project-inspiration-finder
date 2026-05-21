import os
import re
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


def format_inline_markdown(text: str) -> str:
    formatted = escape(text)
    formatted = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2" style="color:#9a3412;text-decoration:underline;">\1</a>',
        formatted,
    )
    formatted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", formatted)
    formatted = re.sub(r"\*(.+?)\*", r"<em>\1</em>", formatted)
    return formatted


def render_html_email(content: str, date: str) -> str:
    rendered_blocks: list[str] = []
    list_items: list[str] = []
    paragraph_lines: list[str] = []

    def flush_list() -> None:
        nonlocal list_items
        if not list_items:
            return
        rendered_blocks.append(
            "<ul style=\"margin:0 0 18px;padding-left:20px;line-height:1.7;\">"
            + "".join(list_items)
            + "</ul>"
        )
        list_items = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text = " ".join(paragraph_lines).strip()
        rendered_blocks.append(
            f"<p style=\"margin:0 0 16px;line-height:1.7;\">{format_inline_markdown(text)}</p>"
        )
        paragraph_lines = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            flush_list()
            flush_paragraph()
            continue

        if line == "---":
            flush_list()
            flush_paragraph()
            rendered_blocks.append(
                "<hr style=\"border:none;border-top:1px solid #e5e7eb;margin:24px 0;\">"
            )
            continue

        if line.startswith("### "):
            flush_list()
            flush_paragraph()
            rendered_blocks.append(
                f"<h3 style=\"margin:24px 0 10px;font-size:18px;line-height:1.35;\">{format_inline_markdown(line[4:])}</h3>"
            )
            continue

        if line.startswith("## "):
            flush_list()
            flush_paragraph()
            rendered_blocks.append(
                f"<h2 style=\"margin:28px 0 12px;font-size:22px;line-height:1.3;\">{format_inline_markdown(line[3:])}</h2>"
            )
            continue

        if line.startswith("# "):
            flush_list()
            flush_paragraph()
            rendered_blocks.append(
                f"<h1 style=\"margin:0 0 16px;font-size:30px;line-height:1.2;\">{format_inline_markdown(line[2:])}</h1>"
            )
            continue

        if line.startswith(("- ", "* ")):
            flush_paragraph()
            list_items.append(
                f"<li style=\"margin:0 0 10px;\">{format_inline_markdown(line[2:])}</li>"
            )
            continue

        flush_list()
        paragraph_lines.append(line)

    flush_list()
    flush_paragraph()

    body = "".join(rendered_blocks) or f"<p style=\"line-height:1.7;\">{format_inline_markdown(content)}</p>"
    return (
        "<!doctype html>"
        "<html><body style=\"margin:0;padding:0;background:#efe7dc;color:#1f2937;\">"
        "<div style=\"max-width:720px;margin:0 auto;padding:32px 16px 48px;\">"
        "<div style=\"font-family:Arial,sans-serif;color:#9a3412;font-size:12px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;margin:0 0 14px;\">"
        "Project Inspiration Finder"
        "</div>"
        "<div style=\"background:linear-gradient(135deg,#fffaf5 0%,#f8efe2 100%);border:1px solid #e7d6bd;border-radius:24px;padding:28px 24px 22px;box-shadow:0 10px 30px rgba(120,81,45,0.08);\">"
        f"<div style=\"font-family:Georgia,'Times New Roman',serif;font-size:34px;line-height:1.1;font-weight:700;color:#111827;margin:0 0 10px;\">Inspiration Digest</div>"
        f"<div style=\"font-family:Arial,sans-serif;color:#6b7280;font-size:14px;line-height:1.5;margin:0 0 18px;\">Curated side-project ideas for {escape(date)}</div>"
        "<div style=\"height:1px;background:#eadbc7;margin:0 0 8px;\"></div>"
        "</div>"
        "<div style=\"background:#ffffff;border:1px solid #eadbc7;border-radius:24px;padding:28px 24px;margin-top:16px;"
        "font-family:Georgia,'Times New Roman',serif;font-size:17px;line-height:1.7;color:#1f2937;"
        "box-shadow:0 10px 30px rgba(120,81,45,0.06);\">"
        f"{body}"
        "</div>"
        "<div style=\"font-family:Arial,sans-serif;color:#6b7280;font-size:12px;line-height:1.6;margin:16px 4px 0;\">"
        "Generated automatically by Project Inspiration Finder."
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
