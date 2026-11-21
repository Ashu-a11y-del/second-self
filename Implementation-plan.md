# SecondSelf — Implementation Plan

> Phase-wise, step-by-step guide to building the complete SecondSelf system.
> Each phase maps to a weekly milestone. Every step is actionable with exact commands.

---

## Phase 0: Pre-Work — Setup & Scaffolding

**Goal**: Get the repo structure, dependencies, and environment configured before writing any pipeline code.

### Step 0.1 — Create project structure
```
secondself/
├── docs/
│   ├── problem-statement.md      ← already exists
│   └── architecture.md           ← already exists
├── raw/                          ← create empty
├── wiki/                         ← create empty (with subdirs)
│   ├── Projects/
│   ├── Areas/
│   ├── Resources/
│   └── Archives/
├── embeddings/                   ← create empty
├── capture.py                    ← Week 1
├── classify.py                   ← Week 2.1
├── link.py                       ← Week 2.2
├── build_graph.py                ← Week 3.1
├── graph.json                    ← Week 3.1 (generated)
├── ask.py                        ← Week 4.1
├── app.py                        ← Week 4.2
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

**Commands**:
```powershell
# From D:\Coding\masai life\second self\
New-Item -ItemType Directory -Path "raw","wiki\Projects","wiki\Areas","wiki\Resources","wiki\Archives","embeddings" -Force
```

### Step 0.2 — Create `requirements.txt`

```
# Week 1 — Capture
requests==2.31.0
beautifulsoup4==4.12.2
PyPDF2==3.0.1
python-docx==1.1.0

# Week 2 — Classify + Link
groq==0.9.0
sentence-transformers==2.7.0
numpy==1.26.4
scikit-learn==1.4.2

# Week 4 — App
streamlit==1.33.0

# Utilities
python-dotenv==1.0.1
pyyaml==6.0.1
```

**Install**:
```powershell
pip install -r requirements.txt
```

### Step 0.3 — Create `.gitignore`

```gitignore
# Raw captures (private notes)
raw/

# Organized wiki (generated)
wiki/

# Embeddings (binary, large)
embeddings/

# Environment
.env

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# Streamlit
.streamlit/secrets.toml

# OS
Thumbs.db
Desktop.ini

# IDE
.vscode/
.idea/
```

### Step 0.4 — Create `.env.example`

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### Step 0.5 — Create `README.md` (minimal, expand in Phase 4)

```markdown
# SecondSelf — Your Personal AI Second Brain

Capture anything → AI classifies & links → Interactive graph → Ask anything → Synthesized answers.

## Quick Start

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `GROQ_API_KEY`
3. `python capture.py --note "Your first note"`
4. `python classify.py`
5. `python link.py`
6. `python build_graph.py`
7. `streamlit run app.py`

See [docs/architecture.md](docs/architecture.md) for full design.
```

### Phase 0 checklist
- [ ] Directory structure created
- [ ] `requirements.txt` created + `pip install` succeeds
- [ ] `.gitignore` created
- [ ] `.env.example` created
- [ ] `README.md` created
- [ ] `GROQ_API_KEY` obtained from [console.groq.com](https://console.groq.com)

---

## Phase 1: The Archivist — Capture Everything, Lose Nothing

**Week 1 deliverable**: One command saves any note, link, or file to `raw/` with timestamp + unique ID.

### Step 1.1 — Write `capture.py`

**What it must do**:
- Accept `--note "text"`, `--link URL`, `--file path`, or `--stdin` as input
- Generate a UUID4 + ISO-8601 timestamp
- For links: fetch page title + content (requests + BeautifulSoup)
- For files: extract text (PyPDF2 for PDF, python-docx for DOCX, raw text for .md/.txt)
- Write to `raw/<timestamp>_<uuid8>.md` with YAML frontmatter
- Print confirmation: `✅ Captured <id> → raw/<filename> (type: note|link|file, <N> chars)`

**Key code structure**:
```python
# capture.py — skeleton
import argparse, uuid, json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

