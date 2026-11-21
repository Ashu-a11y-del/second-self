# Deploying SecondSelf

This guide covers deploying the Streamlit app to a free public URL. There are two platforms that work well: **Streamlit Community Cloud** and **Hugging Face Spaces**.

---

## Important: Your Knowledge Base Data

The deployed app shows your notes (graph + Ask), which requires these files to be available to the app:

| Path | Needed for | Currently gitignored? |
|------|-----------|----------------------|
| `graph.json` | Graph + Browse tabs | yes |
| `embeddings/*.npy` | Ask (retrieval) | yes |
| `wiki/**/*.md` | Ask (answer context) | yes |

You have **two options**:

### Option A - Deploy with your real notes (public demo)
Un-ignore the knowledge base so it ships with the repo:
1. Edit `.gitignore` and remove/comment these lines:
   ```
   wiki/
   embeddings/
   ```
   (keep `raw/` and `.env` ignored - those are private intake + secrets)
2. Make sure `graph.json` is built (`python build_graph.py`).
3. Commit `wiki/`, `embeddings/`, and `graph.json`.

> Note: `graph.json` is not currently in `.gitignore` (only `raw/`, `wiki/`, `embeddings/`, `.env` are), so it will be committed by default once you `git add`.

### Option B - Keep notes private (empty demo)
Leave `.gitignore` as-is. The deployed app will start empty; visitors see "No notes yet" prompts. You (the owner) can capture/classify/link locally. This keeps your knowledge private but the public demo shows an empty brain.

**Recommendation**: For a portfolio/demo, Option A with your real (non-sensitive) learning notes makes the best impression. Do NOT commit passwords, keys, or truly private data.

---

## Option 1 - Streamlit Community Cloud (recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "SecondSelf: complete pipeline + Streamlit app"
   git push
   ```

   (Your `.env` is gitignored, so your key is never committed. Add `GROQ_API_KEY` as a secret in the platform dashboard, not in the repo.)

2. **Deploy**
   - Go to <https://share.streamlit.io>
   - Sign in with GitHub
   - Click **New app** -> choose your repo, branch `main`, file `app.py`
   - Under **Advanced settings**, add secret:
     ```
     GROQ_API_KEY = <your groq key>
     ```
   - Click **Deploy**

3. Your app is live at `https://<name>-<repo>-<hash>.streamlit.app`

---

## Option 2 - Hugging Face Spaces

1. Create a new Space at <https://huggingface.co/new-space>
   - SDK: **Streamlit**
   - Hardware: CPU basic (free)
2. Connect/clone the Space repo, push your code (same files as above).
3. Under **Settings -> Variables and secrets**, add `GROQ_API_KEY`.
4. The Space builds automatically and gives a public URL.

---

## Post-Deploy Checklist

- [ ] Public URL opens
- [ ] Graph tab renders the interactive graph
- [ ] Ask tab returns synthesized answers with sources
- [ ] Browse tab shows the notes table
- [ ] No errors in the app logs

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "GROQ_API_KEY not set" | Add the secret in the platform dashboard |
| Ask tab: "No embeddings found" | Commit `embeddings/` or run `link.py` before deploying |
| Graph tab empty | Build and commit `graph.json` (`python build_graph.py`) |
| App slow on first load | sentence-transformers downloads the model (~90MB) once; subsequent loads are cached |
| Build fails on install | Ensure `requirements.txt` uses the provided (unpinned) versions |