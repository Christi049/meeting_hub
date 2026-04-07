import json
import os
import re
from collections import OrderedDict

from dotenv import load_dotenv

# Load .env from the backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

# Try to import LangChain components, but provide fallbacks
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Initialize OpenRouter via LangChain (OpenAI-compatible API)
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = None
    if api_key:
        llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )

    # TEXT SPLITTER — breaks long transcripts into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=12000,
        chunk_overlap=500,
        separators=["\n\n", "\n", ". ", " "],
    )

except ImportError:
    print("Warning: LangChain dependencies not available, using fallback mode")
    llm = None
    text_splitter = None

# ══════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════

CHUNK_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert meeting transcript analyst. Analyze the provided transcript chunk and return a JSON object with these fields:

- "unique_speakers": list of unique human speaker names (deduplicate variations like "Doug A." and "Doug Alcorn" into one canonical name)
- "speaker_count": integer count of unique speakers in this chunk
- "word_count": count of meaningful spoken words only (exclude timestamps, metadata, formatting)
- "meeting_date": date in YYYY-MM-DD format if found, otherwise "Unknown"
- "meeting_title": the meeting topic or title if identifiable, otherwise "Unknown"
- "abstractive_summary": 2-3 sentence summary of the key themes discussed in this chunk
- "decisions": list of specific team decisions made in this chunk
- "action_items": list of objects with fields:
  - "owner": person responsible
  - "task": what they need to do
  - "due_by": deadline/date, or "Unknown"

Return ONLY valid JSON, no markdown formatting or code fences."""),
    ("human", "Analyze this transcript chunk from the file '{filename}':\n\n{text}"),
])

FINAL_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert meeting analyst. You will receive multiple partial summaries from chunks of the same meeting transcript. 
Synthesize them into ONE final coherent JSON result with these fields:

- "abstractive_summary": A comprehensive 3-5 sentence summary covering ALL key themes from the entire meeting
- "decisions": A deduplicated list of all decisions from across the meeting
- "action_items": A deduplicated list of action item objects with fields: "owner", "task", "due_by"

Return ONLY valid JSON, no markdown formatting or code fences."""),
    ("human", "Here are the partial summaries from different chunks of the same meeting:\n\n{chunk_summaries}"),
])

SPEAKER_FALLBACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You extract speaker names from meeting transcripts.
Return ONLY valid JSON with this schema:
{
  "unique_speakers": ["Name 1", "Name 2"]
}

