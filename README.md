
# Meeting Hub — AI-Powered Meeting Transcript Analyzer

## The Problem

Teams generate hours of meeting recordings and transcripts, but extracting actionable insights — who said what, what was decided, and who owns which task — is time-consuming and error-prone when done manually. Important decisions and action items get buried in long transcript files, leading to missed follow-ups and poor accountability.

## The Solution

Meeting Hub is a full-stack web application that ingests `.txt` and `.vtt` meeting transcript files and automatically extracts structured intelligence from them. Users upload transcripts via a drag-and-drop interface, and the system identifies speakers, generates abstractive summaries, surfaces decisions, and creates a structured list of action items with owners and deadlines. A built-in AI chat interface lets users query across all their uploaded meetings in natural language, with answers grounded in the transcript content. Results can be exported as CSV or PDF reports.

Key features:
- **Transcript parsing** — supports plain text (`.txt`) and WebVTT (`.vtt`) formats
- **Speaker detection** — regex-based heuristics with LLM fallback for robust speaker identification
- **LLM-powered analysis** — abstractive summaries, decision extraction, and action item detection via OpenRouter (GPT-4o-mini)
- **Semantic search** — vector embeddings (TF-IDF hash-based) stored in SQLite for similarity search across transcripts
- **Sentiment analysis** — per-speaker and per-segment tone classification
- **Natural language Q&A** — intent-classified retrieval from vector chunks, structured SQL data, and sentiment records
- **Dashboard** — aggregated view of all uploaded meetings with sentiment scores and meeting metadata
- **Export** — download decisions and action items as CSV or PDF

---

## Tech Stack

### Programming Languages
- **Python 3.11+** — backend services, NLP pipeline, API
- **TypeScript / JavaScript** — frontend application and embedded UI scripts

### Frameworks
- **FastAPI** — REST API backend with async file upload support
- **React 18** — frontend SPA
- **Tailwind CSS** — utility-first styling

### Databases
- **SQLite** — local storage for meetings, transcript chunks, decisions, action items, and sentiment records (via `sqlite3`)

### APIs & Third-Party Tools
- **OpenRouter API** (`openai/gpt-4o-mini`) — LLM inference for transcript summarization, decision extraction, and Q&A
- **LangChain** (`langchain-core`, `langchain-openai`, `langchain-text-splitters`) — prompt templates and LLM chaining
- **jsPDF** — client-side PDF export
- **Vite** — frontend build tool and dev server

### Other Libraries
- `python-multipart` — multipart file upload handling in FastAPI
- `python-dotenv` — environment variable management
- `pydantic` — request/response schema validation
- `uvicorn` — ASGI server for FastAPI

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher and npm
- An [OpenRouter](https://openrouter.ai) API key

---

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-directory>
```

---

### 2. Backend Setup

```bash
cd src/backend
```

#### Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### Install Python dependencies

```bash
pip install -r requirements.txt
```

#### Configure environment variables

Create a `.env` file inside `src/backend/`:

```bash
cp .env.example .env  # if an example exists, otherwise create manually
```

Add the following to `src/backend/.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

> **Note:** The application works without an API key. Without one, transcript analysis falls back to deterministic extraction (speaker detection and word counts), and the Q&A chat will return raw transcript excerpts instead of LLM-generated answers.

#### Run the backend server

```bash
python app.py
```

The API will be available at `http://127.0.0.1:8001`.

---

### 3. Frontend Setup

Open a new terminal window:

```bash
cd src
```

#### Install Node dependencies

```bash
npm install
```

#### Start the development server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or whichever port Vite assigns).

---

### 4. Using the Application

1. Open `http://localhost:5173` in your browser.
2. Navigate to the **Workspace** tab.
3. Drag and drop one or more `.txt` or `.vtt` transcript files into the upload zone.
4. View the extracted speakers, summary, decisions, and action items in the Analysis Results panel.
5. Use the **Chat** panel on the right to ask natural language questions about your transcripts (e.g., *"What action items were assigned to Alice?"* or *"Summarize the decisions from last week's meeting"*.
6. Navigate to the **Dashboard** tab for an aggregated view across all uploaded meetings.
7. Export decisions and action items from any meeting using the **Export CSV** or **Export PDF** buttons.

---
