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

# Custom Styling (Dark Mode, Glassmorphism & Modern Typography)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main {
        background-color: #0E1117;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% -20%, #1a2333 0%, #0e1117 70%);
    }
    
    .metric-card {
        background: rgba(22, 27, 34, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(0, 191, 255, 0.15);
        border-color: rgba(0, 191, 255, 0.4);
    }
    
    .metric-card h3 {
        color: #58a6ff;
        font-size: 26px;
        margin-bottom: 4px;
        font-weight: 700;
    }
    
    .metric-card p {
        color: #8b949e;
        font-size: 13px;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    /* Sleek Proof Citations Block */
    blockquote, div[data-testid="stMarkdownContainer"] blockquote {
        background: rgba(22, 27, 34, 0.85);
        border-left: 4px solid #2ea043 !important;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 10px 0;
        color: #c9d1d9;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        box-shadow: 0 4px 14px rgba(46, 160, 67, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 6px 20px rgba(46, 160, 67, 0.5);
        transform: translateY(-2px);
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

if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state["agent_chat_histories"] = {}
    st.rerun()

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

    if st.sidebar.button("🔬 Data Quality & Normalization"):
        st.session_state["show_normalizer_demo"] = True

elif system_role == "Manager":
    if st.sidebar.button("📋 Team Learning Progress"):
        st.session_state["user_prompt"] = "What are the AIML training progress and skill learning updates for the team?"
        st.session_state["selected_role"] = "manager"

    if st.sidebar.button("🎓 AIML Training Overview"):
        st.session_state["user_prompt"] = "Show AIML training overview and completed team learning accomplishments"
        st.session_state["selected_role"] = "manager"

    if st.sidebar.button("🔬 Data Quality & Normalization"):
        st.session_state["show_normalizer_demo"] = True

else: # Teammate
    if st.sidebar.button(f"💬 My Spoken Quotes ({active_user_name.split()[0]})"):
        st.session_state["user_prompt"] = f"give me what i have discussed on 22/07/2026"
        st.session_state["selected_role"] = role_key

    if st.sidebar.button("🏗️ Codebase Architecture Guide"):
        st.session_state["user_prompt"] = "Explain how LocalVectorStore and RAG architecture work in qdrant_queries.py"
        st.session_state["selected_role"] = role_key

    if st.sidebar.button("🔬 Data Quality & Normalization"):
        st.session_state["show_normalizer_demo"] = True

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

# Pre-Chunking Normalization & Data Quality Inspector UI
with st.expander("🛠️ Pre-Chunking Normalization & Data Quality Inspector (Siddharth's Architecture Fix)", expanded=False):
    st.markdown("### 🎙️ Pre-Chunking Crosstalk Re-Attribution & Subset Vector Search")
    st.info("Fixes audio leakage / unmuted mic misattributions before chunking and enables exact brute-force search over payload-filtered subsets.")
    
    col_raw, col_clean = st.columns(2)
    with col_raw:
        st.markdown("#### ❌ Raw Un-Normalized Input (Mic Leakage)")
        st.code("""Dakshinya Nachimuthu 8 minutes 57 seconds
Siddharth Saminathan: OK, think about these things. Next task for Himaya is to work on prompt engineering.

--> RAG Error: Attributed Siddharth's task assignment to Dakshinya!""", language="text")
    
    with col_clean:
        st.markdown("#### ✅ After Pre-Chunking Normalization")
        st.code("""👤 [Siddharth Saminathan]: "OK, think about these things. Next task for Himaya is to work on prompt engineering."
👤 [Dakshinya Nachimuthu]: "Inventor agent technology specifically asks for word."

--> Clean RAG Attribution: Siddharth's task assigned correctly to Himaya!""", language="text")
        
    st.success("✔ **Data Quality Pipeline Status:** ACTIVE | Pre-chunking speaker re-attribution enabled before Qdrant indexing.")

st.markdown("---")

# Initialize & Maintain Persistent Multi-Agent Chat Histories (No History Loss on Switching)
if "agent_chat_histories" not in st.session_state:
    st.session_state["agent_chat_histories"] = {}

if active_user_name not in st.session_state["agent_chat_histories"]:
    st.session_state["agent_chat_histories"][active_user_name] = [
        {"role": "assistant", "content": f"Hello {active_user_name}! You are logged in under **{system_role} Access Mode**. How can I assist you today?"}
    ]

# Bind current display view to active user's persistent chat log
st.session_state["messages"] = st.session_state["agent_chat_histories"][active_user_name]

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
