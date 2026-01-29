# 🏗️ Architecture Diagram

## System Overview

Simple flow: **User → Frontend → FastAPI → Agents → Response**

```mermaid
graph LR
    User[👤 User] -->|Upload + Message| UI[Frontend]
    UI -->|POST /process| API[FastAPI]
    API --> Planner[🧠 Planner Agent]
    Planner -->|Clear Intent| Executor[⚙️ Executor Agent]
    Planner -->|Unclear| Clarify[❓ Ask Question]
    Executor --> Result[✅ Return Result]
    Clarify --> UI
    Result --> UI
```

**Key Components:**
1. **Frontend** - Simple HTML form for file upload
2. **FastAPI** - Receives files, saves temporarily
3. **Planner Agent** - Understands what user wants (llama-3.1-70b)
4. **Executor Agent** - Does the actual task (llama-3.1-8b)

---

## How It Works (Step-by-Step)

### 1. User Uploads a File

```mermaid
graph TD
    Start[User uploads PDF] --> API[FastAPI saves file to /tmp]
    API --> Extract[Extract text from PDF]
    Extract -->|Try 1| PyPDF[PyPDF2]
    PyPDF -->|Success ✓| Store[Store text in session]
    PyPDF -->|Fail ✗| Fallback[Try pdfplumber]
    Fallback -->|Success ✓| Store
    Fallback -->|Fail ✗| OCR[Try OCR]
    OCR --> Store
```

**File Types Handled:**
- PDF → PyPDF2 → pdfplumber → OCR
- Images → Tesseract → EasyOCR
- Audio → Groq Whisper
- YouTube → Fetch transcript

---

### 2. Planner Decides What to Do

```mermaid
graph TD
    Input[User: 'summarize this'] --> Planner[Planner analyzes]
    Planner --> Confidence{Confidence Score}
    Confidence -->|>= 0.7<br/>CLEAR| Execute[Execute summarization]
    Confidence -->|< 0.7<br/>UNCLEAR| Ask[Ask clarification]
```

**Examples:**
- ✅ "summarize this" → Clear (confidence 0.9)
- ✅ "what's the sentiment?" → Clear (confidence 0.85)
- ❌ "do something" → Unclear (confidence 0.2) → Asks question

---

### 3. Executor Runs the Task

```mermaid
graph LR
    Executor[Executor] --> Task{What task?}
    Task -->|Summarize| Sum[Return 3 formats]
    Task -->|Sentiment| Sent[Return label + confidence]
    Task -->|Code| Code[Return bugs + complexity]
    Task -->|Q&A| QA[Return answer]
```

**All tasks use Groq LLM to generate structured JSON responses**

---

## Multi-Turn Conversations

How the system remembers context across messages:

```mermaid
sequenceDiagram
    User->>System: Upload report.pdf
    System->>Session: Store PDF text
    System->>User: "What would you like me to do?"
    User->>System: "summary"
    System->>Session: Get stored PDF text
    System->>User: Here's the summary
```

**Session stores:**
- Extracted file content
- Conversation history
- Last intent

---

## File Processing Pipeline

```mermaid
flowchart LR
    Upload[File Upload] --> Type{File Type?}
    Type -->|PDF| PDF[Extract text]
    Type -->|Image| OCR[Run OCR]
    Type -->|Audio| Audio[Transcribe]
    Type -->|YouTube| YT[Get transcript]
    
    PDF --> Store[Store in session]
    OCR --> Store
    Audio --> Store
    YT --> Store
    
    Store --> Planner[Send to Planner]
```

---

## Technology Stack

```mermaid
graph TB
    subgraph Frontend
        HTML[HTML Form]
    end
    
    subgraph Backend
        FastAPI[FastAPI Server]
        LangGraph[LangGraph Orchestration]
    end
    
    subgraph Agents
        Planner[Planner: llama-3.1-70b]
        Executor[Executor: llama-3.1-8b]
    end
    
    subgraph Tools
        PDF[PyPDF2/pdfplumber]
        OCR[Tesseract/EasyOCR]
        Audio[Groq Whisper]
        YouTube[YouTube Transcript API]
    end
    
    Frontend --> Backend
    Backend --> Agents
    Agents --> Tools
```

---

## Why This Architecture?

### ✅ Two Separate Agents (Bonus Points)
- **Planner** - Smart, slow (70B model) - understands intent
- **Executor** - Fast, efficient (8B model) - does work

### ✅ LangGraph for Transparency
- Every request has execution trace
- Easy to debug
- Shows exactly what happened

### ✅ Session Persistence
- Remembers uploaded files
- Multi-turn conversations work
- No need to re-upload

### ✅ Graceful Fallbacks
- PDF fails? Try another tool
- OCR confidence low? Try EasyOCR
- LLM fails? Return helpful error

---

## Execution Trace Example

Every request shows what happened:

```json
{
  "trace": [
    "agent_start",
    "input_processing_start",
    "input_processing_complete_type_pdf",
    "planner_start",
    "planner_ready_to_execute_intent_summarization",
    "executor_start",
    "executor_success_task_summarization",
    "format_response_complete"
  ]
}
```

**This trace proves:**
1. PDF was processed successfully
2. Planner understood the intent (summarization)
3. Executor completed the task
4. Response was formatted correctly
