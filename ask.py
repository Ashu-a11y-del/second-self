import os
import sys
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq

load_dotenv()

WIKI_DIR = Path("wiki")
EMBEDDINGS_DIR = Path("embeddings")
TOP_K = int(os.environ.get("TOP_K_RETRIEVAL", 5))
MIN_SIMILARITY = float(os.environ.get("MIN_SIMILARITY", 0.3))
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', re.DOTALL)

SYSTEM_PROMPT = """You are SecondSelf, a personal knowledge assistant.
Answer the question using ONLY the provided context from the user's notes.
If the context doesn't contain relevant information, say "I don't have enough information in your notes to answer that."
Be concise (2-3 sentences max)."""

_model = None
_client = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_client():
    global _client
    if _client is None:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not set. Add it to .env")
        _client = Groq(api_key=key)
    return _client


def load_all_embeddings():
    note_ids = []
    embeddings = []
    for npy_file in EMBEDDINGS_DIR.glob("*.npy"):
        try:
            emb = np.load(npy_file)
        except Exception:
            continue
        if emb.shape[0] == 0:
            continue
        note_ids.append(npy_file.stem)
        embeddings.append(emb)

    if not embeddings:
        raise ValueError("No embeddings found. Run `python link.py` first.")

    return note_ids, np.vstack(embeddings)


def load_notes_by_id():
    """Build a lookup of note_id -> {title, body} from wiki/."""
    notes = {}
    if not WIKI_DIR.exists():
        return notes
    for cat_dir in WIKI_DIR.iterdir():
        if not cat_dir.is_dir():
            continue
        for f in cat_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            m = FRONTMATTER_RE.match(content)
            if not m:
                continue
            frontmatter = m.group(1)
            body = m.group(2).strip()
            note_id = None
            title = None
            for line in frontmatter.split("\n"):
                if line.strip().startswith("id:"):
                    note_id = line.split(":", 1)[1].strip()
                elif line.strip().startswith("summary:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")
            if note_id:
                notes[note_id] = {"title": title or note_id[:8], "body": body}
    return notes


def ask(question: str) -> dict:
    question = (question or "").strip()
    if not question:
        return {"answer": "Please enter a question.", "sources": [], "query": question}

    model = get_model()
    question_emb = model.encode(question, show_progress_bar=False)

    note_ids, note_matrix = load_all_embeddings()
    similarities = cosine_similarity(question_emb.reshape(1, -1), note_matrix)[0]

    top_indices = np.argsort(similarities)[::-1][:TOP_K]
    relevant = [(note_ids[i], float(similarities[i])) for i in top_indices if similarities[i] >= MIN_SIMILARITY]

    if not relevant:
        return {
            "answer": "I don't have enough information in your notes to answer that.",
            "sources": [],
            "query": question,
        }

    notes_lookup = load_notes_by_id()
    context_parts = []
    sources = []
    for note_id, score in relevant:
        info = notes_lookup.get(note_id)
        if not info:
            continue
        body = info["body"]
        context_parts.append(f"---\n[{info['title']}]\n{body}\n---")
        sources.append({"id": note_id, "title": info["title"], "similarity": round(score, 3)})

    if not context_parts:
        return {
            "answer": "I don't have enough information in your notes to answer that.",
            "sources": [],
            "query": question,
        }

    context = "\n\n".join(context_parts)

    client = get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context (from your notes):\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.3,
        max_tokens=500,
    )

    answer = response.choices[0].message.content.strip()

    return {"answer": answer, "sources": sources, "query": question}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Ask your brain: ")

    result = ask(question)
    print(f"\n{result['answer']}\n")
    if result["sources"]:
        print(f"Sources: {len(result['sources'])} notes")
        for s in result["sources"]:
            print(f"  - [{s['title']}] (similarity: {s['similarity']})")


if __name__ == "__main__":
    main()