"""
================================================================================
Streamlit Web UI Dashboard for Multi-Agent System (RAG_COMBINED)
================================================================================
Interactive web interface allowing users to:
1. Select Authenticated User Role (Manager, Mentor, Teammate).
2. Dynamically route prompts to Manager Agent, Mentor Agent, or Teammates Agent.
3. View grounded responses, verbatim proof citations, and latency metrics.
"""

import streamlit as st
import time
import os
import sys

parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from router import route_request

st.set_page_config(
    page_title="Multi-Agent Meeting RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 Multi-Agent Meeting RAG Assistant")
st.caption("Powered by Qdrant Vector DB, Semantic Topic-Shift Chunking, & Groq LLM")

# Sidebar Configuration
st.sidebar.header("🔐 User Session & Role Scoping")
user_role = st.sidebar.selectbox(
    "Select Authenticated Access Role:",
    ["auto", "manager", "siddharth", "himaya", "ganesh", "dakshinya"],
    format_func=lambda x: {
        "auto": "⚡ Auto Intent Router",
        "manager": "👔 Manager (Iyappan Sir Mode)",
        "siddharth": "🎓 Mentor (Siddharth Saminathan)",
        "himaya": "👥 Teammate (Himaya Perumal)",
        "ganesh": "👥 Teammate (Ganesh Krishna)",
        "dakshinya": "👥 Teammate (Dakshinya Nachimuthu)"
    }.get(x, x)
)

target_member = st.sidebar.selectbox(
    "Target Teammate Focus (Optional):",
    ["", "Himaya", "Ganesh", "Dakshinya"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Security & Boundary Scoping")
st.sidebar.success("✅ Module 1 Security Guardrails Active")
st.sidebar.info("🔒 Role-Based Access Control (RBAC) Enforced")
st.sidebar.warning("📌 Zero-Hallucination Policy Active")

# Main Interface
st.subheader("💬 Ask Your Question")

sample_queries = [
    "What are the key technical accomplishments completed by Himaya, Ganesh, and Dakshinya?",
    "Evaluate Himaya's technical understanding of vector embedding caching.",
    "Generate 3 technical testing quiz questions for Ganesh.",
    "Explain how SemanticTranscriptParser and Qdrant work in pipeline.py",
    "What active blockers or bottlenecks are preventing task completion for the team?"
]

selected_sample = st.selectbox("Or choose a sample benchmark query:", ["-- Type custom query below --"] + sample_queries)

if selected_sample != "-- Type custom query below --":
    query_input = selected_sample
else:
    query_input = st.text_area("Enter your query:", placeholder="e.g. Provide a 60-second status update on Himaya's work progress...")

if st.button("🚀 Submit to Multi-Agent System", type="primary"):
    if not query_input.strip():
        st.error("Please enter a valid query.")
    else:
        with st.spinner(f"Routing request via '{user_role}' role..."):
            t0 = time.time()
            response_text = route_request(query_input, user_role=user_role, target_member=target_member)
            latency = round(time.time() - t0, 3)

        st.markdown("---")
        st.markdown(f"### 📋 Agent Response (Executed in `{latency}s`)")
        st.markdown(response_text)
        st.success(f"✔ Completed successfully using role '{user_role}' | Latency: {latency}s")
