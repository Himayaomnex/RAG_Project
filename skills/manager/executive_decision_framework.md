# Executive Decision Framework & MECE Guidelines (Manager Agent)

Supporting reference guide for `manager-executive-intelligence` skill.

## 1. MECE Accomplishment Mapping

To maintain balanced, mutually exclusive, and collectively exhaustive tracking of the AI/ML engineering team, each trainee is evaluated across 3 core capability domains:

### Himaya Perumal
1. **Multi-Agent RAG System Architecture**: Full orchestration of specialized agent nodes, dynamic intent routing, and stateful FastAPI endpoints.
2. **Embedding Caching (Latency & Cost Optimization)**: Chunk-level MD5 cache layer eliminating redundant vector model computation.
3. **Custom Semantic Chunking Strategy**: Sentence-boundary semantic chunking with rolling token overlap preserving contextual meaning.

### Ganesh Krishna
1. **Excel Extraction & Multi-File Editing Pipeline**: Schema-aware cell parsing and multi-sheet editing with transactional rollback.
2. **DeepSeek V4 Integration**: Tiered routing between DeepSeek V4 Flash (low-latency edits) and DeepSeek V4 Pro (complex merges).
3. **Excel Diff Rendering & Verification**: Visual cell-by-cell delta inspection verifying changes against original workbooks.

### Dakshinya Nachimuthu
1. **Feature Engineering & Baseline ML Models**: Tabular data preparation, TF-IDF vectorization, Logistic Regression, and XGBoost training.
2. **Vector Search & Reranker Architecture**: Qdrant dense retrieval integration paired with cross-encoder semantic reranking.
3. **ML Model Experiments & Context Engineering**: Token window budgeting, prompt compression, and batch optimization for LLM inference.

---

## 2. SCQA Blocker Diagnostic Protocol

When diagnosing impediments, format evidence strictly as:
* **Situation (S)**: The assigned task and technical context.
* **Complication (C)**: The specific bottleneck encountered (e.g. rate limit 429, memory OOM, context overflow).
* **Question (Q)**: Impact on development schedule or accuracy.
* **Answer (A)**: Concrete mitigation agreed during the meeting.

---

## 3. Verbatim Citation Syntax

Every table cell containing evidence must follow this standard format:
`📜 **Verbatim Proof:** [Date — Document — Page — Speaker]: "..."`
