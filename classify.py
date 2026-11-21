import os
import json
import time
import re
from pathlib import Path
from dotenv import load_dotenv

from groq import Groq

load_dotenv()

RAW_DIR = Path("raw")
WIKI_DIR = Path("wiki")
PROCESSED_DIR = Path("raw/processed")

SYSTEM_PROMPT = """You are a personal knowledge organizer. Given a note, classify it into PARA.

Return ONLY a JSON object (no markdown, no explanation):
{
  "category": "Projects" | "Areas" | "Resources" | "Archives",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "one-line summary (max 80 chars)"
}

PARA Rules:
- Projects: specific tasks with deadline/goal (e.g., "build portfolio", "launch startup", "Q1 roadmap")
- Areas: ongoing responsibilities with no end date (e.g., "health", "team management", "finances", "reading")
- Resources: reference material, links, docs (e.g., "React docs", "Python tutorial", "design inspiration")
- Archives: inactive/completed items (e.g., old projects, finished courses)

Guidelines:
- Tags should be lowercase, hyphenated, 2-4 words max
- Summary must capture the essence in <80 chars
- When in doubt between two categories, pick the one that best fits the note's primary purpose
"""

VALID_CATEGORIES = {"Projects", "Areas", "Resources", "Archives"}


def extract_frontmatter_value(frontmatter: str, key: str) -> str:
    for line in frontmatter.strip().split("\n"):
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def classify_note(client: Groq, content: str) -> dict:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content[:4000]},
        ],
        temperature=0.1,
        max_tokens=1000,
    )
    result_text = response.choices[0].message.content.strip()

    if not result_text:
        raise ValueError("LLM returned empty response")

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*?\}', result_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                result = json.loads(match.group().replace('\n', ''))
        else:
            raise ValueError(f"LLM returned non-JSON: {result_text[:200]}")

    category = result.get("category", "Resources")
    if category not in VALID_CATEGORIES:
        category = "Resources"

    tags = result.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).lower().strip() for t in tags if t][:5]

    summary = result.get("summary", "")
    if not summary:
        summary = content.strip().split("\n")[0][:80]
    summary = summary[:80]

    return {"category": category, "tags": tags, "summary": summary}


def fallback_result(content: str) -> dict:
    first_line = content.strip().split("\n")[0][:80] if content.strip() else "Untitled"
    return {"category": "Resources", "tags": ["uncategorized"], "summary": first_line}


def write_wiki_note(filepath: Path, frontmatter: str, body: str, result: dict) -> Path:
    category = result["category"]
    category_dir = WIKI_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    note_id = extract_frontmatter_value(frontmatter, "id")
    timestamp = extract_frontmatter_value(frontmatter, "timestamp")

    wiki_filename = filepath.name
    wiki_filepath = category_dir / wiki_filename

    tags_json = json.dumps(result["tags"])
    wiki_content = f"""---
id: {note_id}
raw_id: {note_id}
timestamp: "{timestamp}"
category: {category}
tags: {tags_json}
summary: "{result['summary']}"
links_to: []
links_from: []
---

# {result['summary']}

{body.strip()}
"""
    wiki_filepath.write_text(wiki_content, encoding="utf-8")
    return wiki_filepath


def process_raw_file(client: Groq, filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    body = parts[2] if len(parts) >= 3 else content

    try:
        result = classify_note(client, body.strip())
    except Exception as e:
        print(f"      (classify failed: {e} -> using fallback)")
        result = fallback_result(body)

    category = result["category"]
    wiki_filepath = write_wiki_note(filepath, frontmatter, body, result)

    PROCESSED_DIR.mkdir(exist_ok=True)
    filepath.rename(PROCESSED_DIR / filepath.name)

    return wiki_filepath, result


def main():
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        print("ERROR: GROQ_API_KEY not set. Create .env file with your Groq API key.")
        print("Get a free key at https://console.groq.com")
        return

    client = Groq(api_key=groq_key)

    raw_files = list(RAW_DIR.glob("*.md"))
    print(f"Processing {len(raw_files)} raw captures...")

    if not raw_files:
        print("No new captures to classify.")
        return

    success = 0
    failed = 0
    for i, f in enumerate(raw_files):
        try:
            wiki_path, result = process_raw_file(client, f)
            print(f"  [{i+1}/{len(raw_files)}] {f.name} -> {result['category']} -> {wiki_path.name}")
            success += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{i+1}/{len(raw_files)}] ERROR on {f.name}: {e}")
            failed += 1

    print(f"\nClassified {success} notes into wiki/ ({failed} failed)")


if __name__ == "__main__":
    main()