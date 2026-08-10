"""
================================================================================
Pre-Chunking Transcript Normalizer & Crosstalk Re-attribution Engine
================================================================================
Fixes data quality problems before vector chunking & indexing:
1. Standardizes speaker identities (SS, HP, Dakshinya, etc.)
2. Re-attributes task assignments & mentor commands spoken through unmuted mics to Siddharth Saminathan.
3. Cleans audio timestamp artifacts & noise.
"""

import re
from typing import List, Tuple

SPEAKER_MAP = {
    "ss": "Siddharth Saminathan",
    "siddharth": "Siddharth Saminathan",
    "siddharth saminathan": "Siddharth Saminathan",
    "hp": "Himaya Perumal",
    "himaya": "Himaya Perumal",
    "himaya perumal": "Himaya Perumal",
    "gk": "Ganesh Krishna",
    "ganesh": "Ganesh Krishna",
    "ganesh krishna": "Ganesh Krishna",
    "dn": "Dakshinya Nachimuthu",
    "dakshinya": "Dakshinya Nachimuthu",
    "dakshinya nachimuthu": "Dakshinya Nachimuthu",
    "iyappan": "Iyappan Sir",
    "iyappan sir": "Iyappan Sir"
}

# Master Mentor Speech Pattern Regex Rules (Siddharth's Identity Predictor)
MENTOR_PATTERNS_REGEX = [
    # 1. First-Person Mentor Imperatives ("I + Command/Demand")
    r"\bi\s+(want|need|told|asked|suggested|recommended|assigned|gave|want\s+you\s+to|want\s+to\s+see|want\s+some\s+results|only\s+wanted\s+you)\b",
    r"\bi\s+(will|'ll)\s+(give|send|tell|assign|ask)\b",
    
    # 2. Direct Commands & Task Instructions to Learners
    r"\b(you\s+first|you\s+should|you\s+have\s+to|study\s+about|read\s+about|go\s+through|work\s+on|look\s+into|think\s+about|check\s+whether)\b",
    r"\b(do\s+one\s+thing|do\s+that|make\s+sure|try\s+to)\b",
    
    # 3. Mentorship Evaluation & Training Oversight
    r"\b(evaluation\s+framework|training\s+progress|how\s+is\s+the\s+training|where\s+you\s+guys\s+are|necessary\s+for\s+me\s+to\s+know)\b",
    r"\b(for\s+me,\s+for\s+the\s+mentor|as\s+a\s+mentor|in\s+our\s+training|what\s+did\s+you\s+do|what\s+have\s+you\s+done)\b",
    
    # 4. Material / Code Transfers & Assignment Language
    r"\b(using\s+your\s+code|use\s+your\s+code|send\s+materials|give\s+the\s+work|give\s+you\s+the\s+work|give\s+you\s+work|assignment\s+for|task\s+for)\b",
    r"\b(whether\s+we\s+are\s+using\s+your\s+code|give\s+you\s+to\s+send)\b",

    # 5. Slide Review & Presentation Corrections (Siddharth's Mentorship Review Patterns)
    r"\b(don't\s+put\s+anything|just\s+leave\s+it|remove\s+it|you\s+know\s+what\s+dynamic\s+means|does\s+your\s+chunking\s+strategy\s+change|chunk\s+the\s+whole\s+document|trade\s+off\s+retrieval|lowest\s+level\s+of\s+the\s+document|highest\s+level\s+chunking|put\s+it\s+here|came\s+up\s+with\s+your\s+own)\b",
    r"\b(why\s+have\s+you\s+again\s+said\s+it|don't\s+repeat\s+the\s+same\s+slide|second\s+slide|third\s+slide|fourth\s+slide|this\s+slide\s+is\s+not\s+needed|key\s+decision\s+slide\s+is\s+not\s+needed)\b",
    r"\b(remove\s+that\s+slide|you\s+don't\s+need\s+it|it's\s+worthless|remove\s+this\s+dynamic|dynamic\s+free\s+cut|what\s+are\s+you\s+doing\s+now|what\s+are\s+you\s+doing\s+at\s+all|include\s+this\s+one\s+small)\b"
]

