"""
================================================================================
Pre-Chunking Transcript Normalizer & Crosstalk Re-attribution Engine (RAG_COMBINED)
================================================================================
Fixes data quality issues before vector chunking & indexing across 4 operations:
1. UNKNOWN: Re-attributes unlabelled/unknown speaker turns to Siddharth Saminathan based on mentor linguistic patterns (assigning work, tasks) and audio artifact phonetic cleanup ('dragon' -> 'RAG', 'quadrant' -> 'Qdrant').
2. ECHO: Detects and discards duplicate transcript turns.
3. SPLIT: Splits merged lines where two speaker turns were joined into one.
4. DISCARD: Filters out garbled speech, near-empty classes, and uninformative noise phrases ("joined the meeting").
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

MENTOR_PATTERNS_REGEX = [
    r"\bi\s+(want|need|told|asked|suggested|recommended|assigned|gave|want\s+you\s+to|want\s+to\s+see|want\s+some\s+results|only\s+wanted\s+you)\b",
    r"\bi\s+(will|'ll)\s+(give|send|tell|assign|ask)\b",
    r"\b(you\s+first|you\s+should|you\s+have\s+to|study\s+about|read\s+about|go\s+through|work\s+on|look\s+into|think\s+about|check\s+whether)\b",
    r"\b(do\s+one\s+thing|do\s+that|make\s+sure|try\s+to)\b",
    r"\b(evaluation\s+framework|training\s+progress|how\s+is\s+the\s+training|where\s+you\s+guys\s+are|necessary\s+for\s+me\s+to\s+know)\b",
    r"\b(for\s+me,\s+for\s+the\s+mentor|as\s+a\s+mentor|in\s+our\s+training|what\s+did\s+you\s+do|what\s+have\s+you\s+done)\b",
    r"\b(using\s+your\s+code|use\s+your\s+code|send\s+materials|give\s+the\s+work|give\s+you\s+the\s+work|give\s+you\s+work|assignment\s+for|task\s+for)\b",
    r"\b(don't\s+put\s+anything|just\s+leave\s+it|remove\s+it|you\s+know\s+what\s+dynamic\s+means|does\s+your\s+chunking\s+strategy\s+change|chunk\s+the\s+whole\s+document)\b"
]

def is_mentor_speaking_pattern(text: str) -> bool:
    """Predicts whether a speech turn was spoken by Mentor Siddharth Saminathan based on linguistic patterns."""
    text_lower = text.lower()
    
    if re.search(r"\b(you\s+told\s+(us|me)|you\s+asked\s+(us|me)|you\s+gave\s+(us|me)|you\s+said|yesterday,\s*you|i\s+didn't\s+start|so\s+i'm\s+doing)\b", text_lower):
        return False
    if re.search(r"\b(you|yesterday|so)[,\s]+(you\s+)?(asked|told|gave|said|wanted)\b", text_lower):
        return False

    for pattern in MENTOR_PATTERNS_REGEX:
        if re.search(pattern, text_lower):
            return True
    return False

def normalize_speaker_name(name_str: str) -> str:
    """Standardizes speaker name variations and initials into full canonical names (Entity Normalization)."""
    if not name_str:
        return "Unknown Speaker"
    
    cleaned = re.sub(r"\d+\s*minutes?.*$", "", name_str, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\d+:\d+.*$", "", cleaned).strip()
    
    q = cleaned.lower()
    for key, canonical in SPEAKER_MAP.items():
        if key in q:
            return canonical
            
    return name_str.strip() or "Unknown Speaker"


def clean_audio_artifacts(text: str) -> str:
    """Cleans mic noise, crosstalk artifacts, and transcription phonetic mishearings."""
    if not text:
        return ""
    
    text = re.sub(r"\b\d+\s*minutes?\s*\d*\s*seconds?\d*:?\d*\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", "", text)
    text = re.sub(r"\[(laughter|unmute|cross-talk|inaudible|background noise|crosstalk)\]", "", text, flags=re.IGNORECASE)
    
    # Audio transcription phonetic typos & mishearings
    text = re.sub(r"\bdragon\s+project\b", "RAG project", text, flags=re.IGNORECASE)
    text = re.sub(r"\brack\s+project\b|\brack\b", "RAG", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAqua\s+Pro\s+A\b|\bAqua\s+Pro\b", "RAG Pipeline Architecture", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLandGraph\b|\bland\s+graph\b", "LangGraph", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLM\b", "LLM", text)
    text = re.sub(r"\bLMs\b", "LLMs", text)
    text = re.sub(r"\bEPL\b", "ETL (Extraction, Transform, Load)", text)
    text = re.sub(r"\bquadrant\b", "Qdrant", text, flags=re.IGNORECASE)
    text = re.sub(r"\bq\s*drant\b", "Qdrant", text, flags=re.IGNORECASE)
    text = re.sub(r"\bopen by excel\b", "openpyxl", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfast\s*mcp\b|\bfast\s*mct\b", "FastMCP", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMCT\b", "MCP", text)
    text = re.sub(r"\bstream\s*lit\b|\bstreamlet\b", "Streamlit", text, flags=re.IGNORECASE)
    text = re.sub(r"\bgrok\b", "Groq", text, flags=re.IGNORECASE)
    
    # Strip embedded speaker labels inside text body to prevent concatenated speaker leakage
    text = re.sub(r"\b(Siddharth Saminathan|Siddharth|Himaya Perumal|Himaya|Ganesh Krishna|Ganesh|Dakshinya Nachimuthu|Dakshinya):\s*", " ", text, flags=re.IGNORECASE)
    
    text = re.sub(r"\s+", " ", text).strip()
    return text




def reattribute_crosstalk_turn(speaker: str, text: str) -> Tuple[str, str]:
    """
    Pre-chunking crosstalk re-attribution engine:
    If a turn contains explicit mentor commands spoken via an unmuted teammate mic, re-attributes the turn payload to Siddharth Saminathan.
    """
    text_clean = clean_audio_artifacts(text)
    
    if re.search(r"\b(zomato\s+orders|this\s+is\s+the\s+project\s+workflow\s+that\s+i\s+have\s+done)\b", text_clean, re.IGNORECASE):
        return "Himaya Perumal", text_clean

    if re.search(r"\b(you\s+told\s+us\s+to\s+go\s+through|doing\s+that\s+skills|didn't\s+start)\b", text_clean, re.IGNORECASE):
        return "Dakshinya Nachimuthu", text_clean

    if re.search(r"\b(asked\s+me\s+to\s+integrate\s+the\s+nlm|integrate\s+the\s+nlm|excel\s+agent|schema\s+map|openpyxl)\b", text_clean, re.IGNORECASE):
        return "Ganesh Krishna", text_clean
        
    if is_mentor_speaking_pattern(text_clean):
        return "Siddharth Saminathan", text_clean
        
    embedded = re.match(r"^(Siddharth Saminathan|Siddharth|Himaya Perumal|Himaya|Ganesh Krishna|Ganesh|Dakshinya Nachimuthu|Dakshinya):\s*(.*)", text_clean, re.IGNORECASE)
    if embedded:
        real_spk = normalize_speaker_name(embedded.group(1))
        real_txt = embedded.group(2)
        if real_spk != "Unknown Speaker":
            if is_mentor_speaking_pattern(real_txt):
                return "Siddharth Saminathan", real_txt
            return real_spk, real_txt
            
    norm_spk = normalize_speaker_name(speaker)
    return norm_spk, text_clean


# ------------------------------------------------------------------------------
# Explicit 4-Rule Normalization Handlers
# ------------------------------------------------------------------------------

def rule_unknown_resolution(speaker: str, text: str) -> Tuple[str, str]:
    """RULE 1 — UNKNOWN: Re-attributes unlabelled/unknown speaker turns via mentor linguistic patterns & phonetic cleanup."""
    return reattribute_crosstalk_turn(speaker, text)


def rule_echo_deduplication(turns: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """RULE 2 — ECHO: Detects and discards duplicate transcript turns."""
    deduped = []
    seen = set()
    for spk, txt in turns:
        key = (spk.lower(), txt.strip().lower())
        if key not in seen:
            seen.add(key)
            deduped.append((spk, txt))
    return deduped


def rule_split_turns(speaker: str, text: str) -> List[Tuple[str, str]]:
    """RULE 3 — SPLIT: Splits merged lines where two speaker turns were joined into one."""
    matches = list(re.finditer(r"(Siddharth Saminathan|Himaya Perumal|Ganesh Krishna|Dakshinya Nachimuthu|SS|HP|GK|DN):\s*", text, re.IGNORECASE))
    if len(matches) > 1:
        splits = []
        for i in range(len(matches)):
            spk_name = normalize_speaker_name(matches[i].group(1))
            start_idx = matches[i].end()
            end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
            txt_segment = text[start_idx:end_idx].strip()
            if txt_segment:
                splits.append((spk_name, txt_segment))
        return splits
    return [(normalize_speaker_name(speaker), text)]


def rule_discard_noise(speaker: str, text: str) -> bool:
    """RULE 4 — DISCARD: Filters out garbled speech, near-empty classes, and uninformative noise lines."""
    if not text or len(text.strip()) < 4:
        return True
    if re.search(r"\b(joined the meeting|left the meeting|muted|unmuted|screen sharing started)\b", text, re.IGNORECASE):
        return True
    return False

