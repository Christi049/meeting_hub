import os
from services.parser_service import extract_summary

ALLOWED_EXT = ["txt", "vtt"]
STORAGE_PATH = "storage"

os.makedirs(STORAGE_PATH, exist_ok=True)


async def process_files(files):
    responses = []

    for file in files:
        filename = file.filename
        ext = filename.split(".")[-1]

        # 🔒 Validate file
        if ext not in ALLOWED_EXT:
            responses.append({
                "file_name": filename,
                "error": "Unsupported file type"
            })
            continue

        # 📂 Save file
        file_path = os.path.join(STORAGE_PATH, filename)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 📊 Extract summary
        summary = extract_summary(content.decode("utf-8"), filename)

        responses.append({
            "file_name": filename,
            **summary
        })

    return responses