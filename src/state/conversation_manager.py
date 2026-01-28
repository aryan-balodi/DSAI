"""
Conversation state management for multi-turn interactions.
Tracks user sessions, extracted content, and clarification attempts.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Message:
    """Represents a single message in conversation history."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Stores complete conversation state for a session."""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    extracted_content: Optional[str] = None
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    clarification_count: int = 0
    current_intent: Optional[str] = None
    intent_confidence: float = 0.0
    last_plan: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ConversationManager:
    """
    Manages conversation sessions with clarification tracking.
    
    Design decisions:
    - In-memory storage (simple, fast, suitable for demo)
    - Max 2 clarification attempts to prevent loops
    - Persistent extracted content for follow-up questions
    """
    
    MAX_CLARIFICATION_ATTEMPTS = 2
    
    def __init__(self):
        self._sessions: Dict[str, ConversationState] = {}
    
    def create_session(self) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ConversationState(session_id=session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Retrieve session by ID."""
        return self._sessions.get(session_id)
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add message to conversation history."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        session.messages.append(message)
        session.updated_at = datetime.now()
    
    def store_extracted_content(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store extracted content from files for context."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.extracted_content = content
        session.extraction_metadata = metadata
        session.updated_at = datetime.now()
    
    def increment_clarification(self, session_id: str) -> int:
        """
        Increment clarification attempt counter.
        Returns current count after increment.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.clarification_count += 1
        session.updated_at = datetime.now()
        return session.clarification_count
    
    def should_allow_clarification(self, session_id: str) -> bool:
        """
        Check if another clarification attempt is allowed.
        Prevents infinite clarification loops.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        return session.clarification_count < self.MAX_CLARIFICATION_ATTEMPTS
    
    def update_intent(
        self,
        session_id: str,
        intent: str,
        confidence: float
    ) -> None:
        """Update current intent and confidence."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.current_intent = intent
        session.intent_confidence = confidence
        session.updated_at = datetime.now()
    
    def store_plan(self, session_id: str, plan: Dict[str, Any]) -> None:
        """Store the execution plan from Planner."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.last_plan = plan
        session.updated_at = datetime.now()
    
    def get_conversation_context(self, session_id: str) -> str:
        """
        Build conversation context string for LLM.
        Includes recent messages and extracted content.
        """
        session = self.get_session(session_id)
        if not session:
            return ""
        
        context_parts = []
        
        # Add extracted content if available
        if session.extracted_content:
            source = session.extraction_metadata.get("source", "file")
            context_parts.append(f"[Extracted from {source}]:\n{session.extracted_content}\n")
        
        # Add recent messages (last 5 for context window management)
        recent_messages = session.messages[-5:]
        for msg in recent_messages:
            context_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def delete_session(self, session_id: str) -> None:
        """Remove session from storage."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# Global instance
conversation_manager = ConversationManager()