RAW_DIR = Path("raw")

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
        resp = requests.get(url, timeout=10, headers={"User-Agent": "SecondSelf/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string if soup.title else url
        content = soup.get_text(separator="\n", strip=True)
    except Exception as e:
        title = url
        content = f"[Fetch failed: {e}]"
    return {"id": note_id, "timestamp": timestamp, "type": "link", "source": "url", "url": url, "title": title, "content": content[:50000]}

def capture_file(filepath: str) -> dict:
    note_id = generate_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext == ".pdf":
        import PyPDF2
        reader = PyPDF2.PdfReader(filepath)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        import docx
        doc = docx.Document(filepath)
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return {"id": note_id, "timestamp": timestamp, "type": "file", "source": "file", "original_path": str(path), "content": text[:50000]}

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

# CLI
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
print(f"✅ Captured {capture['id'][:8]} → {filepath} ({capture['type']}, {len(capture['content'])} chars)")
```

### Step 1.2 — Test with real data (10+ items)

**Capture a mix of note / link / file**:
```powershell
python capture.py --note "SecondSelf project idea: AI-powered personal knowledge base"
python capture.py --note "Book recommendation: Atomic Habits by James Clear — focus on habit stacking"
python capture.py --link https://en.wikipedia.org/wiki/Second_brain
python capture.py --link https://fortelabs.com/blog/basboverview/
python capture.py --note "Meeting notes: Discussed Q1 roadmap with team — decided to focus on onboarding flow"
python capture.py --note "TIL: Python 3.11 has exception groups via except* — cleaner error handling for async code"
python capture.py --link https://docs.python.org/3/tutorial/
python capture.py --note "Idea for weekend project: build a URL shortener using Flask and Redis"
python capture.py --file "C:\Users\hp\Documents\resume.pdf"
python capture.py --file "D:\Coding\masai life\second self\docs\problem-statement.md"
python capture.py --note "Health: started intermittent fasting (16:8) — energy levels are noticeably better"
python capture.py --note "Reading: Sapiens by Yuval Noah Harari — chapter on cognitive revolution"
```

### Step 1.3 — Verify

- [ ] `raw/` and `wiki/` folder structure exists
- [ ] One command captures a note: `python capture.py --note "test"` → `raw/<timestamp>_<id>.md`
- [ ] One command captures a link: `python capture.py --link https://example.com` → file with title + content
- [ ] One command captures a file: `python capture.py --file <path>` → file with extracted text
- [ ] Every file in `raw/` has `id`, `timestamp`, `type`, `source` in frontmatter
- [ ] 10+ real items captured (not test data)

---

## Phase 2: The Librarian — Teach AI to Organize For You

**Week 2 deliverable**: Auto-classify raw captures with PARA + auto-link related notes using embeddings.

### Step 2.1 (2.1) — Auto-Classify: `classify.py`

**What it must do**:
- Read all unprocessed files from `raw/`
- Send each to Groq LLM with a classification prompt
- Get back `{category, tags[], summary}` as JSON
- Write enriched note to `wiki/<PARA_CATEGORY>/<timestamp>_<uuid8>.md`
- Mark raw/ capture as processed (rename with `.processed` suffix or move to `raw/processed/`)

**Key code structure**:
```python
# classify.py — skeleton
import os, json, time
from pathlib import Path
from groq import Groq

RAW_DIR = Path("raw")
WIKI_DIR = Path("wiki")
PROCESSED_DIR = Path("raw/processed")

client = Groq(api_key=os.environ["GROQ_API_KEY"])

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

def classify_note(content: str) -> dict:
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content[:4000]}  # truncate to fit context
        ],
        temperature=0.1,
        max_tokens=150,
    )
    result_text = response.choices[0].message.content.strip()
    # Parse JSON from response
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        # Fallback: extract JSON with regex
        import re
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {result_text[:200]}")

def process_raw_file(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    # Parse frontmatter
    parts = content.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    body = parts[2] if len(parts) >= 3 else content
    
    result = classify_note(body.strip())
    category = result["category"]
    
    # Write to wiki/<category>/
    category_dir = WIKI_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    wiki_filename = filepath.name
    wiki_filepath = category_dir / wiki_filename
    
    # Build wiki frontmatter
    wiki_content = f"""---
id: {extract_frontmatter_value(frontmatter, 'id')}
raw_id: {extract_frontmatter_value(frontmatter, 'id')}
timestamp: "{extract_frontmatter_value(frontmatter, 'timestamp')}"
category: {category}
tags: {json.dumps(result['tags'])}
summary: "{result['summary']}"
links_to: []
links_from: []
---

# {result['summary']}

{body.strip()}
"""
    wiki_filepath.write_text(wiki_content, encoding="utf-8")
    
    # Mark raw as processed
    PROCESSED_DIR.mkdir(exist_ok=True)
    filepath.rename(PROCESSED_DIR / filepath.name)
    
    return wiki_filepath, result

# Batch processing
raw_files = list(RAW_DIR.glob("*.md"))
print(f"Processing {len(raw_files)} raw captures...")
for i, f in enumerate(raw_files):
    try:
        wiki_path, result = process_raw_file(f)
        print(f"  [{i+1}/{len(raw_files)}] {f.name} → {result['category']} → {wiki_path.name}")
        time.sleep(0.5)  # rate limit safety
    except Exception as e:
        print(f"  [{i+1}/{len(raw_files)}] ERROR on {f.name}: {e}")

print(f"\n✅ Classified {len(raw_files)} notes into wiki/")
```

**Run it**:
```powershell
python classify.py
```

**Verify**:
- [ ] `wiki/` has 4 subdirectories: `Projects/`, `Areas/`, `Resources/`, `Archives/`
- [ ] Each raw/ capture → one wiki/ note with `category`, `tags`, `summary`
- [ ] Processed raw/ files moved to `raw/processed/`
- [ ] Summary is <80 chars, tags are 2-4 lowercase words

### Step 2.2 (2.2) — Auto-Link: `link.py`

**What it must do**:
- For every note in `wiki/`, compute a 384-dim embedding (sentence-transformers)
- Save embeddings as `.npy` files in `embeddings/`
- Compare each note's embedding against all others (cosine similarity)
- When similarity > 0.75, add bidirectional links between notes
- Update `links_to` and `links_from` in each note's YAML frontmatter

**Key code structure**:
```python
# link.py — skeleton
import os, json, time
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

WIKI_DIR = Path("wiki")
EMBEDDINGS_DIR = Path("embeddings")
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", 0.75))

model = SentenceTransformer("all-MiniLM-L6-v2")

def get_all_notes():
    """Recursively find all .md files in wiki/"""
    notes = []
    for cat_dir in WIKI_DIR.iterdir():
        if cat_dir.is_dir():
            for f in cat_dir.glob("*.md"):
                notes.append(f)
    return notes

def parse_note(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    body = parts[2] if len(parts) >= 3 else content
    # Extract id
    note_id = None
    for line in frontmatter.strip().split("\n"):
        if line.startswith("id:"):
            note_id = line.split(":", 1)[1].strip()
    return {"filepath": filepath, "frontmatter": frontmatter, "body": body.strip(), "id": note_id}

def generate_embedding(text: str) -> np.ndarray:
    return model.encode(text, show_progress_bar=False)

def compute_similarity_matrix(embeddings: dict) -> dict:
    """embeddings: {note_id: np.array} → returns {note_id: [(other_id, score), ...]}"""
    ids = list(embeddings.keys())
    matrix = np.vstack([embeddings[id] for id in ids])
    sim_matrix = cosine_similarity(matrix)
    
    results = {}
    for i, note_id in enumerate(ids):
        similar = []
        for j, other_id in enumerate(ids):
            if i != j and sim_matrix[i][j] >= SIMILARITY_THRESHOLD:
                similar.append((other_id, round(float(sim_matrix[i][j]), 2)))
        similar.sort(key=lambda x: x[1], reverse=True)
        results[note_id] = similar
    return results

def update_note_links(note: dict, links: list) -> None:
    """Update links_to in frontmatter"""
    filepath = note["filepath"]
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    frontmatter_lines = parts[1].strip().split("\n")
    
    # Update links_to line
    links_to_str = json.dumps([l[0] for l in links])
    updated = False
    for i, line in enumerate(frontmatter_lines):
        if line.startswith("links_to:"):
            frontmatter_lines[i] = f"links_to: {links_to_str}"
            updated = True
            break
    if not updated:
        frontmatter_lines.append(f"links_to: {links_to_str}")
    
    # Update Related section in body
    body = parts[2] if len(parts) >= 3 else ""
    related_section = "\n## Related\n"
    for other_id, score in links:
        related_section += f"- [[{other_id}]] — similarity: {score}\n"
    
    # Remove old Related section if exists
    if "## Related" in body:
        body = body[:body.index("## Related")].rstrip() + "\n"
    
    new_content = f"---\n" + "\n".join(frontmatter_lines) + "\n---\n" + body + related_section
    filepath.write_text(new_content, encoding="utf-8")

def link_notes(force_rebuild=False):
    EMBEDDINGS_DIR.mkdir(exist_ok=True)
    
    # Load or generate embeddings
    notes = get_all_notes()
    print(f"Found {len(notes)} notes in wiki/")
    
    embeddings = {}
    for note in notes:
        note = parse_note(note)
        embedding_path = EMBEDDINGS_DIR / f"{note['id']}.npy"
        if force_rebuild or not embedding_path.exists():
            emb = generate_embedding(note["body"])
            np.save(embedding_path, emb)
            embeddings[note["id"]] = emb
            print(f"  Embedded: {note['id'][:8]} ({note['filepath'].name})")
        else:
            embeddings[note["id"]] = np.load(embedding_path)
    
    # Compute similarities
    print("Computing similarity matrix...")
    similar_map = compute_similarity_matrix(embeddings)
    
    # Update links in notes
    total_links = 0
    for note in notes:
        note = parse_note(note)
        links = similar_map.get(note["id"], [])
        if links:
            update_note_links(note, links)
            total_links += len(links)
            print(f"  {note['id'][:8]}: {len(links)} links → {[l[0][:8] for l in links]}")
    
    print(f"\n✅ Embedded {len(notes)} notes, created {total_links} links")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Recompute all embeddings")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD)
    args = parser.parse_args()
    SIMILARITY_THRESHOLD = args.threshold
    link_notes(force_rebuild=args.rebuild)
```

**Run it**:
```powershell
python link.py
```

**Verify**:
- [ ] `embeddings/` has one `.npy` file per wiki/ note
- [ ] Each wiki/ note has `links_to` populated with related note IDs
- [ ] Links are bidirectional (A links_to B → B links_to A)
- [ ] `## Related` section added at bottom of each note
- [ ] 15+ real items processed end-to-end (classify + link)

---

## Phase 3: The Cartographer — Visualize the Brain

**Week 3 deliverable**: Script builds nodes/edges JSON + interactive force-directed graph with hover/drag/zoom.

### Step 3.1 (3.1) — Graph Data Model: `build_graph.py`

**What it must do**:
- Read all notes from `wiki/` (recursively)
- Parse frontmatter: id, title/summary, category, tags, links_to
- Build `nodes` array: one node per note
- Build `edges` array: one edge per link_to (deduplicate bidirectional)
- Export clean JSON to `graph.json`

**Key code structure**:
```python
# build_graph.py — skeleton
import json, re
from pathlib import Path
from datetime import datetime, timezone

WIKI_DIR = Path("wiki")
OUTPUT = Path("graph.json")

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content"""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    frontmatter_str = parts[1].strip()
    body = parts[2].strip()
    
    data = {}
    for line in frontmatter_str.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[key] = value
    return data, body

def parse_tags(tag_str: str) -> list:
    """Parse JSON array string or comma-separated"""
    try:
        return json.loads(tag_str)
    except:
        return [t.strip().strip('"').strip("'") for t in tag_str.split(",") if t.strip()]

def parse_links_to(links_str: str) -> list:
    """Parse JSON array or empty"""
    try:
        return json.loads(links_str)
    except:
        return []

def build_graph():
    nodes = []
    edges = []
    categories = set()
    
    for cat_dir in WIKI_DIR.iterdir():
        if not cat_dir.is_dir():
            continue
        for note_file in cat_dir.glob("*.md"):
            content = note_file.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            
            note_id = meta.get("id", "")
            category = meta.get("category", cat_dir.name)
            tags = parse_tags(meta.get("tags", "[]"))
            summary = meta.get("summary", "")
            links_to = parse_links_to(meta.get("links_to", "[]"))
            
            # Node
            label = summary if summary else body.split("\n")[0][:60]
            content_preview = body[:200]
            
            node = {
                "id": note_id,
                "label": label,
                "category": category,
                "tags": tags,
                "summary": summary,
                "degree": len(links_to),
                "group": category,
                "content_preview": content_preview
            }
            nodes.append(node)
            categories.add(category)
            
            # Edges (deduplicate)
            for target_id in links_to:
                edges.append({
                    "from": note_id,
                    "to": target_id,
                    "weight": 1.0,  # will be updated with actual similarity
                    "label": ""
                })
    
    # Deduplicate edges (undirected)
    seen_edges = set()
    unique_edges = []
    for edge in edges:
        pair = tuple(sorted([edge["from"], edge["to"]]))
        if pair not in seen_edges:
            seen_edges.add(pair)
            unique_edges.append(edge)
    
    # Try to get similarity weights from Related section
    for edge in unique_edges:
        # Look for similarity in note body
        from_note = next((f for f in WIKI_DIR.rglob("*.md") if parse_frontmatter(f.read_text(encoding="utf-8"))[0].get("id") == edge["from"]), None)
        if from_note:
            body = from_note.read_text(encoding="utf-8")
            # Search for "[[target_id]] — similarity: X.XX"
            match = re.search(rf'\[\[{re.escape(edge["to"])}\]\].*?([0-9.]+)', body)
            if match:
                edge["weight"] = float(match.group(1))
                edge["label"] = f"{edge['weight']:.2f}"
    
    graph = {
        "nodes": nodes,
        "edges": unique_edges,
        "meta": {
            "total_nodes": len(nodes),
            "total_edges": len(unique_edges),
            "categories": sorted(list(categories)),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    }
    
    OUTPUT.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"✅ Graph built: {len(nodes)} nodes, {len(unique_edges)} edges → {OUTPUT}")
    print(f"   Categories: {', '.join(sorted(categories))}")

if __name__ == "__main__":
    build_graph()
```

**Run it**:
```powershell
python build_graph.py
```

**Verify**:
- [ ] `graph.json` exists and is valid JSON
- [ ] `nodes` array has one entry per wiki/ note
- [ ] `edges` array has one entry per unique link pair
- [ ] No duplicate edges
- [ ] Each node has: id, label, category, tags, summary, degree, group, content_preview

### Step 3.2 (3.2) — Interactive Graph (Preview, full in Phase 4)

**What it must do**:
- Render a force-directed graph using vis-network.js
- Pulsing nodes (CSS animation on hover)
- Hover popup revealing note content (summary + preview)
- Drag to reposition nodes
- Zoom in/out

**Approach**: Build a standalone HTML file first for testing, then embed in Streamlit (Phase 4).

**Create `graph_viewer.html`** (temporary test file):
```html
<!DOCTYPE html>
<html>
<head>
  <title>SecondSelf — The Living Brain</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #0a0a0a; color: #e0e0e0; }
    #header { padding: 12px 20px; background: #111; border-bottom: 1px solid #333; }
    #header h1 { margin: 0; font-size: 18px; color: #fff; }
    #header p { margin: 4px 0 0; font-size: 12px; color: #888; }
    #network { width: 100%; height: calc(100vh - 80px); }
    .vis-tooltip { background: #1a1a1a !important; color: #e0e0e0 !important; border: 1px solid #444 !important; }
  </style>
</head>
<body>
  <div id="header">
    <h1>🧠 SecondSelf — The Living Brain</h1>
    <p id="stats">Loading...</p>
  </div>
  <div id="network"></div>
  <script>
    // Load graph.json
    fetch('graph.json')
      .then(r => r.json())
      .then(graph => {
        document.getElementById('stats').textContent = 
          `${graph.meta.total_nodes} notes · ${graph.meta.total_edges} connections · Categories: ${graph.meta.categories.join(', ')}`;
        
        // Category colors
        const categoryColors = {
          'Projects': '#e74c3c',
          'Areas': '#3498db',
          'Resources': '#2ecc71',
          'Archives': '#95a5a6'
        };
        
        // Build vis nodes
        const nodes = new vis.DataSet(graph.nodes.map(n => ({
          id: n.id,
          label: n.label,
          group: n.category,
          title: `${n.summary || n.label}\n\nTags: ${(n.tags || []).join(', ')}\nConnections: ${n.degree}`,
          color: { background: categoryColors[n.category] || '#888', border: '#fff' },
          size: 15 + (n.degree || 0) * 3,
          font: { color: '#e0e0e0', size: 11 },
          borderWidth: 2,
          shadow: true
        })));
        
        // Build vis edges
        const edges = new vis.DataSet(graph.edges.map(e => ({
          from: e.from,
          to: e.to,
          width: Math.max(1, (e.weight || 0.5) * 3),
          color: { color: '#555', opacity: 0.6 },
          arrows: { to: { enabled: false } },
          title: `Similarity: ${e.weight || 'N/A'}`
        })));
        
        const container = document.getElementById('network');
        const data = { nodes: nodes, edges: edges };
        const options = {
          physics: {
            forceAtlas2Based: {
              gravitationalConstant: -60,
              centralGravity: 0.01,
              springLength: 150,
              springConstant: 0.08,
              damping: 0.4
            },
            stabilization: { iterations: 200 }
          },
          interaction: {
            hover: true,
            dragNodes: true,
            zoomView: true,
            dragView: true,
            tooltipDelay: 200
          },
          nodes: {
            shape: 'dot',
            font: { face: 'system-ui' }
          },
          edges: {
            smooth: { type: 'continuous' }
          }
        };
        
        const network = new vis.Network(container, data, options);
        
        // Pulsing animation on hover
        network.on('hoverNode', function(params) {
          const nodeId = params.node;
          nodes.update({ id: nodeId, size: 35 });
        });
        network.on('blurNode', function(params) {
          const nodeId = params.node;
          const node = nodes.get(nodeId);
          nodes.update({ id: nodeId, size: 15 + (node.degree || 0) * 3 });
        });
      });
  </script>
</body>
</html>
```

**Test**: Open `graph_viewer.html` in browser after running `build_graph.py`.

**Verify**:
- [ ] Force-directed graph renders with all notes as nodes
- [ ] Hover shows tooltip with summary + tags + degree
- [ ] Drag nodes to reposition
- [ ] Scroll to zoom
- [ ] Nodes colored by PARA category
- [ ] Node size reflects degree (more connections = bigger)
- [ ] Edges show similarity weight on hover

---

## Phase 4: The Oracle — Ask It Anything, Ship It Public

**Week 4 deliverable**: `ask()` function with RAG + single Streamlit app + deployed public URL.

### Step 4.1 (4.1) — Ask Your Brain: `ask.py`

**What it must do**:
- Accept a natural language question
- Embed the question using the same sentence-transformers model
- Compare against all note embeddings (cosine similarity)
- Retrieve top-K (5) most relevant notes above threshold
- Build LLM prompt with retrieved note contents as context
- Call Groq LLM to synthesize an answer
- Return answer + source citations

**Key code structure**:
```python
# ask.py — skeleton
import os, json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq

WIKI_DIR = Path("wiki")
EMBEDDINGS_DIR = Path("embeddings")
TOP_K = int(os.environ.get("TOP_K_RETRIEVAL", 5))
MIN_SIMILARITY = 0.4

model = SentenceTransformer("all-MiniLM-L6-v2")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are SecondSelf, a personal knowledge assistant.
Answer the question using ONLY the provided context from the user's notes.
If the context doesn't contain relevant information, say "I don't have enough information in your notes to answer that."
Be concise (2-3 sentences max). Cite which notes you used by their title in brackets like [1], [2].
"""

def load_all_embeddings() -> tuple[list, np.ndarray]:
    """Load all note embeddings into a matrix"""
    note_ids = []
    embeddings = []
    
    for npy_file in EMBEDDINGS_DIR.glob("*.npy"):
        note_id = npy_file.stem
        emb = np.load(npy_file)
        note_ids.append(note_id)
        embeddings.append(emb)
    
    if not embeddings:
        raise ValueError("No embeddings found. Run `python link.py` first.")
    
    return note_ids, np.vstack(embeddings)

def load_note_content(note_id: str) -> str:
    """Find and load the content of a note by ID"""
    for cat_dir in WIKI_DIR.iterdir():
        if cat_dir.is_dir():
            for f in cat_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                if f"id: {note_id}" in content.split("---")[1]:
                    parts = content.split("---", 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                    # Extract title from summary
                    for line in parts[1].strip().split("\n"):
                        if line.startswith("summary:"):
                            title = line.split(":", 1)[1].strip().strip('"')
                            return f"[{title}]\n{body}"
                    return body[:500]
    return ""

def ask(question: str) -> dict:
    """Main RAG function"""
    # 1. Embed question
    question_emb = model.encode(question, show_progress_bar=False)
    
    # 2. Load all note embeddings
    note_ids, note_matrix = load_all_embeddings()
    
    # 3. Compute similarity
    similarities = cosine_similarity(
        question_emb.reshape(1, -1),
        note_matrix
    )[0]
    
    # 4. Get top-K
    top_indices = np.argsort(similarities)[::-1][:TOP_K]
    relevant = [(note_ids[i], float(similarities[i])) for i in top_indices if similarities[i] >= MIN_SIMILARITY]
    
    if not relevant:
        return {
            "answer": "I don't have enough information in your notes to answer that.",
            "sources": []
        }
    
    # 5. Build context
    context_parts = []
    sources = []
    for i, (note_id, score) in enumerate(relevant):
        content = load_note_content(note_id)
        if content:
            context_parts.append(f"---\n{content}\n---")
            sources.append({"id": note_id, "similarity": round(score, 3)})
    
    context = "\n\n".join(context_parts)
    
    # 6. Call LLM
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context (from your notes):\n{context}\n\nQuestion: {question}"}
        ],
        temperature=0.3,
        max_tokens=300,
    )
    
    answer = response.choices[0].message.content.strip()
    
    return {
        "answer": answer,
        "sources": sources,
        "query": question
    }

# CLI
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Ask your brain: ")
    
    result = ask(question)
    print(f"\n🧠 {result['answer']}\n")
    if result['sources']:
        print(f"Sources: {len(result['sources'])} notes")
        for s in result['sources']:
            print(f"  • {s['id'][:8]} (similarity: {s['similarity']})")
```

**Run it**:
```powershell
python ask.py "What are my current projects?"
python ask.py "What have I been reading about?"
python ask.py "Tell me about my health and fitness notes"
python ask.py --interactive
```

**Verify**:
- [ ] `ask()` returns answers synthesized from your own notes
- [ ] Sources cited with similarity scores
- [ ] Relevant notes retrieved (not random)
- [ ] Works on real questions about your captured notes

### Step 4.2 (4.2) — Streamlit App + Deployment

**What it must do**:
- Single Streamlit app with two views: Graph + Ask
- Graph tab: interactive vis-network.js graph (from graph.json)
- Ask tab: question input → answer display with source cards
- Deploy to Streamlit Cloud or HF Spaces
- Get a public URL

**`app.py` — full implementation**:
```python
# app.py
import streamlit as st
import json
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="SecondSelf — Your Personal AI Second Brain",
    page_icon="🧠",
    layout="wide"
)

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_graph():
    graph_path = Path("graph.json")
    if graph_path.exists():
        return json.loads(graph_path.read_text(encoding="utf-8"))
    return {"nodes": [], "edges": [], "meta": {}}

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-header { font-size: 28px; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
.main-sub { font-size: 14px; color: #666; margin-bottom: 24px; }
.graph-container { border-radius: 12px; overflow: hidden; border: 1px solid #e0e0e0; }
.source-card { background: #f8f9fa; border-left: 3px solid #3498db; padding: 8px 12px; margin: 4px 0; border-radius: 0 6px 6px 0; }
.source-card-title { font-weight: 600; font-size: 13px; color: #2c3e50; }
.source-card-sim { font-size: 11px; color: #888; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.setdefault("similarity_threshold", 0.75)
    st.session_state["similarity_threshold"] = st.slider(
        "Link threshold", 0.5, 0.95, 0.75, 0.05,
        help="Minimum cosine similarity for auto-linking"
    )
    st.session_state.setdefault("top_k", 5)
    st.session_state["top_k"] = st.slider(
        "Notes per query", 1, 10, 5,
        help="Number of notes to retrieve for each question"
    )
    st.markdown("---")
    graph = load_graph()
    st.metric("📝 Notes", graph.get("meta", {}).get("total_nodes", 0))
    st.metric("🔗 Connections", graph.get("meta", {}).get("total_edges", 0))

# ── Main ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🧠 SecondSelf</div>', unsafe_allow_html=True)
st.markdown('<div class="main-sub">Your Personal AI Second Brain — capture, organize, explore, ask.</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🕸️ Graph", "💬 Ask Your Brain", "📋 Browse"])

# ── Tab 1: Graph ────────────────────────────────────────────────────────────
with tab1:
    graph = load_graph()
    if not graph.get("nodes"):
        st.warning("No notes yet. Run `python classify.py` and `python link.py` first.")
    else:
        # Render graph with vis-network via HTML component
        import streamlit.components.v1 as components
        
        # Category colors
        cat_colors = {
            "Projects": "#e74c3c",
            "Areas": "#3498db",
            "Resources": "#2ecc71",
            "Archives": "#95a5a6"
        }
        
        nodes_json = json.dumps(graph["nodes"])
        edges_json = json.dumps(graph["edges"])
        colors_json = json.dumps(cat_colors)
        meta = graph["meta"]
        
        graph_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
          <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            #network {{ width: 100%; height: 600px; background: #fafafa; }}
            .vis-tooltip {{ background: #1a1a2e !important; color: #eee !important; border: 1px solid #444 !important; font-size: 12px !important; padding: 8px !important; max-width: 300px !important; white-space: pre-wrap !important; }}
            .vis-network-label {{ font-size: 11px !important; }}
          </style>
        </head>
        <body>
          <div id="network"></div>
          <script>
            const graph = {{"nodes": {nodes_json}, "edges": {edges_json}}};
            const catColors = {colors_json};
            
            const nodes = new vis.DataSet(graph.nodes.map(n => ({{
              id: n.id,
              label: n.label.length > 25 ? n.label.substring(0, 25) + '...' : n.label,
              title: n.summary + '\\n\\nTags: ' + (n.tags || []).join(', ') + '\\nConnections: ' + n.degree,
              color: {{ background: catColors[n.category] || '#888', border: '#fff' }},
              size: 15 + (n.degree || 0) * 4,
              font: {{ color: '#333', size: 11 }},
              borderWidth: 2,
              shadow: {{ enabled: true, color: 'rgba(0,0,0,0.1)' }}
            })));
            
            const edges = new vis.DataSet(graph.edges.map(e => ({{
              from: e.from,
              to: e.to,
              width: Math.max(1, (e.weight || 0.5) * 2),
              color: {{ color: '#999', opacity: 0.5 }},
              title: 'Similarity: ' + (e.weight || 'N/A'),
              smooth: {{ type: 'continuous' }}
            }})));
            
            const container = document.getElementById('network');
            const data = {{ nodes, edges }};
            const options = {{
              physics: {{
                forceAtlas2Based: {{
                  gravitationalConstant: -60,
                  centralGravity: 0.01,
                  springLength: 150,
                  springConstant: 0.08,
                  damping: 0.4
                }},
                stabilization: {{ iterations: 200 }}
              }},
              interaction: {{
                hover: true,
                dragNodes: true,
                zoomView: true,
                dragView: true,
                tooltipDelay: 200
              }}
            }};
            
            const network = new vis.Network(container, data, options);
            
            network.on('hoverNode', function(params) {{
              const nodeId = params.node;
              nodes.update({{ id: nodeId, size: 40 }});
            }});
            network.on('blurNode', function(params) {{
              const nodeId = params.node;
              const node = nodes.get(nodeId);
              nodes.update({{ id: nodeId, size: 15 + (node.degree || 0) * 4 }});
            }});
          </script>
        </body>
        </html>
        """
        
        components.html(graph_html, height=620)
        
        # Legend
        st.markdown("""
        <div style="display:flex;gap:16px;justify-content:center;padding:8px 0;font-size:12px;color:#666;">
          <span><span style="display:inline-block;width:12px;height:12px;background:#e74c3c;border-radius:50%;margin-right:4px;"></span>Projects</span>
          <span><span style="display:inline-block;width:12px;height:12px;background:#3498db;border-radius:50%;margin-right:4px;"></span>Areas</span>
          <span><span style="display:inline-block;width:12px;height:12px;background:#2ecc71;border-radius:50%;margin-right:4px;"></span>Resources</span>
          <span><span style="display:inline-block;width:12px;height:12px;background:#95a5a6;border-radius:50%;margin-right:4px;"></span>Archives</span>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 2: Ask ──────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### Ask Your Brain")
    st.markdown("Ask any question in plain English. Answers are synthesized from your notes.")
    
    question = st.text_input(
        "Your question:",
        placeholder="e.g., What are my current projects? What have I been reading about?",
        key="question_input"
    )
    
    if st.button("🧠 Ask", type="primary", use_container_width=True) or st.session_state.get("auto_ask", False):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Searching your notes..."):
                try:
                    from ask import ask
                    result = ask(question.strip())
                    
                    st.markdown("#### Answer")
                    st.markdown(result["answer"])
                    
                    if result.get("sources"):
                        st.markdown("#### Sources")
                        for i, src in enumerate(result["sources"], 1):
                            st.markdown(f"""
                            <div class="source-card">
                              <div class="source-card-title">[{i}] {src.get('title', src['id'])}</div>
                              <div class="source-card-sim">Similarity: {src['similarity']:.3f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No relevant notes found for this question.")
                except Exception as e:
                    st.error(f"Error: {e}")

# ── Tab 3: Browse ───────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Browse All Notes")
    
    graph = load_graph()
    nodes = graph.get("nodes", [])
    
    if not nodes:
        st.info("No notes yet.")
    else:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            categories = ["All"] + sorted(list(set(n.get("category", "") for n in nodes)))
            selected_cat = st.selectbox("Category", categories)
        with col2:
            all_tags = sorted(list(set(tag for n in nodes for tag in n.get("tags", []))))
            selected_tag = st.selectbox("Tag", ["All"] + all_tags)
        
        # Filter
        filtered = nodes
        if selected_cat != "All":
            filtered = [n for n in filtered if n.get("category") == selected_cat]
        if selected_tag != "All":
            filtered = [n for n in filtered if selected_tag in n.get("tags", [])]
        
        # Display as table
        import pandas as pd
        if filtered:
            df = pd.DataFrame([{
                "Title": n.get("label", "")[:50],
                "Category": n.get("category", ""),
                "Tags": ", ".join(n.get("tags", [])),
                "Connections": n.get("degree", 0),
                "Summary": n.get("summary", "")
            } for n in filtered])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(filtered)} of {len(nodes)} notes")
        else:
            st.info("No notes match the selected filters.")

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#999;font-size:11px;'>"
    "SecondSelf · Your Personal AI Second Brain · "
    "Capture → Classify → Link → Graph → Ask"
    "</div>",
    unsafe_allow_html=True
)
```

**Run locally**:
```powershell
streamlit run app.py
```

### Step 4.3 — Deploy to Streamlit Cloud

1. **Push to GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "SecondSelf: complete AI second brain"
   git remote add origin https://github.com/<your-username>/secondself.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect GitHub repo
   - Select `app.py` as entry point
   - Add secrets: `GROQ_API_KEY` = your key
   - Deploy

3. **Alternative: Hugging Face Spaces**:
   - Create new Space → Streamlit SDK
   - Connect GitHub repo
   - Add `GROQ_API_KEY` to Space secrets
   - Deploy

**Verify deployment**:
- [ ] Public URL is accessible
- [ ] Graph renders correctly
- [ ] Ask feature works end-to-end
- [ ] No errors in logs

---

## Phase 5: Polish & Ship

**Final deliverable**: Clean README, GitHub repo, verified end-to-end flow.

### Step 5.1 — Write full README

```markdown
# SecondSelf — Your Personal AI Second Brain

> Capture anything → AI classifies & links → Interactive graph → Ask anything in plain English → Synthesized answers from your own knowledge.

## What It Does

SecondSelf is a personal knowledge management system that:
1. **Captures** notes, links, and files into a single raw/ folder
2. **Classifies** them automatically using AI (PARA method: Projects, Areas, Resources, Archives)
3. **Links** related notes automatically using semantic embeddings
4. **Visualizes** your entire knowledge base as an interactive force-directed graph
5. **Answers** any question in plain English using RAG (retrieval-augmented generation) over your notes

## Quick Start

### Prerequisites
- Python 3.9+
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup
```bash
git clone https://github.com/<your-username>/secondself.git
cd secondself
pip install -r requirements.txt
cp .env.example .env  # Add your GROQ_API_KEY
```

### Usage
```bash
# 1. Capture notes, links, files
python capture.py --note "My first thought"
python capture.py --link https://example.com
python capture.py --file document.pdf

# 2. AI auto-classifies into PARA
python classify.py

# 3. Auto-link related notes with embeddings
python link.py

# 4. Build interactive graph
python build_graph.py

# 5. Launch the app
streamlit run app.py
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture.

## Tech Stack

- **LLM**: Groq (Llama 3 / Mixtral) for classification and Q&A
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, local + free)
- **Graph**: vis-network.js (force-directed, interactive)
- **UI**: Streamlit
- **Storage**: Markdown files with YAML frontmatter

## License

MIT
```

### Step 5.2 — Verify end-to-end

- [ ] Capture a note → classify → link → graph → ask (full pipeline works)
- [ ] Graph has 15+ notes from real data
- [ ] Ask returns relevant, synthesized answers
- [ ] Streamlit app deployed and accessible via public URL
- [ ] README is clear with setup instructions
- [ ] GitHub repo is public with clean commit history

### Step 5.3 — Final checklist (all acceptance criteria)

**Week 1 — The Archivist**
- [ ] raw/ and wiki/ folder structure exists
- [ ] One command captures a note, a link, AND a file
- [ ] Every capture has a timestamp + unique ID
- [ ] 10+ real items captured

**Week 2 — The Librarian**
- [ ] Any raw capture → category + tags + summary automatically
- [ ] PARA categorization working
- [ ] Embeddings computed per note
- [ ] Related notes auto-linked (no manual tagging)
- [ ] Runs on 15+ real items → organized wiki/

**Week 3 — The Cartographer**
- [ ] Script builds nodes + edges from notes and exports clean JSON
- [ ] Interactive force-directed graph renders from that JSON
- [ ] Hover reveals note content
- [ ] Drag + zoom work
- [ ] Built from your real notes, not dummy data

**Week 4 — The Oracle**
- [ ] ask() returns answers synthesized from your own notes (retrieval + LLM)
- [ ] One Streamlit app contains both the graph and the search bar
- [ ] Deployed live with a public URL
- [ ] Full pipeline works end to end in the deployed app

**Final Deliverables**
- [ ] Public GitHub repo with a clean README + setup instructions
- [ ] Live deployed URL — interactive graph + ask-your-brain search, both working
- [ ] End-to-end flow verified: capture → classify → link → graph → ask
- [ ] All 4 weekly milestones complete