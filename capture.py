import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RAW_DIR = Path("raw")
MAX_CONTENT_LENGTH = 50000


def generate_id() -> str:
    return str(uuid.uuid4())


def capture_note(text: str) -> dict:
    note_id = generate_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    return {"id": note_id, "timestamp": timestamp, "type": "note", "source": "cli", "content": text}


def capture_link(url: str) -> dict:
    note_id = generate_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "SecondSelf/1.0"}, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        content = soup.get_text(separator="\n", strip=True)
    except requests.exceptions.HTTPError as e:
        title = url
        content = f"[Fetch failed: HTTP {e.response.status_code}]"
    except requests.exceptions.ConnectionError:
        title = url
        content = "[Fetch failed: Connection error]"
    except requests.exceptions.Timeout:
        title = url
        content = "[Fetch failed: Timeout]"
    except Exception as e:
        title = url
        content = f"[Fetch failed: {e}]"
    return {"id": note_id, "timestamp": timestamp, "type": "link", "source": "url", "url": url, "title": title, "content": content[:MAX_CONTENT_LENGTH]}


def capture_file(filepath: str) -> dict:
    note_id = generate_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    path = Path(filepath)
    ext = path.suffix.lower()

    if not path.exists():
        return {"id": note_id, "timestamp": timestamp, "type": "file", "source": "file", "original_path": str(path), "content": f"[File not found: {path}]"}

    if not path.is_file():
        return {"id": note_id, "timestamp": timestamp, "type": "file", "source": "file", "original_path": str(path), "content": f"[Not a file: {path}]"}

    if ext == ".pdf":
        import PyPDF2
        try:
            reader = PyPDF2.PdfReader(filepath)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            text = f"[PDF extraction failed: {e}]"
    elif ext == ".docx":
        import docx
        try:
            doc = docx.Document(filepath)
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            text = f"[DOCX extraction failed: {e}]"
    else:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            text = f"[File read failed: {e}]"

    return {"id": note_id, "timestamp": timestamp, "type": "file", "source": "file", "original_path": str(path), "content": text[:MAX_CONTENT_LENGTH]}


def write_capture(capture: dict) -> Path:
    RAW_DIR.mkdir(exist_ok=True)
    ts = capture["timestamp"][:19].replace("-", "").replace(":", "").replace("T", "_")
    short_id = capture["id"].replace("-", "")[:8]
    filename = f"{ts}_{short_id}.md"
    filepath = RAW_DIR / filename

    frontmatter = f"""---
id: {capture["id"]}
timestamp: "{capture["timestamp"]}"
type: {capture["type"]}
source: {capture["source"]}
"""
    if capture["type"] == "link":
        frontmatter += f'url: {capture["url"]}\ntitle: "{capture["title"]}"\n'
    if capture["type"] == "file":
        frontmatter += f'original_path: {capture["original_path"]}\n'

    content = f"{frontmatter}---\n\n{capture['content']}\n"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Capture anything into SecondSelf")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--note", type=str, help="Text note to capture")
    group.add_argument("--link", type=str, help="URL to capture")
    group.add_argument("--file", type=str, help="File path to capture")
    group.add_argument("--stdin", action="store_true", help="Read from stdin")

    args = parser.parse_args()

    if args.note:
        capture = capture_note(args.note)
    elif args.link:
        capture = capture_link(args.link)
    elif args.file:
        capture = capture_file(args.file)
    elif args.stdin:
        capture = capture_note(sys.stdin.read())

    filepath = write_capture(capture)
    print(f"Captured {capture['id'][:8]} -> {filepath} ({capture['type']}, {len(capture['content'])} chars)")


if __name__ == "__main__":
    main()