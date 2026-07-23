"""AskTheCompany — Sleek Streamlit RAG Interface.
Runs the entire NexusRAG query and ingestion pipeline directly in-memory.
Supports dynamic ACL role selection, real-time citation rendering, and index management.
"""

import sys
import os
from pathlib import Path
import streamlit as st

# Setup PYTHONPATH so local packages imports resolve correctly
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force query rewriting and reranker to be disabled for standard cloud tier reliability
os.environ["USE_QUERY_REWRITING"] = "false"
os.environ["USE_RERANKER"] = "false"

from src.pipeline.query import QueryPipeline
from src.pipeline.ingest import IngestionPipeline

# ---------------------------------------------------------------------------
# Streamlit Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AskTheCompany — Enterprise RAG Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    /* Premium clean aesthetics */
    .reportview-container {
        background: #0F0F11;
    }
    .stChatInput {
        border-radius: 12px !important;
    }
    .role-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.85em;
        font-weight: bold;
        color: white;
        margin-right: 5px;
    }
    .badge-engineering { background: #3B82F6; }
    .badge-hr { background: #EC4899; }
    .badge-exec { background: #10B981; }
    .badge-finance { background: #F59E0B; }
    .badge-all { background: #6B7280; }
    
    .citation-card {
        border-left: 4px solid #8B5CF6;
        background: #1E1E24;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Profiles Configuration (matching permissions.json)
# ---------------------------------------------------------------------------
USER_PROFILES = {
    "alice": {"name": "Alice Chen", "title": "Senior Engineer", "roles": ["engineering", "all"], "avatar": "👩‍💻"},
    "bob": {"name": "Bob Martinez", "title": "VP Product", "roles": ["product", "exec", "all"], "avatar": "👨‍💼"},
    "carol": {"name": "Carol Williams", "title": "HR Manager", "roles": ["hr", "all"], "avatar": "👩‍💼"},
    "dave": {"name": "Dave Kumar", "title": "Finance Analyst", "roles": ["finance", "all"], "avatar": "📊"},
    "frank": {"name": "Frank Intern", "title": "Summer Intern", "roles": ["all"], "avatar": "🧑‍🎓"}
}

# ---------------------------------------------------------------------------
# Lazy Cache Pipelines
# ---------------------------------------------------------------------------
@st.cache_resource
def get_query_pipeline():
    return QueryPipeline()

@st.cache_resource
def get_ingestion_pipeline():
    return IngestionPipeline()

# Initialize session state for messages and active citations
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latest_citations" not in st.session_state:
    st.session_state.latest_citations = []
if "latest_latency" not in st.session_state:
    st.session_state.latest_latency = 0.0

# ---------------------------------------------------------------------------
# Sidebar Panel
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚡ AskTheCompany")
    st.subheader("Security Context (ACL)")
    
    # User Profile Switcher
    selected_username = st.selectbox(
        "Active Identity",
        options=list(USER_PROFILES.keys()),
        format_func=lambda u: f"{USER_PROFILES[u]['name']} ({USER_PROFILES[u]['title']})"
    )
    
    profile = USER_PROFILES[selected_username]
    
    # Render Roles Badges
    st.write("**Active Roles:**")
    role_html = ""
    for r in profile["roles"]:
        role_html += f'<span class="role-badge badge-{r}">{r}</span>'
    st.markdown(role_html, unsafe_allow_html=True)
    st.markdown("---")
    
    # Latency badge
    if st.session_state.latest_latency > 0:
        st.metric(
            label="System Latency",
            value=f"{st.session_state.latest_latency:.0f} ms",
            delta=None
        )
        st.markdown("---")

    # Ingestion Controls
    st.subheader("Database Management")
    if st.button("🔄 Re-ingest Index", use_container_width=True):
        with st.spinner("Parsing and indexing documents..."):
            try:
                pipeline_ingest = get_ingestion_pipeline()
                stats = pipeline_ingest.ingest_directory(Path("./data"), recreate_collection=True)
                st.success(f"Success! Ingested {stats['files_processed']} files into {stats['canonical_count']} chunks ({stats['duplicates_flagged']} duplicates merged).")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")
                
    st.markdown("---")

    # Sidebar Citations List
    st.subheader("📖 Sources & Citations")
    if st.session_state.latest_citations:
        for idx, cite in enumerate(st.session_state.latest_citations, 1):
            source_type = cite.get("type", "unknown")
            icon = "📎"
            if "pdf" in source_type:
                icon = "📄"
            elif "markdown" in source_type or "confluence" in source_type:
                icon = "📝"
            elif "spreadsheet" in source_type or "csv" in source_type:
                icon = "📊"
            elif "slack" in source_type:
                icon = "💬"
            
            with st.expander(f"[{cite.get('index', idx)}] {icon} {cite.get('title')}"):
                st.markdown(f"**Path/Section:** `{cite.get('heading_path')}`")
                st.markdown(f"*Confidence Score: {cite.get('score', 0.0):.3f}*")
                st.write(cite.get("text"))
    else:
        st.info("Ask a query to view citations.")

# ---------------------------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------------------------
st.title("Enterprise RAG Assistant")
st.caption("Ask questions about internal guidelines, budgets, schedules, or onboarding procedures.")

# Render Welcome message
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="⚡"):
        st.write("Hello! I am your AskTheCompany Enterprise Assistant. Ask me anything about internal guidelines, budgets, schedules, or onboarding procedures.")

# Render Chat History
for msg in st.session_state.messages:
    avatar = "⚡" if msg["role"] == "assistant" else USER_PROFILES[msg.get("username", "frank")]["avatar"]
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# User Chat Input
if user_query := st.chat_input("Ask a question..."):
    # Append user question
    st.session_state.messages.append({
        "role": "user",
        "username": selected_username,
        "content": user_query
    })
    
    with st.chat_message("user", avatar=profile["avatar"]):
        st.write(user_query)
        
    # Generate bot response
    with st.chat_message("assistant", avatar="⚡"):
        with st.spinner("Searching company documents..."):
            pipeline_query = get_query_pipeline()
            result = pipeline_query.query(question=user_query, username=selected_username, top_k=5)
            
            answer = result["answer"]
            citations = result.get("citations", [])
            latency = result.get("elapsed_ms", 0.0)
            
            st.session_state.latest_latency = latency
            st.session_state.latest_citations = citations
            
            st.write(answer)
            
            # Save message to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })
            
            # Force UI update for sidebar citations
            st.rerun()
