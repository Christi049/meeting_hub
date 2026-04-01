import os
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Annotated
from services.parser_service import extract_summary
from services.indexing_service import index_meeting

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

        # Run the full NLP pipeline (Normalization → NER → Summarization)
        analysis = extract_summary(text, file.filename)
        project = _safe_segment(analysis.get("meeting_title", "Unknown"), "Unknown Project")
        date = _safe_segment(analysis.get("meeting_date", "Unknown"), "Unknown Date")
        target_dir = os.path.join(STORAGE_ROOT, project, date)
        os.makedirs(target_dir, exist_ok=True)
        stored_path = os.path.join(target_dir, _safe_segment(file.filename, "transcript.txt"))
        with open(stored_path, "wb") as out_file:
            out_file.write(content)
        meeting_id = index_meeting(
            raw_text=text,
            file_name=file.filename,
            analysis=analysis,
            stored_path=os.path.relpath(stored_path, STORAGE_ROOT),
        )

        results.append({
            "meeting_id": meeting_id,
            "file_name": file.filename,
            "word_count": analysis["word_count"],
            "speakers": analysis["speaker_count"],
            "unique_speakers": analysis["unique_speakers"],
            "date": analysis["meeting_date"],
            "title": analysis["meeting_title"],
            "abstractive_summary": analysis["abstractive_summary"],
            "decisions": analysis.get("decisions", analysis.get("key_decisions", [])),
            "action_items": analysis.get("action_items", []),
            "stored_path": os.path.relpath(stored_path, STORAGE_ROOT)
        })

    return results