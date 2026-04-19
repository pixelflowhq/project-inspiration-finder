import os
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
    })
    print("Email sent.")
