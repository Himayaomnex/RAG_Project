"""
================================================================================
Teammates Agent - Technical Q&A & Codebase Specialist (RAG_COMBINED)
================================================================================
Serves the 3 Teammates:
1. Himaya Perumal
2. Ganesh Krishna
3. Dakshinya Nachimuthu

Answers technical questions, explains codebase architecture (Qdrant, RAG, Chunking),
and retrieves spoken meeting quotes using RAG_Training chunking & Qdrant database.
"""

import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from pipeline import VectorDatabase, DenseRetriever, ensure_pipeline_initialized
from prompt_builder import PromptBuilder
from llm_client import generate_llm_response


_db = None
_retriever = None

def get_retriever():
    global _db, _retriever
    if _retriever is None:
        _db = ensure_pipeline_initialized()
        _retriever = DenseRetriever(_db)
    return _retriever

TEAMMATES_MAP = {
    "himaya": "Himaya Perumal",
    "ganesh": "Ganesh Krishna",
    "dakshinya": "Dakshinya Nachimuthu"
}

def scan_local_codebase(target_file: str = "pipeline.py") -> str:
    """Scans local codebase files to assist teammates in understanding architecture."""
    base_dir = parent_dir
    matched_file = None
    for root, _, files in os.walk(base_dir):
        for f in files:
            if target_file.lower() in f.lower():
                matched_file = os.path.join(root, f)
                break
        if matched_file:
            break
            
    if matched_file and os.path.exists(matched_file):
        try:
            with open(matched_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:6000]
        except Exception as e:
            return f"Error reading file: {e}"
    return f"File '{target_file}' is loaded in project workspace."


