# 🤖 Agentic Multi-Modal Assistant

An intelligent multi-agent system that processes text, images, PDFs, audio, and YouTube videos to autonomously understand user intent and execute tasks.

## 🌟 Features

### Supported Input Types
- **Text** - Direct text input for questions, sentiment analysis, code explanation
- **Images** (JPG/PNG) - OCR extraction using Tesseract + EasyOCR fallback
- **PDF** (text/scanned) - 3-tier extraction: PyPDF2 → pdfplumber → OCR
- **Audio** (MP3/WAV/M4A) - Groq Whisper transcription (25MB limit)
- **YouTube URLs** - Automatic transcript fetching with multi-language support

### Autonomous Task Execution
The agent automatically detects and performs:

1. **Text Extraction** - From images and PDFs with confidence scoring
2. **YouTube Transcripts** - Auto-detect URLs and fetch transcripts
3. **Summarization** - Three formats:
   - One-line summary (≤20 words)
   - Three bullet points
   - Five-sentence comprehensive summary
4. **Sentiment Analysis** - Label + confidence + justification
5. **Code Explanation** - Language detection, explanation, bug detection, time complexity
6. **Audio Transcription + Summary** - Converts speech to text with automatic summarization
7. **Conversational Q&A** - Friendly responses to general questions

### 🧠 Intelligent Clarification
When user intent is unclear (confidence < 0.7), the agent **asks follow-up questions** before proceeding:
- "Could you clarify whether you want a summary or sentiment analysis?"
- "What would you like me to do with this extracted text?"
- Remembers uploaded files across clarification turns

