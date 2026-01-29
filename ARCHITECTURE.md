# 🏗️ Architecture Diagram

## System Architecture Overview

```mermaid
graph TB
    User[👤 User] -->|Text/File + Message| UI[🖥️ Frontend UI<br/>index.html]
    UI -->|POST /process| API[⚡ FastAPI Server<br/>src/api/main.py]
    
    API -->|Create AgentState| Graph[🔄 LangGraph Orchestrator<br/>agent_graph.py]
    
    Graph --> InputNode[📥 Input Processing Node]
    InputNode -->|Detect Type| Processor[🔍 Input Processor<br/>input_processor.py]
    
    Processor -->|PDF| PDFTool[📄 PDF Tool<br/>PyPDF2→pdfplumber→OCR]
    Processor -->|Image| OCRTool[🖼️ OCR Tool<br/>Tesseract→EasyOCR]
    Processor -->|Audio| AudioTool[🎵 Audio Tool<br/>Groq Whisper]
    Processor -->|YouTube| YTTool[▶️ YouTube Tool<br/>youtube-transcript-api]
    Processor -->|Text| TextProc[📝 Direct Text]
    
    PDFTool -->|Extracted Text| Session[(💾 Session Manager<br/>conversation_manager.py)]
    OCRTool -->|Extracted Text| Session
    AudioTool -->|Transcript| Session
    YTTool -->|Transcript| Session
    TextProc -->|Raw Text| Session
    
    InputNode -->|State + Content| PlannerNode[🧠 Planner Node]
    PlannerNode -->|Analyze Intent| Planner[🎯 Planner Agent<br/>llama-3.1-70b-versatile]
    
    Planner -->|Confidence < 0.7| Clarify{❓ Need<br/>Clarification?}
    Clarify -->|Yes| Response[📤 Return Clarification]
    Response --> UI
    
    Clarify -->|No| ExecutorNode[⚙️ Executor Node]
    ExecutorNode -->|Execute Task| Executor[🔨 Executor Agent<br/>llama-3.1-8b-instant]
    
    Executor -->|Summarization| SumTask[📊 Summarize<br/>3 Formats]
    Executor -->|Sentiment| SentTask[😊 Sentiment<br/>Label+Confidence]
    Executor -->|Code Explain| CodeTask[💻 Code Analysis<br/>Bugs+Complexity]
    Executor -->|Conversational| ConvTask[💬 Q&A Response]
    Executor -->|Audio Summary| AudioTask[🎧 Transcribe+Summarize]
    Executor -->|YouTube| YTTask[📹 Fetch+Summarize]
    Executor -->|Extract| ExtractTask[📋 Text Extraction]
    
    SumTask --> FormatNode[📝 Format Response Node]
    SentTask --> FormatNode
    CodeTask --> FormatNode
    ConvTask --> FormatNode
    AudioTask --> FormatNode
    YTTask --> FormatNode
    ExtractTask --> FormatNode
    
    FormatNode -->|Structured JSON| API
    API -->|Response| UI
    UI -->|Display Result| User
    
    style User fill:#e1f5ff
    style UI fill:#fff3cd
    style API fill:#d4edda
    style Graph fill:#f8d7da
    style Planner fill:#d1ecf1
    style Executor fill:#d1ecf1
    style Session fill:#e2e3e5
    style Clarify fill:#fff3cd
```

## Detailed Component Flow

### 1️⃣ Input Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant InputProcessor
    participant Tools
    participant SessionManager
    
    User->>Frontend: Upload file + message
    Frontend->>FastAPI: POST /process (multipart/form-data)
    FastAPI->>FastAPI: Save temp file
    FastAPI->>InputProcessor: detect_input_type()
    
    alt File Type: PDF
        InputProcessor->>Tools: extract_pdf()
        Tools-->>InputProcessor: {text, pages, tokens}
    else File Type: Image
        InputProcessor->>Tools: extract_text_from_image()
        Tools-->>InputProcessor: {text, confidence}
    else File Type: Audio
        InputProcessor->>Tools: transcribe_audio()
        Tools-->>InputProcessor: {transcript, duration}
    else File Type: YouTube URL
        InputProcessor->>Tools: fetch_youtube_transcript()
        Tools-->>InputProcessor: {transcript, video_id}
    else File Type: Text
        InputProcessor->>InputProcessor: Use raw text
    end
    
    InputProcessor->>SessionManager: Store extracted content
    SessionManager-->>InputProcessor: Content stored
    InputProcessor-->>FastAPI: {input_type, extracted_content, metadata}
