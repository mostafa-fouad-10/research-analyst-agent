import uuid

import streamlit as st
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# CHANGE THIS: the file where your MAIN graph (the one with "conduct_interview") lives.
# We import the *builder*, not the compiled graph, so we can attach a checkpointer here.
from deep_agent import builder

st.set_page_config(page_title="Research Assistant", page_icon="🔎", layout="wide")

st.markdown(
    """
    <style>
    html { font-size: 21px; }   /* default is 16px; try 18-24 */
    h1 { font-size: 2.6rem !important; }
    h2, h3 { font-size: 2rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
# ---------------------------------------------------------------- graph
@st.cache_resource
def get_graph():
    # MemorySaver lives in RAM -> the graph object must survive Streamlit reruns,
    # otherwise the saved state (and the pending interrupt) would be lost.
    return builder.compile(checkpointer=MemorySaver())


graph = get_graph()


# ---------------------------------------------------------------- session state
def reset():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.phase = "input"  # input -> review -> done
    st.session_state.analysts = []
    st.session_state.report = None


if "thread_id" not in st.session_state:
    reset()


def cfg():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def pending_interrupt():
    """Return the payload of the interrupt the graph is paused on (or None)."""
    snap = graph.get_state(cfg())
    for task in snap.tasks:
        for it in task.interrupts:
            return it.value
    return None


def show_review(payload):
    st.session_state.analysts = payload["analysts"] if payload else []
    st.session_state.phase = "review"


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🔎 Research Assistant")
    st.caption("Analysts interview an expert (web search) and write a report.")
    if st.session_state.phase != "input":
        if st.button("↺ Start over", use_container_width=True):
            reset()
            st.rerun()

# ---------------------------------------------------------------- phase 1: input
if st.session_state.phase == "input":
    topic = st.text_input("Research topic", placeholder="e.g. Benefits of adopting LangGraph")
    max_analysts = st.slider("Number of analysts", 1, 5, 3)

    if st.button("Generate analysts", type="primary", disabled=not topic.strip()):
        st.session_state.thread_id = str(uuid.uuid4())  # fresh thread per run
        with st.spinner("Creating analysts..."):
            graph.invoke({"topic": topic.strip(), "max_analysts": max_analysts}, cfg())
        show_review(pending_interrupt())
        st.rerun()

# ---------------------------------------------------------------- phase 2: human review
elif st.session_state.phase == "review":
    st.subheader("Review the analysts")

    for a in st.session_state.analysts:
        with st.container(border=True):
            st.markdown(f"**{a['name']}**")
            st.caption(f"{a['role']} · {a['affiliation']}")
            st.write(a["description"])

    feedback = st.text_area(
        "Feedback (only needed if you want to regenerate)",
        placeholder="e.g. Add an analyst focused on cost / security...",
    )

    c1, c2, _ = st.columns([1, 1, 3])

    if c1.button("✅ Approve & run", type="primary"):
        with st.status("Running interviews and writing the report...", expanded=True) as status:
            # resume=... becomes the return value of interrupt() inside human_feedback
            for namespace, update in graph.stream(
                Command(resume="continue"),
                cfg(),
                stream_mode="updates",
                subgraphs=True,
            ):
                for node in update:
                    if node.startswith("__"):
                        continue
                    where = " › ".join(n.split(":")[0] for n in namespace)
                    st.write(f"✔ {where + ' › ' if where else ''}{node}")
            status.update(label="Done", state="complete")

        st.session_state.report = graph.get_state(cfg()).values.get("final_report")
        st.session_state.phase = "done"
        st.rerun()

    if c2.button("🔁 Regenerate", disabled=not feedback.strip()):
        with st.spinner("Regenerating analysts..."):
            graph.invoke(Command(resume=feedback.strip()), cfg())
        show_review(pending_interrupt())
        st.rerun()

# ---------------------------------------------------------------- phase 3: report
else:
    report = st.session_state.report
    if report:
        st.markdown(report)
        st.download_button("⬇ Download report (.md)", report, file_name="report.md", mime="text/markdown")
    else:
        st.error("The graph finished but no final_report was produced.")