### 🏗️ Multi-Agent Architecture
- **Planner Agent** - Analyzes intent, determines confidence, routes to execution
- **Executor Agent** - Performs tasks autonomously with structured outputs
- **LangGraph Orchestration** - Explicit state flow for transparency
- **Session Management** - Maintains context across multi-turn conversations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed
- FFmpeg (for audio processing)
- Groq API key ([get one free](https://console.groq.com))

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd DSAI
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install system dependencies**

**macOS:**
```bash
brew install tesseract ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr ffmpeg
```

**Windows:**
- Install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Install [FFmpeg](https://ffmpeg.org/download.html)

5. **Configure environment**

Create `.env` file in project root:
```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=25
```

### Running the Application

1. **Start the FastAPI server**
```bash
uvicorn src.api.main:app --reload --port 8000
```

2. **Access the UI**
```
http://localhost:8000
```

The simple HTML interface will load automatically.

## 📝 Usage Examples

### Example 1: Audio Transcription + Summary
1. Upload an audio file (MP3/WAV/M4A)
2. Type any message or leave blank
3. Agent automatically transcribes and summarizes

**Input:** `lecture_audio.mp3` (5 minutes)  
**Output:**
```json
{
  "transcript": "Full transcription text...",
  "summary": {
    "one_line": "Lecture covers neural network basics and backpropagation",
    "three_bullets": [
      "Neural networks consist of layers of interconnected neurons",
      "Activation functions like sigmoid and ReLU introduce non-linearity",
      "Backpropagation updates weights using gradient descent"
    ],
    "five_sentence": "..."
  },
  "duration": 317.5,
  "language": "en"
}
```

### Example 2: PDF Question Answering
1. Upload PDF: `meeting_notes.pdf`
2. Type: "What are the action items?"
3. Agent extracts text and identifies action items

**Input:** 3-page PDF + "What are the action items?"  
**Output:** List of action items extracted from the document

### Example 3: Image Code Explanation
1. Upload screenshot of code
2. Type: "Explain this code"
3. Agent performs OCR, detects language, explains code

**Input:** Image of Python function  
**Output:**
```json
{
  "language": "Python",
  "explanation": "This function implements binary search...",
  "bugs": ["Missing bounds check for empty array"],
  "time_complexity": "O(log n) - binary search halves search space"
}
```

### Example 4: YouTube Video Summary
**Input:** `https://www.youtube.com/watch?v=aircAruvnKk summarize this`  
**Output:** Transcript + three-format summary

### Example 5: Clarification Flow
1. Upload PDF: `document.pdf`
2. Type: "do it"
3. Agent asks: "Would you like me to summarize this document or analyze its sentiment?"
4. Type: "summary"
5. Agent generates summary using stored PDF content

## 🏛️ Architecture

### System Flow
```
User Input → Input Processing → Planner Agent → [Clarify?] → Executor Agent → Response
                    ↓                ↓                              ↓
              File Extraction   Intent Analysis              Task Execution
```

### Components

**1. Input Processing (`src/orchestration/input_processor.py`)**
- Detects input type (text/image/PDF/audio/YouTube)
- Routes to appropriate extraction tool
- Stores extracted content in session

**2. Planner Agent (`src/agents/planner.py`)**
- Analyzes user intent using Groq LLM (llama-3.1-70b-versatile)
- Confidence scoring (0.0-1.0)
- Triggers clarification if confidence < 0.7
- Creates structured execution plan

**3. Executor Agent (`src/agents/executor.py`)**
- Executes tasks based on planner's instructions
- Uses Groq LLM (llama-3.1-8b-instant) for fast execution
- Structured JSON outputs for all tasks
- Handles errors with graceful fallbacks

**4. LangGraph Orchestration (`src/orchestration/agent_graph.py`)**
- StateGraph with 4 nodes:
  - `input_processing_node`
  - `planner_node`
  - `executor_node`
  - `format_response_node`
- Conditional routing based on clarification needs
- Execution trace for explainability

**5. Extraction Tools (`src/tools/`)**
- `pdf_tool.py` - 3-tier PDF extraction
- `ocr_tool.py` - Tesseract + EasyOCR with confidence
- `audio_tool.py` - Groq Whisper transcription
- `youtube_tool.py` - YouTube transcript fetching

**6. Session Management (`src/state/conversation_manager.py`)**
- In-memory session storage
- Preserves extracted content across turns
- 30-minute session timeout

### Technology Stack
- **Framework:** FastAPI + Uvicorn
- **Multi-Agent:** LangGraph + LangChain
- **LLM Provider:** Groq (llama-3.1 models)
- **Audio:** Groq Whisper API
- **OCR:** pytesseract, EasyOCR
- **PDF:** PyPDF2, pdfplumber, pdf2image
- **Frontend:** Vanilla HTML/CSS/JavaScript

## 📊 Project Structure

```
DSAI/
├── frontend/
│   └── index.html              # Simple UI
├── src/
│   ├── agents/
│   │   ├── executor.py         # Task execution agent
│   │   └── planner.py          # Intent analysis agent
│   ├── api/
│   │   └── main.py             # FastAPI server
│   ├── orchestration/
│   │   ├── agent_graph.py      # LangGraph workflow
│   │   └── input_processor.py  # Input type detection
│   ├── state/
│   │   └── conversation_manager.py  # Session management
│   ├── tools/
│   │   ├── audio_tool.py       # Audio transcription
│   │   ├── ocr_tool.py         # Image text extraction
│   │   ├── pdf_tool.py         # PDF text extraction
│   │   └── youtube_tool.py     # YouTube transcripts
│   └── utils/
│       └── config.py           # Configuration
├── .env                        # Environment variables
├── .gitignore
├── README.md
├── requirements.txt
└── TEST_CASES.md              # Test case documentation
```

## 🧪 Testing

See [TEST_CASES.md](TEST_CASES.md) for comprehensive test scenarios and results.

**Quick Test:**
```bash
# Test text sentiment
curl -X POST http://localhost:8000/process \
  -F "message=I absolutely love this product! Best purchase ever!" \
  -F "session_id=test123"

# Test with PDF
curl -X POST http://localhost:8000/process \
  -F "message=summarize this" \
  -F "file=@sample.pdf" \
  -F "session_id=test123"
```

## 🔧 Configuration

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM access |
| `LOG_LEVEL` | No | INFO | Logging verbosity |
| `MAX_FILE_SIZE_MB` | No | 25 | Maximum file upload size |

### LLM Models Used
- **Planner:** `llama-3.1-70b-versatile` (better reasoning)
- **Executor:** `llama-3.1-8b-instant` (faster execution)
- **Audio:** `whisper-large-v3` (transcription)

## ⚠️ Known Issues & Limitations

1. **Groq Library Conflict**
   - `groq==1.0.0` incompatible with `langchain-groq==0.0.1`
   - Audio transcription requires groq 1.0.0
   - Workaround: Both installed, functionality preserved

2. **YouTube API Version**
   - Requires `youtube-transcript-api==1.2.3`
   - Breaking changes from v0.6.2 (instance methods, attribute access)

3. **Audio File Limits**
   - 25MB max file size (Groq Whisper limit)
   - Supported formats: MP3, WAV, M4A, FLAC

4. **Session Storage**
   - In-memory only (lost on server restart)
   - Production: Use Redis/PostgreSQL

5. **Large Documents**
   - No RAG implementation (not required by assignment)
   - PDFs > 10 pages may hit token limits

## 🎯 Assignment Compliance

### Requirements Met ✅
- [x] Text, Image, PDF, Audio inputs
- [x] OCR with confidence scoring
- [x] Speech-to-Text with cleanup
- [x] Intent understanding
- [x] Mandatory clarification on ambiguity
- [x] All 7 required tasks
- [x] FastAPI + Simple UI
- [x] Text-only outputs
- [x] Clean codebase
- [x] Architecture diagram
- [x] Test cases
- [x] README

### Bonus Features ✅
- [x] **Multi-agent orchestration** (Planner + Executor as separate agents)
- [x] YouTube transcript support
- [x] Explainability (execution trace returned)
