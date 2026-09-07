import streamlit as st
import time
from datetime import datetime
from src.agents.agents import build_search_agent, build_reader_agent, writer_chain, critic_chain


# ── Pipeline logger ──────────────────────────────────────────────────────────
class PipelineLogger:
    """Captures what each step produced and what was handed to the next."""

    def __init__(self):
        self.entries: list[dict] = []
        self._start: float | None = None

    def start_run(self, topic: str):
        self.entries = []
        self._start = time.time()
        self._log("pipeline", "start", f"Topic: {topic}")

    def step_done(self, step: str, output: str, next_input: str | None = None):
        elapsed = round(time.time() - self._start, 1) if self._start else 0
        self._log(step, "output", self._trim(output), elapsed)
        if next_input is not None:
            self._log(step, "→ next input", self._trim(next_input), elapsed)

    def end_run(self):
        elapsed = round(time.time() - self._start, 1) if self._start else 0
        self._log("pipeline", "done", f"Total time: {elapsed}s", elapsed)

    # ── internals ──
    def _log(self, step: str, event: str, text: str, elapsed: float = 0):
        self.entries.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "elapsed": elapsed,
            "step": step,
            "event": event,
            "text": text,
        })

    @staticmethod
    def _trim(s: str, limit: int = 600) -> str:
        s = s.strip()
        if len(s) <= limit:
            return s
        return s[:limit] + f"  … [{len(s)} chars total]"

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

/* ── Result card ── */
.result-card {
    background: #fff;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.result-card-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
    margin-bottom: 0.8rem;
}
.result-card-body {
    font-size: 0.88rem;
    line-height: 1.75;
    color: #333;
    white-space: pre-wrap;
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

/* ── Feedback card ── */
.feedback-card {
    background: #f8fdf8;
    border: 1px solid #d4edd4;
    border-radius: 12px;
    padding: 1.8rem;
    margin-bottom: 1rem;
}

/* ── Expander ── */
details {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #eaeaea;
    padding: 0.2rem 0.6rem;
    margin-bottom: 0.5rem;
}
details summary {
    font-size: 0.82rem !important;
    color: #555 !important;
    cursor: pointer;
    font-weight: 500 !important;
}

/* ── Log viewer ── */
.log-container {
    background: #1a1a1a;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-top: 0.5rem;
    max-height: 420px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.76rem;
    line-height: 1.7;
}
.log-entry {
    display: flex;
    gap: 0.6rem;
    padding: 0.15rem 0;
    border-bottom: 1px solid #2a2a2a;
}
.log-entry:last-child { border-bottom: none; }
.log-ts {
    color: #666;
    flex-shrink: 0;
    min-width: 60px;
}
.log-elapsed {
    color: #555;
    flex-shrink: 0;
    min-width: 48px;
    text-align: right;
}
.log-step {
    color: #7cacf8;
    flex-shrink: 0;
    min-width: 72px;
    font-weight: 600;
}
.log-event {
    color: #a8d8a8;
    flex-shrink: 0;
    min-width: 80px;
}
.log-event.input-event { color: #e8c77b; }
.log-text {
    color: #ccc;
    white-space: pre-wrap;
    word-break: break-word;
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

if "logger" not in st.session_state:
    st.session_state.logger = PipelineLogger()


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
    log = st.session_state.logger
    log.start_run(topic_val)

    # ── Step 1: Search ──
    with st.spinner("Searching the web…"):
        search_agent = build_search_agent()
        search_input = f"Find recent, reliable and detailed information about: {topic_val}"
        sr = search_agent.invoke({
            "messages": [("user", search_input)]
        })
        results["search"] = sr["messages"][-1].content
        st.session_state.results = dict(results)

        reader_input_preview = (
            f"Based on the following search results about '{topic_val}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{results['search'][:800]}"
        )
        log.step_done("search", results["search"], next_input=reader_input_preview)

    # ── Step 2: Reader ──
    with st.spinner("Reading top sources…"):
        reader_agent = build_reader_agent()
        rr = reader_agent.invoke({
            "messages": [("user", reader_input_preview)]
        })
        results["reader"] = rr["messages"][-1].content
        st.session_state.results = dict(results)

        writer_input_preview = (
            f"SEARCH RESULTS:\n{results['search']}\n\n"
            f"DETAILED SCRAPED CONTENT:\n{results['reader']}"
        )
        log.step_done("reader", results["reader"], next_input=writer_input_preview)

    # ── Step 3: Writer ──
    with st.spinner("Writing the report…"):
        results["writer"] = writer_chain.invoke({
            "topic": topic_val,
            "research": writer_input_preview,
        })
        st.session_state.results = dict(results)
        log.step_done("writer", results["writer"], next_input=results["writer"])

    # ── Step 4: Critic ──
    with st.spinner("Reviewing the report…"):
        results["critic"] = critic_chain.invoke({
            "report": results["writer"],
        })
        st.session_state.results = dict(results)
        log.step_done("critic", results["critic"])

    log.end_run()
    st.session_state.running = False
    st.session_state.done = True
    st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
r = st.session_state.results

if r:
    st.markdown('<div class="section-label">Results</div>', unsafe_allow_html=True)

    if "search" in r:
        with st.expander("🔍 Search results", expanded=False):
            st.markdown(
                f'<div class="result-card"><div class="result-card-body">{r["search"]}</div></div>',
                unsafe_allow_html=True,
            )

    if "reader" in r:
        with st.expander("📄 Scraped content", expanded=False):
            st.markdown(
                f'<div class="result-card"><div class="result-card-body">{r["reader"]}</div></div>',
                unsafe_allow_html=True,
            )

    if "writer" in r:
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown(r["writer"])
        st.markdown("</div>", unsafe_allow_html=True)

        st.download_button(
            label="Download report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    if "critic" in r:
        st.markdown('<div class="feedback-card">', unsafe_allow_html=True)
        st.markdown(r["critic"])
        st.markdown("</div>", unsafe_allow_html=True)


# ── Pipeline logs ─────────────────────────────────────────────────────────────
log = st.session_state.logger

if log.entries:
    st.markdown('<div class="section-label">Logs</div>', unsafe_allow_html=True)

    with st.expander(f"🪵 Pipeline log ({len(log.entries)} entries)", expanded=False):
        rows = ""
        for e in log.entries:
            evt_cls = "input-event" if "input" in e["event"] else ""
            rows += (
                f'<div class="log-entry">'
                f'<span class="log-ts">{e["time"]}</span>'
                f'<span class="log-elapsed">{e["elapsed"]}s</span>'
                f'<span class="log-step">{e["step"]}</span>'
                f'<span class="log-event {evt_cls}">{e["event"]}</span>'
                f'<span class="log-text">{e["text"]}</span>'
                f'</div>'
            )
        st.markdown(f'<div class="log-container">{rows}</div>', unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer-note">Research Agent · LangChain multi-agent pipeline · Streamlit</div>',
    unsafe_allow_html=True,
)