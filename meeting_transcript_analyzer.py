import os
import re
import sys
import json
from typing import List, Dict, Any
from pipeline import VectorDatabase
from llm_client import generate_llm_response

def list_available_documents(db: VectorDatabase) -> Dict[int, Dict[str, str]]:
    """Retrieves all unique documents and their meeting dates from Qdrant."""
    print("Scanning Qdrant collection for meeting transcripts...")
    all_chunks = []
    next_token = None
    while True:
        batch, next_token = db.client.scroll(
            collection_name=db.collection_name,
            limit=100,
            with_payload=True,
            with_vectors=False,
            offset=next_token
        )
        if not batch:
            break
        all_chunks.extend(batch)
        if next_token is None:
            break

    docs = {}
    for chunk in all_chunks:
        payload = chunk.payload
        src = payload.get('source_file', 'Unknown')
        dt = payload.get('date', 'Unknown Date')
        if src not in docs:
            docs[src] = {"date": dt, "chunks": []}
        docs[src]["chunks"].append(chunk)

    sorted_docs = sorted(docs.items(), key=lambda x: x[1]["date"])
    
    doc_map = {}
    print("\nAvailable Meeting Transcripts in Qdrant:")
    for idx, (doc_name, info) in enumerate(sorted_docs, start=1):
        doc_map[idx] = {"name": doc_name, "date": info["date"], "chunks": info["chunks"]}
        print(f"[{idx}] {info['date']} - {doc_name} ({len(info['chunks'])} chunks)")
    
    return doc_map


