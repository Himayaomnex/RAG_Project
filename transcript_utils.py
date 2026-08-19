"""
================================================================================
transcript_utils.py — Shared transcript-parsing helpers
================================================================================
Extracted from manager_agent.py and mentor_agent.py, where the same
speaker-demultiplexing regex, XML-tag stripping, and mentee-name resolution
logic was copy-pasted 3-4 times per file. A bug fix here now propagates to
both agents instead of needing to be applied in every copy.
"""

import re
from transcript_normalizer import clean_audio_artifacts

_SPEAKER_TURN_PATTERN = re.compile(
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):\s*(.*?)(?=\n[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+:|$)",
    re.DOTALL,
)


def demux_speaker_turns(raw_txt: str):
    """
    Splits a raw transcript chunk that may contain multiple inline speaker
    turns (e.g. "Ganesh: ...\\nDakshinya: ...") into a list of
    (speaker, text) tuples.

    Returns [] if no inline turns are found — callers should fall back to
    the chunk's own `speaker` payload field in that case, exactly like the
    original `if not matches:` branches in both agents did.
    """
    matches = _SPEAKER_TURN_PATTERN.findall(raw_txt)
    return [(spk.strip(), txt.strip()) for spk, txt in matches]


def clean_chunk_text(raw_txt: str, max_len: int = None) -> str:
    """
    Runs clean_audio_artifacts() + strips the <document ...>...</document>
    XML wrapper tags injected by the P4 map-reduce pipeline.

    Optionally truncates to max_len chars for bullet-point readability,
    closing the sentence cleanly (strips a trailing "..." remnant first so
    you don't get "text....") rather than cutting mid-word.
    """
    txt = clean_audio_artifacts(raw_txt)
    txt = re.sub(r"<document[^>]*>", "", txt, flags=re.DOTALL)
    txt = re.sub(r"</document>", "", txt, flags=re.DOTALL)
    txt = txt.strip()

    if max_len and len(txt) > max_len:
        txt = txt[:max_len].rstrip(".").rstrip() + "..."
    elif txt.endswith("..."):
        txt = txt.rstrip(".").rstrip() + "."

    return txt


def resolve_primary_mentee(spk: str, mentee_names_map: dict) -> str:
    """
    Extracts the first individual mentee name from a (possibly comma-joined)
    speaker field, e.g. "Himaya, Dakshinya" -> "Himaya Perumal".

    Returns the canonical full name from mentee_names_map if a known mentee
    is found, otherwise returns the original first name in the field
    unchanged (same fallback behavior as the original `_primary_mentee`).
    """
    for part in spk.split(","):
        part_lower = part.strip().lower()
        for key, full in mentee_names_map.items():
            if key in part_lower:
                return full
    return spk.split(",")[0].strip()


def iter_chunk_turns(payload: dict, mentee_names_map: dict = None):
    """
    Given a single retrieved chunk's payload, yields one dict per speaker
    turn found in it:
        {"spk": str, "dt": str, "doc": str, "pg": str, "txt": str, "cit": str}

    Handles both the multi-speaker inline case (via demux_speaker_turns)
    and the single-speaker payload case, so callers no longer need to
    branch on `if not matches:` themselves. If mentee_names_map is given,
    `spk` is resolved to its canonical mentee name where applicable.
    """
    dt  = payload.get("date", "Unknown Date")
    doc = payload.get("source_file", "Transcript.docx")
    pg  = payload.get("page", "1")
    raw_txt = payload.get("text", "").strip()

    turns = demux_speaker_turns(raw_txt)
    if not turns:
        spk = payload.get("speaker", "Unknown")
        turns = [(spk, raw_txt)]

    for spk, turn_txt in turns:
        txt = clean_chunk_text(turn_txt)
        if not txt:
            continue
        if mentee_names_map:
            spk = resolve_primary_mentee(spk, mentee_names_map)
        cit = f"[{dt} | {doc} | Speaker: {spk} | Page {pg}]"
        yield {"spk": spk, "dt": dt, "doc": doc, "pg": pg, "txt": txt, "cit": cit}