Rules:
- Include only human speaker names/identifiers present in the transcript.
- Exclude room names, titles, dates, headings, and organizations.
- If none found, return an empty list.
"""),
    ("human", "Extract unique speakers from this transcript:\n\n{text}"),
])


def _clean_transcript(raw_text: str, file_ext: str) -> str:
    text = raw_text or ""
    if file_ext == "vtt":
        text = re.sub(r'^WEBVTT.*?\n\n', '', text, flags=re.DOTALL)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*', '', text)

    # Remove timeline separators and room presence events.
    text = re.sub(r'^---\s*[^-\n]+?\s*---\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\[[^\]]+\bhas (?:left|entered) the room\]\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _normalize_speaker_name(raw_name: str) -> str:
    name = re.sub(r'^\[[^\]]+\]\s*', '', raw_name).strip()
    # Remove common role/metadata wrappers, e.g. "Jane Doe (Host)"
    name = re.sub(r'\((host|guest|organizer|moderator|admin)\)', '', name, flags=re.IGNORECASE)
    # Drop leading @ used in some chat exports
    name = re.sub(r'^@+', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^A-Za-z0-9 .\'\-&_]+', '', name).strip(" .:-")
    return name


def _canonical_speaker_key(name: str) -> str:
    # Canonical form for dedupe: remove punctuation and collapse spaces.
    key = name.lower()
    key = re.sub(r'[^a-z0-9 ]+', ' ', key)
    key = re.sub(r'\s+', ' ', key).strip()

    # Unify "john d" and "john d." style short surname initials.
    key = re.sub(r'\b([a-z]+)\s+([a-z])\b', r'\1 \2', key)
    return key


def _extract_unique_speakers(text: str) -> list[str]:
    speakers = OrderedDict()

    def maybe_add(candidate_raw: str) -> None:
        candidate = _normalize_speaker_name(candidate_raw)
        if len(candidate) < 2:
            return
        low = candidate.lower()
        if low in {"meeting", "note", "notes", "transcript", "unknown"}:
            return
        # Skip obvious headings/metadata lines, keep this generic.
        if re.search(r"\b(participants?|attendees?|agenda|summary|minutes)\b", low):
            return
        # Ignore heading-like all-caps titles (common in transcript headers).
        letters = re.sub(r"[^A-Za-z]", "", candidate)
        if letters and letters.isupper() and len(candidate.split()) >= 2:
            return
        key = _canonical_speaker_key(candidate)
        if not key:
            return
        # Prefer the "longer" display version when the same person appears in variants.
        existing = speakers.get(key)
        if existing is None or len(candidate) > len(existing):
            speakers[key] = candidate

    def looks_like_name_only_line(s: str) -> bool:
        if not s:
            return False
        if re.search(r'https?://|www\.', s, flags=re.IGNORECASE):
            return False
        if re.search(r'\d{4}', s):
            return False
        if ":" in s or "-" in s and "." not in s:
            return False
        if not re.match(r'^[A-Za-z0-9 .\'\-&]+$', s):
            return False

        candidate = _normalize_speaker_name(s)
        low = candidate.lower()
        if len(candidate) < 2 or low in {"meeting", "note", "transcript"}:
            return False
        if re.search(r"\b(participants?|attendees?|agenda|summary|minutes)\b", low):
            return False

        # Heuristic: speaker labels are usually initials or multi-word names.
        parts = [p for p in candidate.split() if p]
        if "." in candidate:
            return True
        if len(parts) >= 2:
            return True
        return len(candidate) >= 5

    lines = [l.strip() for l in text.splitlines()]
    non_empty_indices = [i for i, l in enumerate(lines) if l]

    idx_set = set(non_empty_indices)
    for i, stripped in enumerate(lines):
        if not stripped:
            continue

        # Bracket-style speaker labels (optionally with a trailing colon before the closing bracket).
        match = None
        bracket_match_colon = re.match(r'^\[\s*(.+?)\s*:\]\s*(\S.*)?$', stripped)
        bracket_match_nocolon = None if bracket_match_colon else re.match(r'^\[\s*(.+?)\s*\]\s*(\S.*)?$', stripped)

        bracket_match = bracket_match_colon or bracket_match_nocolon
        if bracket_match:
            speaker_blob = bracket_match.group(1).strip()
            # "Doug A. tweeted" -> "Doug A."
            speaker_blob = re.sub(
                r'\s+(?:tweeted|played a sound|shared|uploaded|pasted|joined|left|has (?:left|entered))\s*$',
                '',
                speaker_blob,
                flags=re.IGNORECASE,
            )
            maybe_add(speaker_blob)
            continue

        # Teams-like format: "Jane Doe 10:13 AM"
        ts_suffix = re.match(
            r'^([A-Za-z][A-Za-z0-9 .\'\-&_]{1,80})\s+\d{1,2}:\d{2}\s*(?:AM|PM)\s*$',
            stripped,
            flags=re.IGNORECASE,
        )
        if ts_suffix:
            maybe_add(ts_suffix.group(1))
            continue

        # Timestamp prefix format: "10:13 AM Jane Doe"
        ts_prefix = re.match(
            r'^\d{1,2}:\d{2}\s*(?:AM|PM)\s+([A-Za-z][A-Za-z0-9 .\'\-&_]{1,80})$',
            stripped,
            flags=re.IGNORECASE,
        )
        if ts_prefix:
            maybe_add(ts_prefix.group(1))
            continue

        # Common transcript patterns:
        # - "Alice: text"
        # - "[00:12] Bob - text"
        # - "00:12:01 Carol: text"
        match = re.match(
            r'^(?:\[[0-9:\.\- ]+\]\s*|[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?\s+)?'
            r'([A-Za-z][A-Za-z0-9 .\'\-&]{1,60})\s*(?::|-)\s+\S+',
            stripped,
        )
        if match:
            maybe_add(match.group(1))
            continue

        # Alternative separator used by some exports: "Alice | message"
        pipe_sep = re.match(r'^([A-Za-z][A-Za-z0-9 .\'\-&_]{1,80})\s*\|\s+\S+', stripped)
        if pipe_sep:
            maybe_add(pipe_sep.group(1))
            continue

        # Speaker label on its own line, e.g. "Doug A.:" or "Doug A. -"
        delimiter_only = re.match(
            r'^([A-Za-z][A-Za-z0-9 .\'\-&]{1,60})\s*[:\-]\s*$',
            stripped,
        )
        if delimiter_only:
            next_non_empty = None
            for j in range(i + 1, len(lines)):
                if j in idx_set and lines[j]:
                    next_non_empty = j
                    break
            if next_non_empty is not None and not re.match(r'^([A-Za-z][A-Za-z0-9 .\'\-&]{1,60})\s*[:\-]\s*$', lines[next_non_empty]):
                maybe_add(delimiter_only.group(1))
            continue

        # Name-only lines: e.g. some transcripts use a separate line for the speaker name.
        if looks_like_name_only_line(stripped):
            # If the next non-empty line is not another name-only label, count this one.
            next_non_empty = None
            for j in range(i + 1, len(lines)):
                if j in idx_set and lines[j]:
                    next_non_empty = j
                    break
            if next_non_empty is not None and not looks_like_name_only_line(lines[next_non_empty]):
                maybe_add(stripped)

    return sorted(speakers.values())


def _count_words_including_links(text: str) -> int:
    # Count URLs as one token and also count alphanumeric terms (with apostrophes/hyphens).
    tokens = re.findall(r'https?://\S+|www\.\S+|[A-Za-z0-9]+(?:[\'’\-][A-Za-z0-9]+)*', text)
    return len(tokens)


def _extract_speakers_from_participants_block(text: str) -> list[str]:
    # Supports lines such as:
    # "Participants: Alice, Bob, Carol"
    # "Attendees - Alice; Bob; Carol"
    pattern = re.compile(r'^(participants|attendees|speakers)\s*[:\-]\s*(.+)$', re.IGNORECASE | re.MULTILINE)
    found = OrderedDict()
    for _, raw in pattern.findall(text):
        parts = re.split(r'[;,/|]\s*|\s{2,}', raw)
        for part in parts:
            candidate = _normalize_speaker_name(part)
            if not candidate:
                continue
            low = candidate.lower()
            if len(candidate) < 2 or low in {"meeting", "note", "notes", "transcript", "unknown"}:
                continue
            if re.search(r"\b(participants?|attendees?|agenda|summary|minutes)\b", low):
                continue
            found.setdefault(low, candidate)
    return sorted(found.values())


def _llm_extract_speakers(text: str) -> list[str]:
    if not llm:
        return []
    try:
        chain = SPEAKER_FALLBACK_PROMPT | llm
        response = chain.invoke({"text": text[:30000]})
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        parsed = json.loads(raw)
        names = parsed.get("unique_speakers", [])
        if not isinstance(names, list):
            return []

        out = OrderedDict()
        for n in names:
            if not isinstance(n, str):
                continue
            candidate = _normalize_speaker_name(n)
            if len(candidate) < 2:
                continue
            out.setdefault(candidate.lower(), candidate)
        return sorted(out.values())
    except Exception:
        return []


def _merge_speaker_lists(primary: list[str], secondary: list[str]) -> list[str]:
    merged = OrderedDict()
    for name in primary:
        key = _canonical_speaker_key(_normalize_speaker_name(name))
        if key:
            merged[key] = _normalize_speaker_name(name)

    for name in secondary:
        normalized = _normalize_speaker_name(name)
        key = _canonical_speaker_key(normalized)
        if not key:
            continue
        if key in merged:
            if len(normalized) > len(merged[key]):
                merged[key] = normalized
            continue
        merged[key] = normalized

    return sorted(merged.values())


def _fallback_summary(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    short = [s.strip() for s in sentences if s.strip()]
    if not short:
        return "No summary generated."
    return " ".join(short[:2])


def extract_summary(raw_text: str, filename: str) -> dict:
    """Transcript analysis with deterministic metrics + optional LLM summary."""

    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'

    # ── Stage 1: deterministic cleanup and metrics ──
    text = _clean_transcript(raw_text, file_ext)
    unique_speakers = _extract_unique_speakers(text)
    if not unique_speakers:
        print("[Pipeline] Speaker regex found 0; trying participants/attendees fallback...")
        unique_speakers = _extract_speakers_from_participants_block(text)

    print(f"[Pipeline] Speakers detected: {len(unique_speakers)}")
    total_word_count = _count_words_including_links(text)

    print(f"[Pipeline] Cleaned text: {len(text)} chars from '{filename}'")

    # ── Fallback mode when LLM is not available ──
    if not llm or not text_splitter:
        print("[Pipeline] Using fallback mode - no LLM available")
        return {
            "unique_speakers": unique_speakers,
            "speaker_count": len(unique_speakers),
            "word_count": total_word_count,
            "meeting_date": "Unknown",
            "meeting_title": filename,
            "abstractive_summary": _fallback_summary(text),
            "decisions": [],
            "action_items": []
        }

    # ── Stage 2: Split into chunks for semantic analysis ──
    chunks = text_splitter.split_text(text)
    print(f"[Pipeline] Split into {len(chunks)} chunk(s)")

    # ── Stage 3: Analyze each chunk via optional OpenAI ──
    all_decisions = []
    all_action_items = []
    all_summaries = []
    meeting_date = "Unknown"
    meeting_title = filename

    chunk_chain = (CHUNK_ANALYSIS_PROMPT | llm) if llm else None

    if chunk_chain:
        for i, chunk in enumerate(chunks):
            print(f"[Pipeline] Processing chunk {i+1}/{len(chunks)}...")
            try:
                response = chunk_chain.invoke({
                    "filename": filename,
                    "text": chunk,
                })

                # Parse the JSON response
                raw_content = response.content.strip()
                # Strip markdown code fences if present
                if raw_content.startswith("```"):
                    raw_content = re.sub(r'^```(?:json)?\s*', '', raw_content)
                    raw_content = re.sub(r'\s*```$', '', raw_content)

                data = json.loads(raw_content)
                print(f"[Pipeline] Chunk {i+1}: semantic analysis complete")

                chunk_decisions = data.get("decisions", data.get("key_decisions", []))
                if isinstance(chunk_decisions, list):
                    all_decisions.extend(chunk_decisions)
                all_action_items.extend(data.get("action_items", []))
                all_summaries.append(data.get("abstractive_summary", ""))

                if data.get("meeting_date", "Unknown") != "Unknown":
                    meeting_date = data["meeting_date"]
                if data.get("meeting_title") and data["meeting_title"] not in ("Unknown", filename):
                    meeting_title = data["meeting_title"]

            except Exception as e:
                print(f"[Pipeline] Chunk {i+1} error: {e}")
    else:
        print("[Pipeline] OPENROUTER_API_KEY missing. Returning deterministic metrics with fallback summary.")

    # ── Stage 4: Merge chunk results ──
    if llm and len(all_summaries) > 1:
        # Use the LLM to synthesize a coherent final summary from chunk summaries
        print("[Pipeline] Merging chunk summaries via LLM...")
        try:
            merge_chain = FINAL_SUMMARY_PROMPT | llm
            chunk_summaries_text = "\n\n".join(
                [f"Chunk {i+1}: {s}" for i, s in enumerate(all_summaries) if s]
            )
            merge_response = merge_chain.invoke({
                "chunk_summaries": chunk_summaries_text,
            })

            raw_merge = merge_response.content.strip()
            if raw_merge.startswith("```"):
                raw_merge = re.sub(r'^```(?:json)?\s*', '', raw_merge)
                raw_merge = re.sub(r'\s*```$', '', raw_merge)

            merged = json.loads(raw_merge)
            final_summary = merged.get("abstractive_summary", " ".join(all_summaries))
            # Merge in any extra decisions/action items from the synthesis
            extra_decisions = merged.get("decisions", merged.get("key_decisions", []))
            all_decisions.extend(extra_decisions)
            extra_actions = merged.get("action_items", [])
            if isinstance(extra_actions, list):
                all_action_items.extend(extra_actions)
        except Exception as e:
            print(f"[Pipeline] Merge error, falling back to concatenation: {e}")
            final_summary = " ".join([s for s in all_summaries if s])
    elif llm and len(all_summaries) == 1:
        final_summary = all_summaries[0]
    else:
        final_summary = _fallback_summary(text)

    # Normalize/dedupe decisions and action items.
    decision_set = OrderedDict()
    for d in all_decisions:
        if not isinstance(d, str):
            continue
        cleaned = d.strip()
        if cleaned:
            decision_set.setdefault(cleaned.lower(), cleaned)

    action_map = OrderedDict()
    for item in all_action_items:
        if not isinstance(item, dict):
            continue
        owner = str(item.get("owner", "Unknown")).strip() or "Unknown"
        task = str(item.get("task", "")).strip()
        due_by = str(item.get("due_by", "Unknown")).strip() or "Unknown"
        if not task:
            continue
        key = f"{owner.lower()}|{task.lower()}|{due_by.lower()}"
        action_map.setdefault(key, {"owner": owner, "task": task, "due_by": due_by})

    deduped_decisions = list(decision_set.values())
    deduped_action_items = list(action_map.values())

    return {
        "speaker_count": len(unique_speakers),
        "word_count": total_word_count,
        "meeting_date": meeting_date,
        "meeting_title": meeting_title,
        "abstractive_summary": final_summary or "No summary generated.",
        "decisions": deduped_decisions,
        "action_items": deduped_action_items,
        # Backward compatibility for existing UI consumers.
        "key_decisions": deduped_decisions,
        "unique_speakers": unique_speakers,
    }