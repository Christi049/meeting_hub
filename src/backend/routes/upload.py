import os
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Annotated
import threading

# Try to import services with thread-level timeout to avoid blocking on LangChain
SERVICES_AVAILABLE = False
extract_summary = None
index_meeting = None

def _load_services():
    """Load services in a way that doesn't block if imports hang."""
    global SERVICES_AVAILABLE, extract_summary, index_meeting
    try:
        from services.parser_service import extract_summary as extract_fn
        from services.indexing_service import index_meeting as index_fn
        extract_summary = extract_fn
        index_meeting = index_fn
        SERVICES_AVAILABLE = True
        print("✓ Services loaded successfully")
    except Exception as e:
        print(f"✗ Services failed to load: {type(e).__name__}: {str(e)[:100]}")
        SERVICES_AVAILABLE = False

# Try loading services, but don't block the whole app if it fails
service_thread = threading.Thread(target=_load_services, daemon=True)
service_thread.start()
service_thread.join(timeout=5)  # Wait max 5 seconds, then give up

router = APIRouter()
STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


def _safe_segment(value: str, fallback: str) -> str:
    if not value or value == "Unknown":
        return fallback
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80] if cleaned else fallback


@router.post("/upload-transcripts")
async def upload_transcripts(
    files: Annotated[List[UploadFile], File(description="Upload transcripts")]
):
    results = []

    for file in files:
        # Validate file type
        if not file.filename.lower().endswith(('.txt', '.vtt')):
            raise HTTPException(status_code=400, detail=f"Unsupported format: {file.filename}. Upload .txt or .vtt files only.")

        content = await file.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be UTF-8 encoded.")

        # Use your backend services if available
        if SERVICES_AVAILABLE and extract_summary:
            try:
                analysis = extract_summary(text, file.filename)
            except Exception as e:
                print(f"Service execution error: {e}")
                analysis = {
                    "meeting_title": file.filename,
                    "meeting_date": "Unknown",
                    "word_count": len(text.split()),
                    "speaker_count": 0,
                    "unique_speakers": [],
                    "abstractive_summary": "Error in analysis",
                    "decisions": [],
                    "action_items": []
                }
        else:
            # Fallback when services not available
            analysis = {
                "meeting_title": file.filename,
                "meeting_date": "Unknown",
                "word_count": len(text.split()),
                "speaker_count": 0,
                "unique_speakers": [],
                "abstractive_summary": "Analysis service not available",
                "decisions": [],
                "action_items": []
            }
        
        project = _safe_segment(analysis.get("meeting_title", "Unknown"), "Unknown Project")
        date = _safe_segment(analysis.get("meeting_date", "Unknown"), "Unknown Date")
        target_dir = os.path.join(STORAGE_ROOT, project, date)
        os.makedirs(target_dir, exist_ok=True)
        stored_path = os.path.join(target_dir, _safe_segment(file.filename, "transcript.txt"))
        with open(stored_path, "wb") as out_file:
            out_file.write(content)
        
        if SERVICES_AVAILABLE and index_meeting:
            try:
                result = index_meeting(
                    raw_text=text,
                    file_name=file.filename,
                    analysis=analysis,
                    stored_path=os.path.relpath(stored_path, STORAGE_ROOT),
                )
                # Handle both single return (int) and tuple return (int, list)
                if isinstance(result, tuple):
                    meeting_id, segments = result
                else:
                    meeting_id = result
                    segments = []
                print(f"[Segments] Generated {len(segments)} segment(s)")
            except Exception as e:
                print(f"✗ Error in index_meeting for {file.filename}: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                meeting_id = hash(file.filename) % 1000000
                segments = []
        else:
            meeting_id = hash(file.filename) % 1000000
            segments = []

        results.append({
            "meeting_id": meeting_id,
            "file_name": file.filename,
            "word_count": analysis.get("word_count", 0),
            "speakers": analysis.get("speaker_count", 0),
            "unique_speakers": analysis.get("unique_speakers", []),
            "date": analysis.get("meeting_date", "Unknown"),
            "title": analysis.get("meeting_title", file.filename),
            "abstractive_summary": analysis.get("abstractive_summary", ""),
            "decisions": analysis.get("decisions", analysis.get("key_decisions", [])),
            "action_items": analysis.get("action_items", []),
            "stored_path": os.path.relpath(stored_path, STORAGE_ROOT),
            "segments": [
                {
                    "segment_index": s["segment_index"],
                    "start_time": s["start_time"],
                    "sentiment_label": s["sentiment_label"],
                    "sentiment_score": s["sentiment_score"],
                }
                for s in segments
            ],
        })
        print(f"✓ Upload complete for {file.filename}")
        print(f"  - Speakers: {analysis.get('speaker_count', 0)}")
        print(f"  - Words: {analysis.get('word_count', 0)}")
        print(f"  - Decisions: {len(analysis.get('decisions', []))}")
        print(f"  - Action items: {len(analysis.get('action_items', []))}")
        if segments:
            for seg in segments:
                print(f"  - Segment {seg['segment_index']}: {seg['sentiment_label']} (score: {seg['sentiment_score']})")

    print(f"✓ Returning {len(results)} result(s)")
    return results