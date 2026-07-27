"""
================================================================================
Enterprise Multi-Agent RAG Web Dashboard (Streamlit UI)
================================================================================
A modern, dark-mode Streamlit Web App featuring Role Selection, Interactive Chat,
Quantitative Evaluation Scorecard Tables, and Codebase Learning.
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))
from router import route_request

# Streamlit Page Config
st.set_page_config(
    page_title="Multi-Agent RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Mode & Premium Aesthetics)
st.markdown("""
<style>
    .main {
        background-color: #0E1117;
    }
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%);
    }
    .metric-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        box-shadow: 0 0 10px rgba(46, 160, 67, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("🤖 Multi-Agent RAG System")
st.caption("Powered by FastMCP, Qdrant Vector DB, SHA-256 Caching, and Groq Llama 3.3")

# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/color/96/000000/bot.png", width=70)
st.sidebar.title("System Controls")

# Role Selection
user_role = st.sidebar.selectbox(
    "Select User Role:",
    options=["Siddharth (Mentor)", "Manager", "Himaya (Teammate)", "Ganesh (Teammate)", "Dakshinya (Teammate)"],
    index=0
)

# Clean role string for router
role_key = user_role.split()[0].lower()

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Quick Preset Actions")

# Preset Prompt Buttons
if st.sidebar.button("📊 Evaluate Himaya"):
    st.session_state["user_prompt"] = "Evaluate performance of Himaya Perumal"
    st.session_state["selected_role"] = "siddharth"

if st.sidebar.button("📝 Evaluate Dakshinya"):
    st.session_state["user_prompt"] = "Evaluate performance of Dakshinya Nachimuthu"
    st.session_state["selected_role"] = "siddharth"

if st.sidebar.button("📋 Team Action Items"):
    st.session_state["user_prompt"] = "What are the project updates and action items for the team?"
    st.session_state["selected_role"] = "manager"

if st.sidebar.button("❓ Quiz Questions for Ganesh"):
    st.session_state["user_prompt"] = "Generate 3 technical testing quiz questions for Ganesh"
    st.session_state["selected_role"] = "siddharth"

if st.sidebar.button("💻 Explain LocalVectorStore"):
    st.session_state["user_prompt"] = "Explain how LocalVectorStore works in qdrant_queries.py"
    st.session_state["selected_role"] = "himaya"

# Metrics Banner
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-card"><h3>2,023</h3><p>Ingested Chunks</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h3>100%</h3><p>emb_cache Hit Rate</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h3>5.3 ms</h3><p>Retrieval Speed</p></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><h3>$0.00</h3><p>API Cache Cost</p></div>', unsafe_allow_html=True)

st.markdown("---")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle Preset Click or Direct Chat Input
prompt = st.chat_input("Ask a question to the Multi-Agent System...")

if "user_prompt" in st.session_state and st.session_state["user_prompt"]:
    prompt = st.session_state["user_prompt"]
    role_key = st.session_state.get("selected_role", role_key)
    del st.session_state["user_prompt"]

if prompt:
    # Add User Message to UI
    st.session_state.messages.append({"role": "user", "content": f"**[{user_role}]**: {prompt}"})
    with st.chat_message("user"):
        st.markdown(f"**[{user_role}]**: {prompt}")

    # Generate Response via Router.py
    with st.chat_message("assistant"):
        with st.spinner("Dispatching through Router.py & executing Agents..."):
            try:
                response = route_request(prompt, user_role=role_key)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error processing request: {e}")