```

### 2️⃣ Planning & Decision Flow

```mermaid
sequenceDiagram
    participant InputNode
    participant PlannerNode
    participant PlannerAgent
    participant GroqLLM
    participant ExecutorNode
    participant User
    
    InputNode->>PlannerNode: AgentState with content
    PlannerNode->>PlannerAgent: analyze(user_input, extracted_content)
    
    PlannerAgent->>PlannerAgent: Check auto-detection<br/>(audio/YouTube)
    
    alt Auto-detected (audio/YouTube)
        PlannerAgent-->>PlannerNode: {intent, confidence: 0.95, parameters}
    else Requires LLM analysis
        PlannerAgent->>GroqLLM: Analyze intent<br/>(llama-3.1-70b-versatile)
        GroqLLM-->>PlannerAgent: {intent, confidence, reasoning}
    end
    
    PlannerNode->>PlannerNode: Check confidence score
    
    alt Confidence < 0.7
        PlannerNode-->>User: Return clarification question
    else Confidence >= 0.7
        PlannerNode->>ExecutorNode: Execute plan
    end
```

### 3️⃣ Execution Flow

```mermaid
sequenceDiagram
    participant ExecutorNode
    participant ExecutorAgent
    participant GroqLLM
    participant Tools
    participant FormatNode
    
    ExecutorNode->>ExecutorAgent: execute(plan)
    ExecutorAgent->>ExecutorAgent: Route to task handler
    
    alt Task: Summarization
        ExecutorAgent->>GroqLLM: Generate summary (3 formats)
        GroqLLM-->>ExecutorAgent: {one_line, three_bullets, five_sentence}
    else Task: Sentiment
        ExecutorAgent->>GroqLLM: Analyze sentiment
        GroqLLM-->>ExecutorAgent: {label, confidence, justification}
    else Task: Code Explanation
        ExecutorAgent->>GroqLLM: Explain code
        GroqLLM-->>ExecutorAgent: {language, explanation, bugs, complexity}
    else Task: Audio Transcribe+Summary
        ExecutorAgent->>Tools: Already transcribed in input processing
        ExecutorAgent->>GroqLLM: Summarize transcript
        GroqLLM-->>ExecutorAgent: {summary, duration, language}
    else Task: YouTube
        ExecutorAgent->>Tools: fetch_youtube_transcript()
        Tools-->>ExecutorAgent: {transcript}
        ExecutorAgent->>GroqLLM: Summarize if requested
        GroqLLM-->>ExecutorAgent: {summary}
    else Task: Conversational
        ExecutorAgent->>GroqLLM: Answer question
        GroqLLM-->>ExecutorAgent: {response}
    end
    
    ExecutorAgent->>ExecutorAgent: Parse JSON response
    ExecutorAgent-->>ExecutorNode: Structured result
    ExecutorNode->>FormatNode: Format for user
    FormatNode-->>ExecutorNode: Final response
```

## State Management

### AgentState Schema

```mermaid
classDiagram
    class AgentState {
        +string session_id
        +string user_input
        +string file_path
        +string file_type
        +string input_type
        +dict input_metadata
        +string extracted_content
        +dict planner_result
        +bool needs_clarification
        +string clarification_question
        +dict executor_result
        +dict final_response
        +string error
        +list trace
    }
    
    class ConversationState {
        +string session_id
        +datetime created_at
        +datetime last_active
        +list messages
        +string extracted_content
        +dict extraction_metadata
        +string last_intent
    }
    
    AgentState --> ConversationState: Managed by
