import json
import re
from pathlib import Path
from datetime import datetime, timezone

WIKI_DIR = Path("wiki")
OUTPUT = Path("graph.json")

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', re.DOTALL)


def parse_frontmatter(content: str) -> tuple:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    frontmatter_str = m.group(1).strip()
    body = m.group(2).strip()

    data = {}
    for line in frontmatter_str.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data, body


def parse_tags(tag_str: str) -> list:
    try:
        val = json.loads(tag_str)
        return val if isinstance(val, list) else []
    except Exception:
        return [t.strip().strip('"').strip("'") for t in tag_str.split(",") if t.strip()]


def parse_links(links_str: str) -> list:
    try:
        val = json.loads(links_str)
        return val if isinstance(val, list) else []
    except Exception:
        return []


def collect_notes():
    """Return list of dicts with parsed metadata for every wiki note."""
    notes = []
    if not WIKI_DIR.exists():
        return notes
    for cat_dir in WIKI_DIR.iterdir():
        if not cat_dir.is_dir():
            continue
        for note_file in cat_dir.glob("*.md"):
            content = note_file.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            notes.append({
                "id": meta.get("id", ""),
                "category": meta.get("category", cat_dir.name),
                "tags": parse_tags(meta.get("tags", "[]")),
                "summary": meta.get("summary", ""),
                "links_to": parse_links(meta.get("links_to", "[]")),
                "body": body,
            })
    return notes


def build_graph():
    notes = collect_notes()

    nodes = []
    edges = []
    categories = set()

    for n in notes:
        note_id = n["id"]
        if not note_id:
            continue
        summary = n["summary"]
        label = summary if summary else n["body"].split("\n")[0][:60]
        categories.add(n["category"])

        preview_source = n["body"]
        if "## Related" in preview_source:
            preview_source = preview_source[:preview_source.index("## Related")].rstrip()

        nodes.append({
            "id": note_id,
            "label": label,
            "category": n["category"],
            "tags": n["tags"],
            "summary": summary,
            "degree": len(n["links_to"]),
            "group": n["category"],
            "content_preview": preview_source[:200],
        })

        for target_id in n["links_to"]:
            edges.append({"from": note_id, "to": target_id, "weight": 1.0, "label": ""})

    # Deduplicate edges (undirected)
    seen = set()
    unique_edges = []
    for edge in edges:
        if edge["from"] == edge["to"]:
            continue
        pair = tuple(sorted([edge["from"], edge["to"]]))
        if pair not in seen:
            seen.add(pair)
            unique_edges.append(edge)

    # Extract similarity weights from each note's ## Related section
    body_by_id = {n["id"]: n["body"] for n in notes if n["id"]}
    for edge in unique_edges:
        body = body_by_id.get(edge["from"], "")
        match = re.search(rf'\[\[{re.escape(edge["to"])}\]\].*?([0-9]*\.?[0-9]+)', body)
        if match:
            edge["weight"] = float(match.group(1))
        edge["label"] = f"{edge['weight']:.2f}"

    graph = {
        "nodes": nodes,
        "edges": unique_edges,
        "meta": {
            "total_nodes": len(nodes),
            "total_edges": len(unique_edges),
            "categories": sorted(categories),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    OUTPUT.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Graph built: {len(nodes)} nodes, {len(unique_edges)} edges -> {OUTPUT}")
    print(f"Categories: {', '.join(sorted(categories))}")


if __name__ == "__main__":
    build_graph()