def is_mentor_speaking_pattern(text: str) -> bool:
    """Predicts whether a speech turn was spoken by Mentor Siddharth Saminathan based on linguistic patterns."""
    text_lower = text.lower()
    
    # EXEMPTION: Teammates reporting tasks received ("You told us", "You asked me", "yesterday, you told me", "I didn't start")
    if re.search(r"\b(you\s+told\s+(us|me)|you\s+asked\s+(us|me)|you\s+gave\s+(us|me)|you\s+said|yesterday,\s*you|i\s+didn't\s+start|so\s+i'm\s+doing)\b", text_lower):
        return False
    if re.search(r"\b(you|yesterday|so)[,\s]+(you\s+)?(asked|told|gave|said|wanted)\b", text_lower):
        return False

    for pattern in MENTOR_PATTERNS_REGEX:
        if re.search(pattern, text_lower):
            return True
    return False

def normalize_speaker_name(name_str: str) -> str:
    """Standardizes speaker name variations and initials into full canonical names."""
    if not name_str:
        return "Unknown Speaker"
    
    cleaned = re.sub(r"\d+\s*minutes?.*$", "", name_str, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\d+:\d+.*$", "", cleaned).strip()
    
    q = cleaned.lower()
    for key, canonical in SPEAKER_MAP.items():
        if key in q:
            return canonical
            
    return "Unknown Speaker"


def clean_audio_artifacts(text: str) -> str:
    """Cleans mic noise, cross-talk artifacts, and transcription status noise."""
    if not text:
        return ""
    
    text = re.sub(r"\b\d+\s*minutes?\s*\d*\s*seconds?\d*:?\d*\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", "", text)
    text = re.sub(r"\[(laughter|unmute|cross-talk|inaudible|background noise|crosstalk)\]", "", text, flags=re.IGNORECASE)
    
    # Audio transcription phonetic typos & mishearings
    text = re.sub(r"\bdragon\s+project\b", "RAG project", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdragon\s+(system|model|architecture|experiment|workflow|pipeline|vector|chunk)\b", r"RAG \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\brack\s+project\b", "RAG project", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEPL\b", "ETL (Extraction, Transform, Load)", text)
    text = re.sub(r"\bquadrant\b", "Qdrant", text, flags=re.IGNORECASE)
    text = re.sub(r"\bq\s*drant\b", "Qdrant", text, flags=re.IGNORECASE)
    text = re.sub(r"\bopen by excel\b", "openpyxl", text, flags=re.IGNORECASE)
    text = re.sub(r"\bopen by ex\b", "openpyxl", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfast\s*mcp\b|\bfast\s*mct\b", "FastMCP", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMCT\s+(layer|server|protocol|directory|architecture|retrieval)\b", r"MCP \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMCTs\b", "MCPs", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMCT\b", "MCP", text)
    text = re.sub(r"\bstream\s*lit\b|\bstreamlet\b", "Streamlit", text, flags=re.IGNORECASE)
    text = re.sub(r"\bgrok\b", "Groq", text, flags=re.IGNORECASE)
    
    text = re.sub(r"\s+", " ", text).strip()
    return text


def reattribute_crosstalk_turn(speaker: str, text: str) -> Tuple[str, str]:
    """
    Re-attributes turns where a mentor speaks through an unmuted mic.
    If text contains explicit mentor assignment commands, re-attributes speaker payload strictly to 'Siddharth Saminathan'.
    """
    text_clean = clean_audio_artifacts(text)
    
    # 0. TEAMMATE WORKFLOW REPORT PATTERN: Himaya's Zomato / ETL workflow updates
    if re.search(r"\b(zomato\s+orders|this\s+is\s+the\s+project\s+workflow\s+that\s+i\s+have\s+done)\b", text_clean, re.IGNORECASE):
        return "Himaya Perumal", text_clean

    # 0b. DAKSHINYA WORKFLOW REPORT PATTERN: Dakshinya's track / skills updates
    if re.search(r"\b(you\s+told\s+us\s+to\s+go\s+through|doing\s+that\s+skills|didn't\s+start)\b", text_clean, re.IGNORECASE):
        return "Dakshinya Nachimuthu", text_clean

    # 0c. GANESH WORKFLOW REPORT PATTERN: Ganesh's NLM & Excel agent updates
    if re.search(r"\b(asked\s+me\s+to\s+integrate\s+the\s+nlm|integrate\s+the\s+nlm|excel\s+agent|schema\s+map|openpyxl)\b", text_clean, re.IGNORECASE):
        return "Ganesh Krishna", text_clean
        
    # 1. PRIORITY MENTOR PATTERN PREDICTOR: If text matches mentor speech patterns, Siddharth is speaking!
    if is_mentor_speaking_pattern(text_clean):
        return "Siddharth Saminathan", text_clean
        
    # 2. Check embedded speaker prefixes like "Siddharth Saminathan: OK, think..."
    embedded = re.match(r"^(Siddharth Saminathan|Siddharth|Himaya Perumal|Himaya|Ganesh Krishna|Ganesh|Dakshinya Nachimuthu|Dakshinya):\s*(.*)", text_clean, re.IGNORECASE)
    if embedded:
        real_spk = normalize_speaker_name(embedded.group(1))
        real_txt = embedded.group(2)
        if real_spk != "Unknown Speaker":
            # Re-check embedded text for mentor commands
            if is_mentor_speaking_pattern(real_txt):
                return "Siddharth Saminathan", real_txt
            return real_spk, real_txt
            
    norm_spk = normalize_speaker_name(speaker)
    return norm_spk, text_clean


def parse_and_normalize_turns(raw_transcript_text: str) -> List[Tuple[str, str]]:
    """
    Parses raw transcript text into normalized (speaker, turn_text) tuples.
    Detects and re-attributes embedded crosstalk (e.g., when Siddharth speaks into Dakshinya's unmuted mic).
    """
    lines = raw_transcript_text.split("\n")
    normalized_turns: List[Tuple[str, str]] = []
    
    current_speaker = "Unknown Speaker"
    current_lines = []
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        if "started transcription" in line_clean.lower() or "stopped transcription" in line_clean.lower():
            continue
            
        # Embedded speaker prefix check
        embedded_match = re.match(r"^(Siddharth Saminathan|Himaya Perumal|Ganesh Krishna|Dakshinya Nachimuthu|Siddharth|Himaya|Ganesh|Dakshinya):\s*(.*)", line_clean, re.IGNORECASE)
        if embedded_match:
            if current_lines:
                spk, txt = reattribute_crosstalk_turn(current_speaker, " ".join(current_lines))
                if txt:
                    normalized_turns.append((spk, txt))
            current_speaker = normalize_speaker_name(embedded_match.group(1))
            current_lines = [embedded_match.group(2)]
            continue
            
        # Speaker turn header line check
        norm_name = normalize_speaker_name(line_clean)
        if norm_name != "Unknown Speaker" and ("minutes" in line_clean.lower() or ":" in line_clean or len(line_clean.split()) <= 4):
            if current_lines:
                spk, txt = reattribute_crosstalk_turn(current_speaker, " ".join(current_lines))
                if txt:
                    normalized_turns.append((spk, txt))
            current_speaker = norm_name
            current_lines = []
            continue
            
        current_lines.append(line_clean)
        
    if current_lines:
        spk, txt = reattribute_crosstalk_turn(current_speaker, " ".join(current_lines))
        if txt:
            normalized_turns.append((spk, txt))
            
    return [(spk, txt) for spk, txt in normalized_turns if spk != "Unknown Speaker" and txt]


def build_normalized_transcript_text(raw_transcript_text: str) -> str:
    """
    Reconstructs clean, normalized transcript text ready for chunking & vector indexing.
    """
    turns = parse_and_normalize_turns(raw_transcript_text)
    output_lines = []
    for spk, txt in turns:
        output_lines.append(f"{spk} 0:00")
        output_lines.append(txt)
        output_lines.append("")
    return "\n".join(output_lines)