```

## LangGraph State Transitions

```mermaid
stateDiagram-v2
    [*] --> InputProcessing: User request
    
    InputProcessing --> CheckSession: Load session
    CheckSession --> ExtractContent: New file
    CheckSession --> ReuseContent: Follow-up (no file)
    
    ExtractContent --> Planner: Content extracted
    ReuseContent --> Planner: Using stored content
    
    Planner --> AnalyzeIntent: Get intent
    
    AnalyzeIntent --> CheckConfidence: Intent analyzed
    
    CheckConfidence --> Clarification: confidence < 0.7
    CheckConfidence --> Executor: confidence >= 0.7
    
    Clarification --> [*]: Return question
    
    Executor --> RouteTask: Route based on intent
    
    RouteTask --> Summarization: intent=summarization
    RouteTask --> Sentiment: intent=sentiment_analysis
    RouteTask --> CodeExplain: intent=code_explanation
    RouteTask --> Conversational: intent=conversational
    RouteTask --> AudioProcess: intent=audio_transcribe_summarize
    RouteTask --> YouTubeProcess: intent=youtube_transcript
    RouteTask --> Extract: intent=extract_text
    
    Summarization --> FormatResponse
    Sentiment --> FormatResponse
    CodeExplain --> FormatResponse
    Conversational --> FormatResponse
    AudioProcess --> FormatResponse
    YouTubeProcess --> FormatResponse
    Extract --> FormatResponse
    
    FormatResponse --> [*]: Return result
```

## Technology Stack Diagram

```mermaid
graph LR
    subgraph Frontend
        HTML[HTML5]
        CSS[CSS3]
        JS[JavaScript ES6]
    end
    
    subgraph Backend
        FastAPI[FastAPI]
        Uvicorn[Uvicorn ASGI]
    end
    
    subgraph Orchestration
        LangGraph[LangGraph]
        LangChain[LangChain]
    end
    
    subgraph Agents
        Planner[Planner Agent<br/>llama-3.1-70b]
        Executor[Executor Agent<br/>llama-3.1-8b]
    end
    
    subgraph External_APIs
        Groq[Groq API<br/>LLM + Whisper]
        YouTube[YouTube Transcript API]
    end
    
    subgraph Tools
        PyPDF[PyPDF2]
        PDFPlumber[pdfplumber]
        Tesseract[pytesseract]
        EasyOCR[EasyOCR]
        PDF2Image[pdf2image]
    end
    
    subgraph Storage
        Memory[In-Memory<br/>Session Store]
        TempFiles[Temp Files<br/>/tmp]
    end
    
    Frontend --> Backend
    Backend --> Orchestration
    Orchestration --> Agents
    Agents --> External_APIs
    Agents --> Tools
    Backend --> Storage
    
    style Frontend fill:#e3f2fd
    style Backend fill:#e8f5e9
    style Orchestration fill:#fff3e0
    style Agents fill:#f3e5f5
    style External_APIs fill:#fce4ec
    style Tools fill:#e0f2f1
    style Storage fill:#f1f8e9
```

## File Upload & Processing Pipeline

```mermaid
flowchart TD
    Start([User Upload]) --> Check{File Type?}
    
    Check -->|.pdf| PDF[PDF Extraction Pipeline]
    Check -->|.jpg/.png| Image[Image OCR Pipeline]
    Check -->|.mp3/.wav/.m4a| Audio[Audio Transcription Pipeline]
    Check -->|YouTube URL| YouTube[YouTube Fetch Pipeline]
    Check -->|Plain text| Text[Direct Processing]
    
    PDF --> PDF1[1. Try PyPDF2]
    PDF1 -->|Success| Store[Store in Session]
    PDF1 -->|Fail| PDF2[2. Try pdfplumber]
    PDF2 -->|Success| Store
    PDF2 -->|Fail| PDF3[3. Try OCR]
    PDF3 --> Store
    
    Image --> OCR1[1. Try Tesseract]
    OCR1 -->|Confidence > 0.7| Store
    OCR1 -->|Confidence < 0.7| OCR2[2. Try EasyOCR]
    OCR2 --> Store
    
    Audio --> Size{File Size?}
    Size -->|< 25MB| Whisper[Groq Whisper API]
    Size -->|>= 25MB| Error1[Return Error]
    Whisper --> Store
    
    YouTube --> YT1[Extract Video ID]
    YT1 --> YT2[Fetch Transcript]
    YT2 --> Store
    
    Text --> Store
    
    Store --> Planner[Continue to Planner]
    Error1 --> End([Return Error])
    
    style Start fill:#81c784
    style End fill:#e57373
    style Store fill:#64b5f6
    style Planner fill:#ba68c8
