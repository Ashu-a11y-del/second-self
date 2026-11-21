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