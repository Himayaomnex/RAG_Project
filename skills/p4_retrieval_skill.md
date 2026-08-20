---
name: p4-transcript-retrieval
description: "Use for executing Pipeline 4 (P4 Full Corpus Map-Reduce) dense retrieval, cross-encoder reranking, speaker normalization, and XML packaging across meeting transcripts."
---

# P4 Transcript Retrieval — Operational Sub-Skill Specification

## Overview
Shared evidence extraction engine for all upstream agents. Ingests, normalizes, retrieves, and packages meeting dialogue chunks into auditable XML context blocks.

## The Iron Law
```
NO CONTEXT INJECTION WITHOUT NORMALIZED SPEAKER ATTRIBUTION AND DENSE RETRIEVAL PROOF
```

## 4-Stage Execution Protocol

1. **Dense Semantic Retrieval**: Query Qdrant vector store (`teams_dense_collection`) using MiniLM-L6-v2 embeddings to fetch candidate dialogue turns across the full temporal scope.
2. **Cross-Encoder Reranking**: Score retrieved candidates against user query semantics using cross-encoder weights to maximize signal-to-noise ratio.
3. **Speaker Normalization & Crosstalk Resolution**: Clean audio transcription artifacts and resolve mic-bleed turns so words are strictly attributed to the true speaker.
4. **Structured XML Context Packaging**: Wrap verified turns into structured XML blocks:
   ```xml
   <transcript_evidence>
     <turn date="Date" doc="File" page="Page" speaker="Speaker">Exact text</turn>
   </transcript_evidence>
   ```

## Invariants
- Never fabricate timestamps, dates, or page numbers.
- Never truncate middle turns without explicit boundary markers.
