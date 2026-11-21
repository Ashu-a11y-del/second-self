import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="SecondSelf - Your Personal AI Second Brain",
    page_icon="🧠",
    layout="wide",
)

CATEGORY_COLORS = {
    "Projects": "#e74c3c",
    "Areas": "#3498db",
    "Resources": "#2ecc71",
    "Archives": "#95a5a6",
}


@st.cache_data
def load_graph():
    graph_path = Path("graph.json")
    if graph_path.exists():
        try:
            return json.loads(graph_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"nodes": [], "edges": [], "meta": {}}


st.markdown(
    """
<style>
.main-header { font-size: 28px; font-weight: 700; color: #1a1a2e; margin-bottom: 2px; }
.main-sub { font-size: 14px; color: #666; margin-bottom: 20px; }
.source-card { background: #f8f9fa; border-left: 3px solid #3498db; padding: 8px 12px; margin: 4px 0; border-radius: 0 6px 6px 0; }
.source-card-title { font-weight: 600; font-size: 13px; color: #2c3e50; }
.source-card-sim { font-size: 11px; color: #888; }
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("Notes per query", 1, 10, 5, help="Number of notes to retrieve for each question")
    st.markdown("---")
    graph = load_graph()
    st.metric("Notes", graph.get("meta", {}).get("total_nodes", 0))
    st.metric("Connections", graph.get("meta", {}).get("total_edges", 0))
    if st.button("Rebuild graph"):
        import build_graph

        build_graph.build_graph()
        st.cache_data.clear()
        st.success("Graph rebuilt. Refresh the page.")
        st.rerun()

st.markdown('<div class="main-header">SecondSelf</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-sub">Your Personal AI Second Brain - capture, organize, explore, ask.</div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["Graph", "Ask Your Brain", "Browse"])

with tab1:
    graph = load_graph()
    if not graph.get("nodes"):
        st.warning("No notes yet. Run capture.py, classify.py, link.py, then build_graph.py.")
    else:
        nodes_json = json.dumps(graph["nodes"])
        edges_json = json.dumps(graph["edges"])
        colors_json = json.dumps(CATEGORY_COLORS)

        graph_html = """
<!DOCTYPE html>
<html>
<head>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    #network { width: 100%; height: 600px; background: #fafafa; }
    .vis-tooltip { background: #1a1a2e !important; color: #eee !important; border: 1px solid #444 !important; font-size: 12px !important; padding: 8px !important; max-width: 320px !important; white-space: pre-wrap !important; }
  </style>
</head>
<body>
  <div id="network"></div>
  <script>
    const graph = {"nodes": __NODES__, "edges": __EDGES__};
    const catColors = __COLORS__;

    const nodes = new vis.DataSet(graph.nodes.map(n => ({
      id: n.id,
      label: n.label && n.label.length > 25 ? n.label.substring(0, 25) + '...' : (n.label || n.id.slice(0,8)),
      title: (n.summary || n.label || '') + '\\n\\nTags: ' + (n.tags || []).join(', ') + '\\nConnections: ' + (n.degree || 0),
      color: { background: catColors[n.category] || '#888', border: '#fff' },
      size: 15 + (n.degree || 0) * 4,
      font: { color: '#333', size: 11 },
      borderWidth: 2,
      shadow: { enabled: true, color: 'rgba(0,0,0,0.15)' }
    })));

    const edges = new vis.DataSet(graph.edges.map(e => ({
      from: e.from,
      to: e.to,
      width: Math.max(1, (e.weight || 0.5) * 3),
      color: { color: '#999', opacity: 0.5 },
      title: 'Similarity: ' + (e.weight != null ? e.weight : 'N/A')
    })));

    const container = document.getElementById('network');
    const data = { nodes, edges };
    const options = {
      physics: {
        forceAtlas2Based: { gravitationalConstant: -60, centralGravity: 0.01, springLength: 150, springConstant: 0.08, damping: 0.4 },
        stabilization: { iterations: 200 }
      },
      interaction: { hover: true, dragNodes: true, zoomView: true, dragView: true, tooltipDelay: 200, navigationButtons: true }
    };

    const network = new vis.Network(container, data, options);

    network.on('hoverNode', params => { nodes.update({ id: params.node, size: 40 }); });
    network.on('blurNode', params => {
      const node = nodes.get(params.node);
      nodes.update({ id: params.node, size: 15 + ((node && node.degree) || 0) * 4 });
    });
  </script>
</body>
</html>
"""
        graph_html = (
            graph_html.replace("__NODES__", nodes_json)
            .replace("__EDGES__", edges_json)
            .replace("__COLORS__", colors_json)
        )

        components.html(graph_html, height=620)

        legend = "".join(
            f'<span style="display:inline-block;width:12px;height:12px;background:{color};border-radius:50%;margin-right:4px;"></span>{cat}'
            for cat, color in CATEGORY_COLORS.items()
        )
        st.markdown(
            f'<div style="display:flex;gap:16px;justify-content:center;padding:8px 0;font-size:12px;color:#666;">{legend}</div>',
            unsafe_allow_html=True,
        )

with tab2:
    st.markdown("### Ask Your Brain")
    st.markdown("Ask any question in plain English. Answers are synthesized from your notes.")

    question = st.text_input(
        "Your question:",
        placeholder="e.g., What are my current projects? What have I been reading about?",
        key="question_input",
    )

    if st.button("Ask", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Searching your notes..."):
                try:
                    from ask import ask

                    os.environ.setdefault("TOP_K_RETRIEVAL", str(top_k))
                    result = ask(question.strip())

                    st.markdown("#### Answer")
                    st.markdown(result["answer"])

                    if result.get("sources"):
                        st.markdown("#### Sources")
                        for i, src in enumerate(result["sources"], 1):
                            st.markdown(
                                f"""
                                <div class="source-card">
                                  <div class="source-card-title">[{i}] {src.get('title', src['id'])}</div>
                                  <div class="source-card-sim">Similarity: {src['similarity']:.3f}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info("No relevant notes found for this question.")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab3:
    st.markdown("### Browse All Notes")

    graph = load_graph()
    nodes = graph.get("nodes", [])

    if not nodes:
        st.info("No notes yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            categories = ["All"] + sorted(list({n.get("category", "") for n in nodes}))
            selected_cat = st.selectbox("Category", categories)
        with col2:
            all_tags = sorted({tag for n in nodes for tag in n.get("tags", [])})
            selected_tag = st.selectbox("Tag", ["All"] + all_tags)

        filtered = nodes
        if selected_cat != "All":
            filtered = [n for n in filtered if n.get("category") == selected_cat]
        if selected_tag != "All":
            filtered = [n for n in filtered if selected_tag in n.get("tags", [])]

        if filtered:
            import pandas as pd

            df = pd.DataFrame(
                [
                    {
                        "Title": n.get("label", "")[:50],
                        "Category": n.get("category", ""),
                        "Tags": ", ".join(n.get("tags", [])),
                        "Connections": n.get("degree", 0),
                        "Summary": n.get("summary", ""),
                    }
                    for n in filtered
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(filtered)} of {len(nodes)} notes")
        else:
            st.info("No notes match the selected filters.")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#999;font-size:11px;'>"
    "SecondSelf - Your Personal AI Second Brain - "
    "Capture -> Classify -> Link -> Graph -> Ask"
    "</div>",
    unsafe_allow_html=True,
)