import streamlit as st
import time
from src.agents.agents import build_search_agent, build_reader_agent, writer_chain, critic_chain


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #1a1a1a;
}

.stApp {
    background: #fafafa;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2.5rem 2rem 4rem; max-width: 780px; }

/* ── Header ── */
.page-header {
    padding: 2rem 0 1.5rem;
}
.page-header h1 {
    font-family: 'Source Serif 4', serif;
    font-size: 2rem;
    font-weight: 600;
    color: #111;
    margin: 0 0 0.4rem;
    line-height: 1.2;
}
.page-header p {
    font-size: 0.9rem;
    color: #666;
    margin: 0;
    line-height: 1.5;
}

/* ── Input area ── */
.stTextInput > div > div > input {
    background: #fff !important;
    border: 1.5px solid #ddd !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.15s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: #333 !important;
    box-shadow: none !important;
}
.stTextInput > label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: #444 !important;
}

/* ── Button ── */
.stButton > button {
    background: #111 !important;
    color: #fff !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.5rem !important;
    cursor: pointer !important;
    transition: background 0.15s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: #333 !important;
}

/* ── Pipeline steps ── */
.step-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid #eee;
}
.step-row:last-child { border-bottom: none; }
.step-icon {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    flex-shrink: 0;
}
.step-icon.waiting { background: #f0f0f0; color: #aaa; }
.step-icon.running { background: #e8f4fd; color: #2196f3; }
.step-icon.done    { background: #e8f5e9; color: #4caf50; }
.step-name {
    font-size: 0.88rem;
    font-weight: 500;
    color: #222;
    flex: 1;
}
.step-badge {
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.15rem 0.55rem;
    border-radius: 6px;
}
.step-badge.waiting { background: #f5f5f5; color: #999; }
.step-badge.running { background: #e3f2fd; color: #1976d2; }
.step-badge.done    { background: #e8f5e9; color: #388e3c; }

/* ── Section label ── */
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #999;
    margin: 2rem 0 0.6rem;
}

/* ── Report ── */
.report-card {
    background: #fff;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 1.8rem;
    margin-bottom: 1rem;
}
.report-card h1, .report-card h2, .report-card h3 {
    font-family: 'Source Serif 4', serif;
    color: #111;
}

/* ── Footer ── */
.footer-note {
    text-align: center;
    font-size: 0.72rem;
    color: #bbb;
    margin-top: 3rem;
}

/* ── Spinner ── */
.stSpinner > div { color: #555 !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: #fff !important;
    color: #333 !important;
    border: 1.5px solid #ddd !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 1.2rem !important;
}
.stDownloadButton > button:hover {
    border-color: #999 !important;
    background: #fafafa !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
for key in ("results", "running", "done"):
    if key not in st.session_state:
        st.session_state[key] = {} if key == "results" else False


# ── Helper: pipeline step status ──────────────────────────────────────────────
def get_step_state(step):
    r = st.session_state.results
    if not r:
        return "waiting"
    steps = ["search", "reader", "writer", "critic"]
    if step in r:
        return "done"
    if st.session_state.running:
        for k in steps:
            if k not in r:
                return "running" if k == step else "waiting"
    return "waiting"


def render_step(icon_text, name, state):
    icons = {"waiting": "○", "running": "◉", "done": "✓"}
    labels = {"waiting": "Waiting", "running": "Running", "done": "Done"}
    st.markdown(f"""
    <div class="step-row">
        <div class="step-icon {state}">{icons[state]}</div>
        <span class="step-name">{icon_text} {name}</span>
        <span class="step-badge {state}">{labels[state]}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>Research Agent</h1>
    <p>Four AI agents collaborate to search, read, write, and critique a research report on any topic.</p>
</div>
""", unsafe_allow_html=True)


# ── Input ─────────────────────────────────────────────────────────────────────
topic = st.text_input(
    "Topic",
    placeholder="e.g. The impact of AI agents on software development",
    key="topic_input",
    label_visibility="visible",
)

st.button("Run research pipeline", key="run_btn", use_container_width=True)


# ── Pipeline status ───────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Pipeline</div>', unsafe_allow_html=True)

render_step("🔍", "Search", get_step_state("search"))
render_step("📄", "Reader", get_step_state("reader"))
render_step("✍️", "Writer", get_step_state("writer"))
render_step("🧐", "Critic", get_step_state("critic"))


# ── Trigger pipeline ─────────────────────────────────────────────────────────
if st.session_state.run_btn:
    if not topic.strip():
        st.warning("Enter a research topic to get started.")
    else:
        st.session_state.results = {}
        st.session_state.running = True
        st.session_state.done = False
        st.rerun()


# ── Run pipeline ──────────────────────────────────────────────────────────────
if st.session_state.running and not st.session_state.done:

    results = {}
    topic_val = st.session_state.topic_input

    # ── Step 1: Search ──
    with st.spinner("Searching the web…"):
        search_agent = build_search_agent()
        search_input = f"Find recent, reliable and detailed information about: {topic_val}"
        sr = search_agent.invoke({
            "messages": [("user", search_input)]
        })
        results["search"] = sr["messages"][-1].content
        st.session_state.results = dict(results)

        reader_input = (
            f"Based on the following search results about '{topic_val}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{results['search'][:800]}"
        )

    # ── Step 2: Reader ──
    with st.spinner("Reading top sources…"):
        reader_agent = build_reader_agent()
        rr = reader_agent.invoke({
            "messages": [("user", reader_input)]
        })
        results["reader"] = rr["messages"][-1].content
        st.session_state.results = dict(results)

        writer_input = (
            f"SEARCH RESULTS:\n{results['search']}\n\n"
            f"DETAILED SCRAPED CONTENT:\n{results['reader']}"
        )

    # ── Step 3: Writer ──
    with st.spinner("Writing the report…"):
        results["writer"] = writer_chain.invoke({
            "topic": topic_val,
            "research": writer_input,
        })
        st.session_state.results = dict(results)

    # ── Step 4: Critic ──
    with st.spinner("Reviewing the report…"):
        results["critic"] = critic_chain.invoke({
            "report": results["writer"],
        })
        st.session_state.results = dict(results)

    st.session_state.running = False
    st.session_state.done = True
    st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
r = st.session_state.results

if "writer" in r:
    st.markdown('<div class="section-label">Report</div>', unsafe_allow_html=True)

    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.markdown(r["writer"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        label="Download report (.md)",
        data=r["writer"],
        file_name=f"research_report_{int(time.time())}.md",
        mime="text/markdown",
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer-note">Research Agent · LangChain multi-agent pipeline · Streamlit</div>',
    unsafe_allow_html=True,
)