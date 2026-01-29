"""
FastAPI Backend for Agentic Application

Simple REST API with:
- POST /process - Main endpoint for processing text/files
- GET /health - Health check
- Session-based clarification flow (no WebSockets needed)
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
import tempfile
import shutil
from pathlib import Path

# Import our orchestration layer
from src.orchestration.agent_graph import run_agent
from src.state.conversation_manager import conversation_manager

app = FastAPI(
    title="Agentic Application API",
    description="Multi-agent system for text/file processing with clarification support",
    version="1.0.0"
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    """Request model for text-only processing."""
    session_id: Optional[str] = None
    message: str


class ProcessResponse(BaseModel):
    """Response model for all processing requests."""
    status: str  # 'success', 'needs_clarification', 'error'
    session_id: str
    result: Optional[Dict[str, Any]] = None
    clarification_question: Optional[str] = None
    error: Optional[str] = None
    trace: Optional[list] = None


@app.get("/")
async def root():
    """Serve the frontend HTML."""
    html_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {
        "message": "Agentic Application API",
        "version": "1.0.0",
        "endpoints": {
            "POST /process": "Process text input with optional file upload",
            "GET /health": "Health check",
            "GET /session/{session_id}": "Get session info"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api": "running",
        "agents": "ready"
    }


@app.post("/process", response_model=ProcessResponse)
async def process_input(
    message: str = Form(""),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Main processing endpoint.
    
    Handles:
    - Text-only input
    - File uploads (PDF, images, audio)
    - Session-based clarification flow
    
    Args:
        message: User's text input
        session_id: Optional session ID for multi-turn conversations
        file: Optional file upload
    
    Returns:
        ProcessResponse with status and results
    """
    # Generate or use existing session ID
    if not session_id:
        session_id = str(uuid.uuid4())
    
    file_path = None
    temp_file_path = None
    
    try:
        # Handle file upload if present
        if file:
            # Validate file type
            filename = file.filename.lower()
            allowed_extensions = {
                '.pdf', '.jpg', '.jpeg', '.png', '.mp3'
            }
            
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
                )
            
            # Save uploaded file to temp location
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"{session_id}_{filename}")
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_path = temp_file_path
        
        # Run agent orchestration
        result = run_agent(
            user_input=message,
            file_path=file_path,
            session_id=session_id
        )
        
        # Determine response status based on result type
        result_type = result.get('type')
        
        if result_type == 'clarification':
            return ProcessResponse(
                status='needs_clarification',
                session_id=session_id,
                clarification_question=result.get('question'),
                trace=result.get('trace', [])
            )
        
        elif result_type == 'error':
            return ProcessResponse(
                status='error',
                session_id=session_id,
                error=result.get('error'),
                trace=result.get('trace', [])
            )
        
        elif result_type == 'result':
            return ProcessResponse(
                status='success',
                session_id=session_id,
                result=result.get('result'),
                trace=result.get('trace', [])
            )
        
        else:
            return ProcessResponse(
                status='error',
                session_id=session_id,
                error=f"Unknown result type: {result_type}",
                trace=result.get('trace', [])
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        # Log error and return user-friendly message
        import traceback
        traceback.print_exc()
        
        return ProcessResponse(
            status='error',
            session_id=session_id,
            error=f"Internal server error: {str(e)}"
        )
    
    finally:
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass  # Best effort cleanup


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a session.
    
    Useful for debugging and viewing conversation history.
    """
    session = conversation_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "message_count": len(session.messages),
        "clarification_count": session.clarification_count,
        "has_extracted_content": bool(session.extracted_content),
        "intent": session.intent,
        "confidence": session.confidence
    }


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session (useful for testing)."""
    if session_id in conversation_manager.sessions:
        del conversation_manager.sessions[session_id]
        return {"status": "cleared", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
