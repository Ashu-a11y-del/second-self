# SecondSelf - Your Personal AI Second Brain

> Capture anything -> AI classifies & links -> Interactive graph -> Ask anything in plain English -> Synthesized answers from your own knowledge.

SecondSelf is a personal knowledge management system that captures notes, links, and files, organizes them automatically with the PARA method, links related notes using semantic embeddings, visualizes everything as an interactive force-directed graph, and answers questions in plain English using retrieval-augmented generation (RAG) over your own notes.

## What It Does

1. **Captures** notes, links, and files into a single `raw/` folder (timestamp + unique ID)
2. **Classifies** them automatically with AI (PARA: Projects, Areas, Resources, Archives) + tags + summary
3. **Links** related notes automatically using sentence-transformer embeddings
4. **Visualizes** your entire knowledge base as an interactive, hoverable graph
5. **Answers** any question in plain English, synthesized from your notes with source citations

## Quick Start

### Prerequisites
- Python 3.9+
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup
```bash
pip install -r requirements.txt
```

Then create a `.env` file in the project root with your Groq key:
```
GROQ_API_KEY=your_key_here
```

### Usage
```bash
# 1. Capture notes, links, files
python capture.py --note "My first thought"
python capture.py --link https://example.com
python capture.py --file document.pdf

# 2. AI auto-classifies into PARA (category + tags + summary)
python classify.py

# 3. Auto-link related notes with embeddings
python link.py

# 4. Build the interactive graph (graph.json)
python build_graph.py

# 5. Launch the app (Graph + Ask + Browse)
streamlit run app.py
```

## Usage Examples

```bash
# Ask your brain a question from the CLI
python ask.py "What are my current projects?"
python ask.py "What have I been reading about?"

# View stored embeddings
python pack_embeddings.py      # pack embeddings/*.npy -> data/embeddings.pkl
python view_embeddings.py      # inspect the vectors

# Preview the graph as a standalone page
python -m http.server 8000     # then open http://localhost:8000/graph_viewer.html
```

## Architecture

```
Capture (capture.py)        -> raw/          (timestamp + unique ID)
Classify (classify.py)      -> wiki/<PARA>/  (category + tags + summary)
Link (link.py)              -> embeddings/   (384-dim vectors + auto-links)
Graph (build_graph.py)      -> graph.json    (nodes + edges)
Ask (ask.py)                -> RAG answer    (retrieval + LLM synthesis)
App (app.py)                -> Streamlit     (Graph + Ask + Browse)
```

See [docs/architecture.md](docs/architecture.md) for the full architecture and [docs/Implementation-plan.md](docs/Implementation-plan.md) for the build plan.

## Tech Stack

- **LLM**: Groq (`openai/gpt-oss-20b`) for classification and Q&A
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`, local + free)
- **Graph**: vis-network.js (force-directed, interactive)
- **UI**: Streamlit
- **Storage**: Markdown files with YAML frontmatter (the `wiki/` folder is the database)

## Configuration

Configurable via environment variables (`.env` or Streamlit secrets):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Groq API key for LLM calls |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | LLM model for classification + Q&A |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `SIMILARITY_THRESHOLD` | `0.35` | Cosine similarity cutoff for auto-linking |
| `TOP_K_RETRIEVAL` | `5` | Notes retrieved per question |

## Deployment (Streamlit Cloud / HF Spaces)

The Streamlit app can be deployed free. See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.

Short version:
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, select `app.py`.
3. Add `GROQ_API_KEY` under App secrets -> Deploy.

## Project Structure

```
secondself/
├── raw/                 # raw captures (gitignored)
├── wiki/                # classified + linked notes (PARA)
├── embeddings/          # .npy embedding vectors
├── capture.py           # one-command capture
├── classify.py          # PARA classification via LLM
├── link.py              # embeddings + auto-linking
├── build_graph.py       # nodes/edges -> graph.json
├── ask.py               # retrieval-augmented Q&A
├── app.py               # Streamlit UI (graph + search)
├── graph_viewer.html    # standalone graph preview
├── requirements.txt
├── .env.example
└── README.md
```

## Notes & Limitations

- Groq's free tier is used; the Llama 3 models were decommissioned in 2026, so this project uses `openai/gpt-20b`. Change `GROQ_MODEL` if you have access to others.
- The default link threshold (0.35) is tuned for short personal notes; adjust `SIMILARITY_THRESHOLD` as needed.
- Storage is file-based (no database) - ideal for a personal knowledge base of hundreds to low thousands of notes.

## License

MIT