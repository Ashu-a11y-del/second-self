import os
import json
import re
import argparse
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

WIKI_DIR = Path("wiki")
EMBEDDINGS_DIR = Path("embeddings")
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", 0.35))
MAX_LINKS_PER_NOTE = 10
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', re.DOTALL)


def parse_note(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    if m:
        frontmatter = m.group(1)
        body = m.group(2)
    else:
        frontmatter = ""
        body = content

    note_id = None
    for line in frontmatter.split("\n"):
        if line.strip().startswith("id:"):
            note_id = line.split(":", 1)[1].strip()
            break

    return {"filepath": filepath, "frontmatter": frontmatter, "body": body, "id": note_id}


def get_all_notes() -> list:
    notes = []
    if not WIKI_DIR.exists():
        return notes
    for cat_dir in WIKI_DIR.iterdir():
        if cat_dir.is_dir():
            for f in cat_dir.glob("*.md"):
                notes.append(f)
    return notes


def generate_embedding(model, text: str) -> np.ndarray:
    return model.encode(text, show_progress_bar=False)


def strip_related_section(body: str) -> str:
    if "## Related" in body:
        return body[:body.index("## Related")].rstrip()
    return body.rstrip()


def update_note_links(note: dict, links: list) -> None:
    filepath = note["filepath"]
    content = filepath.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    frontmatter = m.group(1) if m else ""
    body = m.group(2) if m else content

    links_to_ids = [l[0] for l in links]
    links_to_str = json.dumps(links_to_ids)

    frontmatter_lines = frontmatter.split("\n")
    updated = False
    for i, line in enumerate(frontmatter_lines):
        if line.strip().startswith("links_to:"):
            frontmatter_lines[i] = f"links_to: {links_to_str}"
            updated = True
            break
    if not updated:
        frontmatter_lines.append(f"links_to: {links_to_str}")

    body_clean = strip_related_section(body)

    related_section = "\n\n## Related\n"
    for other_id, score in links:
        related_section += f"- [[{other_id}]] - similarity: {score}\n"

    new_content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body_clean + related_section
    filepath.write_text(new_content, encoding="utf-8")


def compute_similarity_map(embeddings: dict, threshold: float) -> dict:
    ids = list(embeddings.keys())
    matrix = np.vstack([embeddings[i] for i in ids])
    sim_matrix = cosine_similarity(matrix)

    results = {}
    for i, note_id in enumerate(ids):
        similar = []
        for j, other_id in enumerate(ids):
            if i == j:
                continue
            score = float(sim_matrix[i][j])
            if np.isnan(score):
                continue
            if score >= threshold:
                similar.append((other_id, round(score, 2)))
        similar.sort(key=lambda x: x[1], reverse=True)
        results[note_id] = similar[:MAX_LINKS_PER_NOTE]
    return results


def cleanup_orphaned_embeddings(valid_ids: set) -> None:
    if not EMBEDDINGS_DIR.exists():
        return
    removed = 0
    for npy in EMBEDDINGS_DIR.glob("*.npy"):
        if npy.stem not in valid_ids:
            npy.unlink()
            removed += 1
    if removed:
        print(f"  Cleaned up {removed} orphaned embedding(s)")


def link_notes(force_rebuild: bool = False, threshold: float = SIMILARITY_THRESHOLD) -> None:
    EMBEDDINGS_DIR.mkdir(exist_ok=True)

    notes = get_all_notes()
    print(f"Found {len(notes)} notes in wiki/")

    if not notes:
        print("No notes to link. Run classify.py first.")
        return

    print(f"Loading embedding model ({EMBEDDING_MODEL})...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    embeddings = {}
    valid_ids = set()
    for note in notes:
        parsed = parse_note(note)
        note_id = parsed["id"]
        if not note_id:
            print(f"  WARNING: skipping note without id: {note.name}")
            continue
        valid_ids.add(note_id)

        body = parsed["body"].strip()
        if not body:
            print(f"  WARNING: skipping empty note: {note.name}")
            continue

        embedding_path = EMBEDDINGS_DIR / f"{note_id}.npy"
        emb = None
        if not force_rebuild and embedding_path.exists():
            try:
                emb = np.load(embedding_path)
                if emb.shape[0] == 0 or np.all(emb == 0):
                    emb = None
            except Exception:
                emb = None

        if emb is None:
            emb = generate_embedding(model, body)
            np.save(embedding_path, emb)
            print(f"  Embedded: {note_id[:8]} ({note.name})")

        embeddings[note_id] = emb

    cleanup_orphaned_embeddings(valid_ids)

    if len(embeddings) < 2:
        print("Need at least 2 notes to compute links.")
        return

    print("Computing similarity matrix...")
    similar_map = compute_similarity_map(embeddings, threshold)

    total_links = 0
    for note in notes:
        parsed = parse_note(note)
        links = similar_map.get(parsed["id"], [])
        if links:
            update_note_links(parsed, links)
            total_links += len(links)
            print(f"  {parsed['id'][:8]}: {len(links)} links -> {[l[0][:8] for l in links]}")

    print(f"\nEmbedded {len(embeddings)} notes, created {total_links} links")


def main():
    parser = argparse.ArgumentParser(description="Embed notes and auto-link related ones")
    parser.add_argument("--rebuild", action="store_true", help="Recompute all embeddings")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD, help="Similarity threshold")
    args = parser.parse_args()

    link_notes(force_rebuild=args.rebuild, threshold=args.threshold)


if __name__ == "__main__":
    main()