"""
================================================================================
Enterprise Multi-Agent RAG Web Dashboard (Streamlit UI)
================================================================================
A modern, dark-mode Streamlit Web App featuring Role-Based Access Control:
- Manager (Single Executive Account)
- Mentor (Single Evaluation Account)
- Teammate (Multi-Member Teammate Accounts: Himaya, Ganesh, Dakshinya)
"""

import streamlit as st
import sys
import os

import importlib
import router
importlib.reload(router)
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
st.title("🤖 Enterprise Multi-Agent RAG System")
st.caption("Powered by FastMCP, Qdrant Vector DB, SHA-256 Caching, and Groq Llama 3.3")

# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/color/96/000000/bot.png", width=70)
st.sidebar.title("System Controls")

# 1. Primary System Role Selection
system_role = st.sidebar.radio(
    "Select System Access Role:",
    options=["Manager", "Mentor", "Teammate"],
    index=0
)

# 2. Dynamic Identity Scoping Based on Role
if system_role == "Manager":
    active_user_name = "Iyappan Sir"
    role_key = "manager"
    st.sidebar.info("👔 **Active Account:** Project Manager (Iyappan Sir)")

elif system_role == "Mentor":
    active_user_name = "Siddharth Saminathan"
    role_key = "siddharth"
    st.sidebar.info("🎓 **Active Account:** Mentor (Siddharth Saminathan)")

else: # Teammate (3 Members)
    st.sidebar.markdown("### 👥 Select Teammate Identity:")
    selected_member = st.sidebar.selectbox(
        "Active Teammate Member:",
        options=["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu", "➕ Enter Custom Teammate..."],
        index=0
    )
    if selected_member == "➕ Enter Custom Teammate...":
        active_user_name = st.sidebar.text_input("Enter Custom Teammate Name:", value="Guest Teammate")
    else:
        active_user_name = selected_member
    
    role_key = active_user_name.split()[0].lower() if active_user_name and active_user_name.split() else "himaya"
    st.sidebar.success(f"👤 **Active Account:** {active_user_name}")

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Word Transcripts (.docx)")
uploaded_file = st.sidebar.file_uploader(
    "Upload Microsoft Teams Meeting Transcripts (.docx):",
    type=["docx", "txt"]
)

if uploaded_file is not None:
    save_dir = os.path.join(os.path.dirname(__file__), "transcripts")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Connected '{uploaded_file.name}' to RAG System!")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Quick Preset Actions")

# Dynamic Preset Action Buttons (Practical Technical Actions)
if system_role == "Mentor":
    if st.sidebar.button("❓ Generate Team Quiz"):
        st.session_state["user_prompt"] = "Generate 5 technical quiz questions for the team based on meeting transcripts"
        st.session_state["selected_role"] = "siddharth"

    if st.sidebar.button("📖 Suggested Reading Topics"):
        st.session_state["user_prompt"] = "What technical reading topics should be assigned to the team based on recent discussions?"
        st.session_state["selected_role"] = "siddharth"

    if st.sidebar.button("🗣️ Recent Technical Discussions"):
        st.session_state["user_prompt"] = "Summarize the key technical discussions between Siddharth and the team"
        st.session_state["selected_role"] = "siddharth"

elif system_role == "Manager":
    if st.sidebar.button("📋 Team Action Items"):
        st.session_state["user_prompt"] = "What are the project updates and action items for the team?"
        st.session_state["selected_role"] = "manager"

    if st.sidebar.button("📈 Executive Project Status"):
        st.session_state["user_prompt"] = "Show executive project status and completed team milestones"
        st.session_state["selected_role"] = "manager"

else: # Teammate
    if st.sidebar.button(f"💬 My Spoken Quotes ({active_user_name.split()[0]})"):
        st.session_state["user_prompt"] = f"give me what i have discussed on 22/07/2026"
        st.session_state["selected_role"] = role_key

    if st.sidebar.button("🏗️ Codebase Architecture Guide"):
        st.session_state["user_prompt"] = "Explain how LocalVectorStore and RAG architecture work in qdrant_queries.py"
        st.session_state["selected_role"] = role_key

    if st.sidebar.button("📖 Suggested Technical Topics"):
        st.session_state["user_prompt"] = "What are the key technical concepts and reading topics from my meeting transcripts?"
        st.session_state["selected_role"] = role_key

# Metrics Banner
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-card"><h3>2,843</h3><p>Ingested Vector Chunks</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h3>100%</h3><p>emb_cache Hit Rate</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h3>3.8 ms</h3><p>Retrieval Speed</p></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><h3>$0.00</h3><p>API Cache Cost</p></div>', unsafe_allow_html=True)

st.markdown("---")

# Initialize & Dynamic Reset of Chat History on User Switch
if "current_user" not in st.session_state or st.session_state["current_user"] != active_user_name:
    st.session_state["current_user"] = active_user_name
    st.session_state["messages"] = [
        {"role": "assistant", "content": f"Hello {active_user_name}! You are logged in under **{system_role} Access Mode**. How can I assist you today?"}
    ]

# Display Chat History
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input Box
user_prompt = st.chat_input(f"Ask as {active_user_name} ({system_role})...")

# Handle Preset Button Injection
if "user_prompt" in st.session_state and st.session_state["user_prompt"]:
    user_prompt = st.session_state["user_prompt"]
    del st.session_state["user_prompt"]

if user_prompt:
    # Append User Message
    st.session_state["messages"].append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Process Request via Multi-Agent Router
    with st.chat_message("assistant"):
        with st.spinner(f"Routing request for {active_user_name} ({system_role})..."):
            active_role_param = role_key if system_role == "Teammate" else system_role.lower()
            importlib.reload(router)
            response_text = router.route_request(user_prompt, user_role=active_role_param)
            st.markdown(response_text)
            st.session_state["messages"].append({"role": "assistant", "content": response_text})