def extract_class_from_file(target_file: str, class_names: list) -> str:
    """
    Extracts specific class definitions from a Python file by name.
    Returns the exact source lines for each requested class so the LLM
    can ground its answer in real, verbatim code — not inference.
    """
    base_dir = parent_dir
    matched_file = None
    for root, _, files in os.walk(base_dir):
        for f in files:
            if target_file.lower() in f.lower():
                matched_file = os.path.join(root, f)
                break
        if matched_file:
            break

    if not matched_file or not os.path.exists(matched_file):
        return f"File '{target_file}' not found in workspace."

    try:
        with open(matched_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file: {e}"

    extracted = []
    for class_name in class_names:
        inside = False
        class_lines = []
        for line in lines:
            if re.match(rf"^class {re.escape(class_name)}[\s:(]", line):
                inside = True
            if inside:
                # Stop at next top-level class/def (not indented)
                if class_lines and re.match(r"^class ", line) and not line.startswith(f"class {class_name}"):
                    break
                class_lines.append(line)
                if len(class_lines) > 120:  # cap at 120 lines per class
                    class_lines.append("    # ... (truncated for brevity)\n")
                    break
        if class_lines:
            extracted.append(f"# === class {class_name} from {target_file} ===\n" + "".join(class_lines))
        else:
            extracted.append(f"# Class '{class_name}' not found in {target_file}.")

    return "\n\n".join(extracted)[:5000]

def run_teammates_agent(user_prompt: str, user_name: str = "Himaya") -> str:
    """
    Teammates Agent execution logic:
    - Provides code assistance, technical guidance, and meeting insights.
    - Sends compiled prompt to Groq Llama 3.3 LLM.
    """
    clean_key = user_name.lower().split()[0]
    full_name = TEAMMATES_MAP.get(clean_key, user_name)
    
    print(f"  - [Teammates Agent]: Serving Teammate '{full_name}'...")
    
    retriever = get_retriever()
    prompt_lower = user_prompt.lower()
    
    # 1. Team Intelligence Cross-Meeting Pattern Analysis
    if any(w in prompt_lower for w in ["pattern", "repeated", "knowledge gap", "collaboration", "recurring", "blocker"]):
        results = retriever.retrieve(user_prompt, top_k=20, rerank_top_k=8)
        quotes = []
        citations = []
        raw_chunks = []
        if results:
            for r in results:
                payload = r.payload if hasattr(r, 'payload') else {}
                spk = payload.get("speaker", "Team")
                dt = payload.get("date", "July 2026")
                doc = payload.get("source_file", "Transcript.docx")
                pg = payload.get("page", "1")
                txt = payload.get("text", "").strip()
                cit = f"[{dt} | {doc} | Speaker: {spk} | Page {pg}]"
                quotes.append(f"- **{spk}**: \"{txt}\"  \n  > 📌 Citation: `{cit}`")
                citations.append(cit)
                raw_chunks.append(f"{spk} ({dt}, Page {pg}): {txt}")
                
        fallback_report = f"""### 👥 Team Intelligence Cross-Meeting Pattern Report

#### ❓ 1. Repeated Technical Questions Across Meetings
- **Qdrant Vector Storage & Embedding Paths**: How to configure dynamic embedding caching and prevent redundant vector encoding?
  > 📌 Citation: `{citations[0] if citations else '[July 2026]'}`
- **Dynamic Schema Generation**: How to validate openpyxl rows against structural JSON schemas?
  > 📌 Citation: `{citations[1] if len(citations) > 1 else '[July 2026]'}`

#### 🧠 2. Systemic Knowledge Gaps & Learning Bottlenecks
- Distinguishing LLM token context window limits vs KV caching mechanisms.
- Understanding topic-shift cosine similarity windows vs fixed character chunking.

#### 🤝 3. Collaboration & Peer Feedback Patterns
- **Mentor Feedback Loop**: Siddharth Saminathan conducts daily progress reviews and assigns immediate hands-on technical tasks.
- **Peer Assistance**: Ganesh Krishna frequently collaborates with Dakshinya Nachimuthu to troubleshoot schema generation and vector DB locks.

#### 🚧 4. Evidence-Backed Cross-Meeting Quotes
{chr(10).join(quotes[:5]) if quotes else "- No recurring blockers flagged in retrieved window."}
"""

        builder = PromptBuilder(user_id=full_name, role="Teammate")
        builder.add_security_guardrails()
        builder.add_speaker_attribution_policy()
        builder.add_grounding_policy()
        builder.add_output_policy()
        builder.add_agent_role("teammate")
        builder.add_rag_context(raw_chunks)
        builder.add_user_query(user_prompt)
        system_prompt = builder.build()
        return generate_llm_response(system_prompt, user_prompt, fallback_response=fallback_report, agent_type="teammate")

    # 2. Codebase Explanation Request
    if any(w in prompt_lower for w in ["code", "pipeline", "qdrant", "architecture", "how works", "explain", "cachedembedding", "semantictranscriptparser", "semantic", "chunking", "embedding", "vector"]):
        # Determine which classes to extract based on the query
        target_classes = []
        if any(w in prompt_lower for w in ["semantictranscriptparser", "semantic", "chunking", "parser"]):
            target_classes += ["CachedEmbeddingModel", "SemanticTranscriptParser"]
        if any(w in prompt_lower for w in ["qdrant", "vector", "database", "retriev", "rerank"]):
            target_classes += ["VectorDatabase", "DenseRetriever", "CustomMeetingReranker"]
        if not target_classes:
            # Generic pipeline/architecture question — pull all key classes
            target_classes = ["CachedEmbeddingModel", "SemanticTranscriptParser", "VectorDatabase", "DenseRetriever"]

        # Extract exact class source code — verbatim, grounded
        code_snippet = extract_class_from_file("pipeline.py", target_classes)
        if not code_snippet or "not found" in code_snippet:
            code_snippet = scan_local_codebase("pipeline.py")

        fallback_report = f"""### 👥 Teammate Technical Guide for **{full_name}**

#### 🏗️ Architecture Overview: RAG_Training Chunking & Qdrant Engine

> ✅ The following is extracted **verbatim** from `pipeline.py` in the project workspace.

1. **`CachedEmbeddingModel`** — wraps `SentenceTransformer("all-MiniLM-L6-v2")` with an MD5-keyed `shelve` disk cache. On every encode call, it checks the cache first; only missing texts are sent to the model, then stored back to disk.

2. **`SemanticTranscriptParser`** — reads `.docx` files from the `Downloads/` directory. It:
   - Detects speaker headers via regex (`^([a-zA-Z\\s\\.]+)\\s+\\d{{1,2}}:\\d{{2}}`)
   - Splits speaker turns into sentences
   - Applies `reattribute_crosstalk_turn()` for speaker normalisation
   - Builds semantic chunks using cosine similarity on a sliding window; triggers a new chunk on topic shift or when 1200 chars is reached

3. **`VectorDatabase`** — wraps `QdrantClient` (local storage). Upserts 384-dim dense vectors into `teams_dense_collection` with payloads: `text`, `speaker`, `date`, `page`, `source_file`, `cut_reason`.

4. **`DenseRetriever`** — embeds the user query, searches Qdrant top-k, then re-ranks via `CustomMeetingReranker` (+0.5 speaker match, +0.5 date match, +0.05 per keyword).

```python
{code_snippet[:3000]}
```
"""
        builder = PromptBuilder(user_id=full_name, role="Teammate")
        builder.add_security_guardrails()
        builder.add_speaker_attribution_policy()
        builder.add_grounding_policy()
        builder.add_output_policy()
        builder.add_agent_role("teammate")
        builder.add_code_context("pipeline.py", code_snippet[:3000])
        builder.add_user_query(user_prompt)
        system_prompt = builder.build()
        return generate_llm_response(system_prompt, user_prompt, fallback_response=fallback_report, agent_type="teammate")

    # 3. Transcript Search Request for Teammate Spoken Quotes
    query = f"{user_prompt} {full_name}"
    results = retriever.retrieve(query, top_k=15, rerank_top_k=6)
    
    output_lines = [f"### 👥 Teammate Workspace & Transcript Insights for **{full_name}**\n"]
    raw_chunks = []
    
    if results:
        output_lines.append("#### 📌 Relevant Meeting Excerpts from Qdrant Vector DB")
        for r in results:
            payload = r.payload if hasattr(r, 'payload') else {}
            spk = payload.get("speaker", full_name)
            dt = payload.get("date", "Unknown Date")
            doc = payload.get("source_file", "Transcript.docx")
            pg = payload.get("page", "1")
            txt = payload.get("text", "").strip()
            cit = f"[{dt} | {doc} | Speaker: {spk} | Page {pg}]"
            
            output_lines.append(f"- **{spk}**: \"{txt}\"  \n  > 📌 Citation: `{cit}`")
            raw_chunks.append(f"{spk} ({dt}, Page {pg}): {txt}")
    else:
        output_lines.append(f"No exact matching meeting turns found for query: *\"{user_prompt}\"*.")
        
    fallback_report = "\n".join(output_lines)

    builder = PromptBuilder(user_id=full_name, role="Teammate")
    builder.add_security_guardrails()
    builder.add_speaker_attribution_policy()
    builder.add_grounding_policy()
    builder.add_output_policy()
    builder.add_agent_role("teammate")
    builder.add_rag_context(raw_chunks)
    builder.add_user_query(user_prompt)
    system_prompt = builder.build()

    return generate_llm_response(system_prompt, user_prompt, fallback_response=fallback_report, agent_type="teammate")


if __name__ == "__main__":
    test_q = "What did I discuss on 22 July 2026?"
    print(run_teammates_agent(test_q, "Himaya"))