```

## Clarification Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant System
    participant Session
    participant Planner
    
    User->>System: Upload file.pdf + "do it"
    System->>Session: Store extracted PDF content
    System->>Planner: Analyze intent
    Planner->>Planner: Confidence = 0.3 (too low)
    Planner-->>User: "What would you like me to do?<br/>- Summarize<br/>- Sentiment analysis"
    
    Note over Session: PDF content stored
    
    User->>System: "summary" (no file uploaded)
    System->>Session: Check for stored content
    Session-->>System: Return stored PDF content
    System->>Planner: Analyze "summary" + stored content
    Planner->>Planner: Confidence = 0.95 (high)
    Planner-->>System: Execute summarization
    System-->>User: Summary of PDF
```

## Error Handling Flow

```mermaid
flowchart TD
    Request[Incoming Request] --> Validate{Valid Input?}
    
    Validate -->|No| Error1[Return 400 Error]
    Validate -->|Yes| Process[Process Input]
    
    Process --> Extract{Extract Content}
    
    Extract -->|Fail| Retry{Retry with<br/>Fallback?}
    Retry -->|Yes| Fallback[Use Fallback Tool]
    Retry -->|No| Error2[Return Extraction Error]
    
    Extract -->|Success| Plan[Planner Analysis]
    Fallback --> Plan
    
    Plan --> Confidence{Confidence<br/>Check}
    
    Confidence -->|Low| Clarify[Ask Clarification]
    Confidence -->|High| Execute[Execute Task]
    
    Execute --> LLM{LLM Call}
    LLM -->|Fail| Error3[Return LLM Error]
    LLM -->|Success| Parse{Parse JSON}
    
    Parse -->|Fail| Fallback2[Use Fallback Response]
    Parse -->|Success| Success[Return Result]
    
    Fallback2 --> Success
    
    Error1 --> Cleanup[Cleanup Temp Files]
    Error2 --> Cleanup
    Error3 --> Cleanup
    Clarify --> Cleanup
    Success --> Cleanup
    
    Cleanup --> End([Response to User])
    
    style Error1 fill:#ef5350
    style Error2 fill:#ef5350
    style Error3 fill:#ef5350
    style Success fill:#66bb6a
    style Clarify fill:#ffb74d
```

---

## Key Design Decisions

### 1. Multi-Agent Separation
- **Planner (llama-3.1-70b):** Better reasoning, intent analysis
- **Executor (llama-3.1-8b):** Faster execution, structured outputs
- **Why:** Separation of concerns, bonus points, better accuracy

### 2. LangGraph vs Custom Loop
- **Chosen:** LangGraph StateGraph
- **Why:** Explicit state transitions, built-in tracing, required for explainability scoring

### 3. In-Memory Session Storage
- **Chosen:** Python dict in memory
- **Why:** Simple, fast, sufficient for demo/assignment
- **Production:** Would use Redis/PostgreSQL

### 4. Three-Tier PDF Extraction
- **PyPDF2 → pdfplumber → OCR**
- **Why:** Maximizes success rate across different PDF types

### 5. Confidence-Based Clarification
- **Threshold:** 0.7
- **Why:** Balance between over-asking and wrong assumptions

---

## Execution Trace Example

Every request includes a trace showing the path through the system:

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
    "format_response_start",
    "format_response_complete"
  ]
}
```

This provides **explainability** required by the rubric.
