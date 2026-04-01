from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from routes.query import router as query_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Hub - Upload Transcripts</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.9);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            max-width: 550px;
            width: 100%;
            text-align: center;
            backdrop-filter: blur(10px);
            box-sizing: border-box;
        }
        h1 { color: #2d3748; margin-bottom: 5px; font-weight: 800; }
        p { color: #718096; margin-bottom: 25px; line-height: 1.5; }
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #4a5568;
            font-weight: 600;
            font-size: 14px;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            box-sizing: border-box;
            font-size: 15px;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #4299e1;
        }
        #drop-zone {
            border: 2px dashed #4299e1;
            border-radius: 12px;
            padding: 30px 20px;
            background: #ebf8ff;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        #drop-zone:hover { background: #bee3f8; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(66,153,225,0.2); }
        #drop-zone.dragover { background: #bee3f8; border-color: #3182ce; }
        .upload-icon { font-size: 40px; margin-bottom: 10px; }
        #file-input { display: none; }
        .btn {
            background: #4299e1;
            color: white;
            border: none;
            padding: 14px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 25px;
            width: 100%;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(66, 153, 225, 0.3);
        }
        .btn:hover:not(:disabled) { background: #3182ce; transform: translateY(-1px); box-shadow: 0 6px 8px rgba(66, 153, 225, 0.4); }
        .btn:disabled { background: #a0aec0; cursor: not-allowed; box-shadow: none; opacity: 0.7; }
        #results {
            margin-top: 30px;
            text-align: left;
            display: none;
            animation: fadeIn 0.5s;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .result-item {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.06);
            border-left: 5px solid #48bb78;
        }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid #edf2f7;
        }
        .filename { font-weight: 700; color: #2d3748; word-break: break-all; margin-right: 15px; font-size: 16px; }
        .wordcount { color: #276749; font-weight: bold; background: #c6f6d5; padding: 6px 12px; border-radius: 20px; font-size: 13px; white-space: nowrap; }
        .result-details {
            font-size: 14px;
            color: #4a5568;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 10px;
        }
        .detail-card {
            background: #f7fafc;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .detail-label { display: block; font-size: 12px; color: #718096; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
        #selected-files { margin-top: 20px; color: #4a5568; font-size: 14px; text-align: left; padding: 0 10px; }
        .file-item { margin-top: 4px; color: #2b6cb0; font-weight: 600; }
        .error-message { color: #e53e3e; background: #fff5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #e53e3e; margin-bottom: 20px; display: none; text-align: left; font-size: 14px; font-weight: 500;}
        .mini-btn {
            background: #2b6cb0;
            color: #fff;
            border: none;
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
        }
        .mini-btn:hover { background: #2c5282; }
        .simple-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
        .simple-table th, .simple-table td { border: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }
        .simple-table th { background: #edf2f7; color: #2d3748; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Meeting Hub</h1>
        <p>Upload meeting transcripts—we'll automatically extract the project title and date for storage!</p>
        
        <div id="error-alert" class="error-message"></div>

        <form id="upload-form">
            <div id="drop-zone" onclick="document.getElementById('file-input').click()">
                <div class="upload-icon">📄</div>
                <div style="font-size: 18px; color: #2b6cb0;"><strong>Click to browse</strong> or drag & drop files</div>
                <div style="font-size: 14px; color: #718096; margin-top: 8px;">Supports multiple .txt or .vtt files</div>
            </div>
            <input type="file" id="file-input" name="files" multiple accept=".txt,.vtt,text/plain">
            
            <div id="selected-files"></div>
            
            <button type="submit" class="btn" id="submit-btn" disabled>Upload and Analyze Transcripts</button>
        </form>

        <div id="results">
            <h3 style="color: #2d3748; margin-bottom: 20px; border-bottom: 2px solid #edf2f7; padding-bottom: 10px;">Analysis Summaries</h3>
            <div id="results-list"></div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js"></script>
    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const submitBtn = document.getElementById('submit-btn');
        const form = document.getElementById('upload-form');
        const selectedFilesDiv = document.getElementById('selected-files');
        const resultsDiv = document.getElementById('results');
        const resultsList = document.getElementById('results-list');
        const errorAlert = document.getElementById('error-alert');

        let selectedFiles = [];

        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFiles();
            }
        });

        fileInput.addEventListener('change', handleFiles);

        function handleFiles() {
            selectedFiles = Array.from(fileInput.files);
            errorAlert.style.display = 'none'; // Clear previous errors

            // Validate by extension (browser MIME can be empty/inconsistent)
            const invalidFiles = selectedFiles.filter(f => {
                const lower = f.name.toLowerCase();
                return !(lower.endsWith('.txt') || lower.endsWith('.vtt'));
            });
            if (invalidFiles.length > 0) {
                showError(`Invalid file format detected. Please upload .txt or .vtt records.`);
                selectedFiles = [];
                fileInput.value = '';
                selectedFilesDiv.innerHTML = '';
                submitBtn.disabled = true;
                return;
            }

            if (selectedFiles.length > 0) {
                selectedFilesDiv.innerHTML = `<div style="margin-bottom: 8px; font-weight: bold;">Selected ${selectedFiles.length} file(s):</div>` + 
                    selectedFiles.map(f => `<div class="file-item">• ${f.name}</div>`).join('');
                submitBtn.disabled = false;
            } else {
                selectedFilesDiv.innerHTML = '';
                submitBtn.disabled = true;
            }
        }

        function showError(msg) {
            errorAlert.textContent = msg;
            errorAlert.style.display = 'block';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function escapeHtml(value) {
            if (value === null || value === undefined) return '';
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function toCsvCell(value) {
            const raw = String(value ?? '');
            const escaped = raw.replace(/"/g, '""');
            return `"${escaped}"`;
        }

        function exportCsv(result) {
            const rows = [];
            rows.push(['Type', 'Owner', 'Item', 'Due By']);
            (result.decisions || []).forEach(d => rows.push(['Decision', '', d, '']));
            (result.action_items || []).forEach(a => rows.push(['Action Item', a.owner || 'Unknown', a.task || '', a.due_by || 'Unknown']));

            const csv = rows.map(row => row.map(toCsvCell).join(',')).join('\\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            const baseName = (result.file_name || 'meeting').replace(/\\.[^.]+$/, '');
            link.download = `${baseName}_decisions_actions.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }

        function exportPdf(result) {
            if (!window.jspdf || !window.jspdf.jsPDF) {
                showError('PDF library failed to load. Please try again or use CSV export.');
                return;
            }

            const doc = new window.jspdf.jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 14;
            const maxWidth = pageWidth - (margin * 2);
            let y = margin;

            function ensureSpace(required = 8) {
                if (y + required > pageHeight - margin) {
                    doc.addPage();
                    y = margin;
                }
            }

            function writeLine(text, size = 11, bold = false, gap = 6) {
                doc.setFont('helvetica', bold ? 'bold' : 'normal');
                doc.setFontSize(size);
                const lines = doc.splitTextToSize(String(text ?? ''), maxWidth);
                for (const line of lines) {
                    ensureSpace(gap + 2);
                    doc.text(line, margin, y);
                    y += gap;
                }
            }

            function drawTable(headers, rows, colWidths) {
                const rowPad = 3;
                const lineHeight = 5;

                const drawRow = (cells, isHeader = false) => {
                    const wrapped = cells.map((cell, idx) => doc.splitTextToSize(String(cell ?? ''), colWidths[idx] - (rowPad * 2)));
                    const maxLines = Math.max(...wrapped.map(w => Math.max(1, w.length)));
                    const rowHeight = (maxLines * lineHeight) + (rowPad * 2);

                    ensureSpace(rowHeight + 2);
                    let x = margin;
                    for (let i = 0; i < cells.length; i++) {
                        if (isHeader) {
                            doc.setFillColor(237, 242, 247);
                            doc.rect(x, y, colWidths[i], rowHeight, 'FD');
                            doc.setFont('helvetica', 'bold');
                        } else {
                            doc.rect(x, y, colWidths[i], rowHeight);
                            doc.setFont('helvetica', 'normal');
                        }
                        doc.setFontSize(10);
                        doc.text(wrapped[i], x + rowPad, y + rowPad + 3);
                        x += colWidths[i];
                    }
                    y += rowHeight;
                };

                drawRow(headers, true);
                rows.forEach(r => drawRow(r, false));
                y += 4;
            }

            writeLine(`Meeting Report: ${result.file_name || 'meeting'}`, 14, true, 7);
            writeLine(`Project: ${result.title || 'Unknown'}`);
            writeLine(`Date: ${result.date || 'Unknown'}`);
            writeLine(`Speakers: ${result.speakers || 0}`);
            y += 2;

            writeLine('Detected Speakers', 12, true, 7);
            writeLine((result.unique_speakers || []).join(', ') || 'None');
            y += 2;

            writeLine('Decisions', 12, true, 7);
            const decisionsRows = (result.decisions && result.decisions.length)
                ? result.decisions.map((d, i) => [String(i + 1), d])
                : [['-', 'None detected']];
            drawTable(['#', 'Decision'], decisionsRows, [16, maxWidth - 16]);

            writeLine('Action Items', 12, true, 7);
            const actionRows = (result.action_items && result.action_items.length)
                ? result.action_items.map((a, i) => [String(i + 1), a.owner || 'Unknown', a.task || '', a.due_by || 'Unknown'])
                : [['-', '-', 'None detected', '-']];
            drawTable(['#', 'Who', 'What', 'By When'], actionRows, [12, 36, maxWidth - 12 - 36 - 34, 34]);

            const baseName = (result.file_name || 'meeting').replace(/\\.[^.]+$/, '');
            doc.save(`${baseName}_decisions_actions.pdf`);
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (selectedFiles.length === 0) return;

            errorAlert.style.display = 'none';
            submitBtn.disabled = true;
            submitBtn.textContent = 'Uploading and Analyzing...';
            resultsDiv.style.display = 'none';

            const formData = new FormData();
            selectedFiles.forEach(file => { formData.append('files', file); });

            try {
                const response = await fetch('/upload-transcripts', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    throw new Error(errData.detail || 'Upload failed with status ' + response.status);
                }

                const data = await response.json();
                
                resultsList.innerHTML = data.map((result, index) => `
                    <div class="result-item" id="result-${index}">
                        <div class="result-header">
                            <span class="filename">${result.file_name}</span>
                            <span class="wordcount">${result.word_count} words</span>
                        </div>
                        <div style="margin-bottom: 12px; font-size: 14px; color: #4a5568;">
                            <strong>Project Title:</strong> ${result.title}
                        </div>
                        <div class="result-details">
                            <div class="detail-card">
                                <span class="detail-label">Detected Date</span>
                                <strong>${result.date}</strong>
                            </div>
                            <div class="detail-card">
                                <span class="detail-label">Speakers Found</span>
                                <strong>${result.speakers}</strong>
                            </div>
                            <div class="detail-card">
                                <span class="detail-label">Stored Under</span>
                                <strong>${escapeHtml(result.stored_path || 'N/A')}</strong>
                            </div>
                            <div class="detail-card" style="grid-column: span 2; padding: 12px;">
                                <span class="detail-label">Detected Speaker Names</span>
                                <div style="font-size: 13px; color: #4a5568; margin-top: 4px; line-height: 1.5;">
                                    ${(result.unique_speakers && result.unique_speakers.length)
                                        ? result.unique_speakers.map(escapeHtml).join(', ')
                                        : 'None detected'}
                                </div>
                            </div>
                            <div class="detail-card" style="grid-column: span 2; padding: 15px;">
                                <span class="detail-label">Abstractive Summary</span>
                                <div style="font-size: 13px; color: #4a5568; margin-top: 5px;">${result.abstractive_summary}</div>
                            </div>
                            <div class="detail-card" style="grid-column: span 2; padding: 15px;">
                                <span class="detail-label">Decisions</span>
                                <ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 13px; color: #4a5568;">
                                    ${result.decisions && result.decisions.length > 0 
                                        ? result.decisions.map(d => `<li>${escapeHtml(d)}</li>`).join('') 
                                        : '<li>None detected</li>'}
                                </ul>
                            </div>
                            <div class="detail-card" style="grid-column: span 2; padding: 15px;">
                                <span class="detail-label">Action Items</span>
                                ${(result.action_items && result.action_items.length > 0) ? `
                                    <table class="simple-table">
                                        <thead>
                                            <tr>
                                                <th>Who</th>
                                                <th>What</th>
                                                <th>By When</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${result.action_items.map(a => `
                                                <tr>
                                                    <td>${escapeHtml(a.owner || 'Unknown')}</td>
                                                    <td>${escapeHtml(a.task || '')}</td>
                                                    <td>${escapeHtml(a.due_by || 'Unknown')}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                ` : '<div style="font-size: 13px; color: #4a5568;">None detected</div>'}
                                <div style="margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;">
                                    <button class="mini-btn export-csv-btn" data-result-index="${index}">Export CSV</button>
                                    <button class="mini-btn export-pdf-btn" data-result-index="${index}">Export PDF</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');

                document.querySelectorAll('.export-csv-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const idx = Number(btn.getAttribute('data-result-index'));
                        if (!Number.isNaN(idx) && data[idx]) exportCsv(data[idx]);
                    });
                });
                document.querySelectorAll('.export-pdf-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const idx = Number(btn.getAttribute('data-result-index'));
                        if (!Number.isNaN(idx) && data[idx]) exportPdf(data[idx]);
                    });
                });
                
                resultsDiv.style.display = 'block';
            } catch (error) {
                showError('Error uploading files: ' + error.message);
            } finally {
                submitBtn.textContent = 'Upload and Analyze Transcripts';
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""

@app.get("/")
def home():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)

app.include_router(upload_router)
app.include_router(query_router)