def run_map_phase(doc_name: str, date: str, chunks: list) -> List[str]:
    """MAP Phase: Summarizes the meeting transcripts in small batches of 5 chunks."""
    BATCH_SIZE = 5
    num_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[MAP PHASE] Summarizing {len(chunks)} chunks in {num_batches} batches...")
    
    batch_summaries = []
    for b in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[b:b + BATCH_SIZE]
        batch_num = (b // BATCH_SIZE) + 1
        
        doc_context = ""
        for c in batch_chunks:
            p = c.payload
            doc_context += f"[Page {p.get('page', '1')}] {p.get('speaker', 'Unknown')}: {p.get('text', '')}\n\n"

        map_prompt = (
            f"You are extracting training performance notes from meeting transcripts for {doc_name} dated {date}.\n"
            f"Extract ONLY details present in the text below. Focus on:\n"
            f"- Governing topics discussed.\n"
            f"- Specific trainee actions, tasks, or confusion (Himaya, Ganesh, Dakshinya).\n"
            f"- Technical definitions, questions asked, or mentorship feedback from Siddharth Saminathan.\n"
            f"If the text is empty or has no content, output: NO_CONTENT\n\n"
            f"Excerpts:\n{doc_context}"
        )
        
        summary = generate_llm_response(
            system_prompt="You are a precise data extractor.",
            user_query=map_prompt,
            fallback_response="NO_CONTENT",
            agent_type="teammates"
        )
        
        if "NO_CONTENT" not in summary.strip():
            batch_summaries.append(summary.strip())
            print(f"  -> Batch {batch_num}/{num_batches} processed.")
        else:
            print(f"  -> Batch {batch_num}/{num_batches} skipped (no relevant content).")
            
    return batch_summaries


def run_reduce_phase(doc_name: str, date: str, summaries: List[str]) -> Dict[str, Any]:
    """REDUCE Phase: Synthesizes document batch summaries into the final 9-field JSON report."""
    print(f"\n[REDUCE PHASE] Synthesizing final JSON report according to SKILL.md...")
    combined_summaries = "\n\n".join(summaries)
    
    reduce_prompt = f"""You are a meeting transcript analyzer. Synthesize the following meeting summaries into a final structured analysis report.

Session Name: {doc_name}
Date: {date}
Meeting Summaries:
{combined_summaries}

YOUR TASK:
Produce a single, valid, parsable JSON object matching this schema. You MUST include all 9 fields. Do not add any intro, explanations, reasoning, or markdown code block wrapping. Output ONLY the raw JSON string.

Schema:
{{
  "governing_thought": "1-sentence core message summarizing the session outcome",
  "pillars": [
    {{
      "title": "Topic/Pillar Title",
      "summary": "Brief summary",
      "evidence": "Verbatim proof or specific citations",
      "score": 8
    }}
  ],
  "scqa": {{
    "situation": "Initial state or baseline context",
    "complication": "Problems, blockers, or gaps that arose",
    "question": "The core question/challenge to address",
    "answer": "Solution or path forward agreed upon"
  }},
  "delta": {{
    "previous_session": "Summary of previous session state",
    "current_session": "Summary of current session state",
    "key_changes": "Key changes observed",
    "trajectory": "Trainee progress vector (e.g. improving, stagnant)"
  }},
  "action_items": [
    {{
      "owner": "Name of trainee or mentor",
      "task": "Specific task",
      "deadline": "Due date if mentioned, otherwise 'Next Session'",
      "binary_verification": "Binary criteria to verify task is complete"
    }}
  ],
  "ten_second_questions": [
    {{
      "question": "Direct question for trainee",
      "good_answer_pattern": "What a correct answer sounds like",
      "bad_answer_pattern": "Red flags or wrong answers"
    }}
  ],
  "key_quotes": [
    {{
      "speaker": "Name of speaker",
      "quote": "Exact verbatim quote from transcripts",
      "timestamp": "Document Name / Page reference",
      "why_it_matters": "Strategic import of quote"
    }}
  ],
  "coaching_notes": {{
    "what_went_well": "Positive observations",
    "what_went_wrong": "Gaps, mistakes, or areas of concern",
    "patterns_to_watch": "Behavioral or technical patterns to watch",
    "tomorrow_focus": "Immediate training focus areas"
  }},
  "scores": {{
    "himaya": {{
      "preparation": 7,
      "conceptual_depth": 7,
      "code_quality": 8,
      "engagement": 8,
      "overall": 7.5,
      "one_line_verdict": "Clear, direct assessment"
    }},
    "ganesh": {{
      "preparation": 7,
      "conceptual_depth": 7,
      "code_quality": 8,
      "engagement": 8,
      "overall": 7.5,
      "one_line_verdict": "Clear, direct assessment"
    }},
    "dakshinya": {{
      "preparation": 7,
      "conceptual_depth": 7,
      "code_quality": 8,
      "engagement": 8,
      "overall": 7.5,
      "one_line_verdict": "Clear, direct assessment"
    }}
  }}
}}"""

    response = generate_llm_response(
        system_prompt="You are a strict JSON generator. Output raw JSON ONLY. No markdown, no preambles.",
        user_query=reduce_prompt,
        fallback_response="{}",
        agent_type="teammates"
    )
    
    cleaned_json = response.strip()
    if cleaned_json.startswith("```"):
        cleaned_json = re.sub(r"^```(?:json)?\n", "", cleaned_json)
        cleaned_json = re.sub(r"\n```$", "", cleaned_json)
    
    try:
        report_data = json.loads(cleaned_json)
        return report_data
    except Exception as e:
        print(f"\n[JSON Parsing Error]: Could not parse JSON response. Error: {e}")
        return {{
            "governing_thought": f"Meeting review for {date}.",
            "error": "Failed to parse JSON report.",
            "raw_response": response
        }}


def print_report_summary(report: Dict[str, Any]):
    """Prints a beautiful summary of the analysis report to the console."""
    print("\n" + "="*80)
    print("📝 MEETING TRANSCRIPT ANALYSIS REPORT")
    print("="*80)
    print(f"💡 Governing Thought:\n   {report.get('governing_thought', 'N/A')}\n")
    
    print("📋 Key Action Items:")
    action_items = report.get("action_items", [])
    if isinstance(action_items, list):
        for item in action_items:
            print(f"  • [{item.get('owner', 'Unknown')}] {item.get('task', 'N/A')} (Verify: {item.get('binary_verification', 'N/A')})")
    else:
        print("  • No action items found.")
        
    print("\n📊 Trainee overall scores:")
    scores = report.get("scores", {})
    if isinstance(scores, dict):
        for trainee, metrics in scores.items():
            if isinstance(metrics, dict):
                print(f"  • {trainee.upper()}: Overall={metrics.get('overall', 'N/A')} | Verdict: {metrics.get('one_line_verdict', 'N/A')}")
    
    print("\n🔬 SCQA Summary:")
    scqa = report.get("scqa", {})
    if isinstance(scqa, dict):
        print(f"  - Situation: {scqa.get('situation', 'N/A')}")
        print(f"  - Complication: {scqa.get('complication', 'N/A')}")
        print(f"  - Question: {scqa.get('question', 'N/A')}")
        print(f"  - Answer: {scqa.get('answer', 'N/A')}")

    print("="*80 + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        
    db = VectorDatabase()
    doc_map = list_available_documents(db)
    
    if not doc_map:
        print("No documents found in Qdrant database. Exiting.")
        return
        
    try:
        choice = input("\nEnter the index of the meeting transcript to analyze (or 'exit' to quit): ").strip()
        if choice.lower() == 'exit':
            return
        
        idx = int(choice)
        if idx not in doc_map:
            print("Invalid choice. Exiting.")
            return
    except ValueError:
        print("Invalid number format. Exiting.")
        return

    selected = doc_map[idx]
    doc_name = selected["name"]
    date = selected["date"]
    chunks = selected["chunks"]
    
    print(f"\nAnalyzing Meeting: {date} - {doc_name}")
    
    summaries = run_map_phase(doc_name, date, chunks)
    
    if not summaries:
        print("No meaningful content extracted during the MAP phase. Analysis aborted.")
        return
        
    report = run_reduce_phase(doc_name, date, summaries)
    print_report_summary(report)
    
    output_filename = "meeting_analysis_report.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Success! Exhaustive JSON analysis report saved to: {output_filename}")


if __name__ == "__main__":
    main()
