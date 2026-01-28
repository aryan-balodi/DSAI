"""
Planner Agent: Analyzes user intent and decides execution strategy.

Key responsibilities:
1. Determine user's goal from extracted content
2. Calculate confidence score for intent classification
3. Generate clarification questions when confidence < 0.7
4. Create execution plans for the Executor Agent

Design: Uses Groq LLM with structured prompts and few-shot examples
to avoid generic AI-generated patterns.
"""
from typing import Dict, Any, Optional, Tuple, List
from groq import Groq
import json
import re

from src.utils.config import settings
from src.state.conversation_manager import conversation_manager


def extract_youtube_url(text: str) -> Optional[str]:
    """Extract YouTube URL from text using regex."""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, text)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return None


class IntentType:
    """Supported task intents."""
    SUMMARIZE = "summarize"
    SENTIMENT = "sentiment_analysis"
    CODE_EXPLAIN = "code_explanation"
    EXTRACT = "text_extraction"
    YOUTUBE = "youtube_transcript"
    QUESTION_ANSWER = "question_answer"
    GENERAL_CHAT = "general_chat"
    AUDIO_TRANSCRIBE_SUMMARIZE = "audio_transcribe_summarize" 


class PlannerAgent:
    """
    Planner Agent for intent analysis and execution planning.
    
    Confidence threshold: 0.7
    - >= 0.7: Proceed with execution
    - < 0.7: Ask clarification question
    
    Special case: Audio files automatically trigger transcription + summarization
    """
    
    CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.planner_model
    
    def analyze(
        self,
        user_input: str,
        session_id: str,
        extracted_content: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None  # NEW: to detect audio
    ) -> Dict[str, Any]:
        """
        Analyze user intent and decide next action.
        
        Args:
            user_input: User's text input or request
            session_id: Conversation session ID
            extracted_content: Content extracted from files
            input_metadata: Metadata about input type (to detect audio)
        
        Returns:
            {
                'action': 'execute' | 'clarify',
                'intent': str,
                'confidence': float,
                'plan': {...} or None,
                'clarification_question': str or None,
                'reasoning': str
            }
        """
        # SPECIAL CASE: Audio files auto-transcribe and summarize
        # Assignment requirement: "Audio → Speech-to-Text + cleanup + summarize"
        if input_metadata and input_metadata.get('type') == 'audio':
            return self._handle_audio_input(user_input, extracted_content, input_metadata)
        
        # Get conversation context
        session = conversation_manager.get_session(session_id)
        context = conversation_manager.get_conversation_context(session_id)
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            user_input=user_input,
            extracted_content=extracted_content,
            conversation_context=context
        )
        
        # Call LLM for intent analysis
        response = self._call_llm(prompt)
        
        # Parse structured response
        analysis = self._parse_analysis(response)
        
        # Decide action based on confidence
        if analysis['confidence'] >= self.CONFIDENCE_THRESHOLD:
            # High confidence - create execution plan
            plan = self._create_execution_plan(
                intent=analysis['intent'],
                user_input=user_input,
                extracted_content=extracted_content
            )
            
            return {
                'action': 'execute',
                'intent': analysis['intent'],
                'confidence': analysis['confidence'],
                'plan': plan,
                'clarification_question': None,
                'reasoning': analysis['reasoning']
            }
        else:
            # Low confidence - ask for clarification
            # Check if clarification is still allowed
            if not conversation_manager.should_allow_clarification(session_id):
                # Max attempts reached, default to summarization
                return self._default_to_summarize(user_input, extracted_content)
            
            question = self._generate_clarification_question(
                analysis=analysis,
                user_input=user_input
            )
            
            conversation_manager.increment_clarification(session_id)
            
            return {
                'action': 'clarify',
                'intent': analysis.get('possible_intents', [None])[0],
                'confidence': analysis['confidence'],
                'plan': None,
                'clarification_question': question,
                'reasoning': analysis['reasoning']
            }
    
    def _handle_audio_input(
        self,
        user_input: str,
        extracted_content: Optional[str],
        input_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle audio input with automatic transcription + summarization.
        
        Assignment requirement: Audio files → transcribe + summarize (3 formats)
        High confidence because this is a defined workflow.
        """
        # Get file path from metadata
        file_path = input_metadata.get('path') if input_metadata else None
        
        plan = {
            'task': IntentType.AUDIO_TRANSCRIBE_SUMMARIZE,
            'input': file_path or user_input,
            'user_query': user_input,
            'parameters': {
                'transcribe': True,
                'summarize': True,
                'formats': ['one_line', 'three_bullets', 'five_sentence'],
                'include_duration': True,
                'file_path': file_path
            }
        }
        
        return {
            'action': 'execute',
            'intent': IntentType.AUDIO_TRANSCRIBE_SUMMARIZE,
            'confidence': 0.95,  # High confidence for defined workflow
            'plan': plan,
            'clarification_question': None,
            'reasoning': 'Audio file detected - automatic transcription and summarization'
        }
    
    def _build_analysis_prompt(
        self,
        user_input: str,
        extracted_content: Optional[str],
        conversation_context: str
    ) -> str:
        """Build prompt for intent analysis with few-shot examples."""
        
        # Combine input and extracted content
        content_to_analyze = user_input
        if extracted_content:
            content_to_analyze = f"User request: {user_input}\n\nExtracted content:\n{extracted_content}"
        
        prompt = f"""You are an intent classifier for an agentic system. Analyze the user's request and determine their goal.

SUPPORTED TASKS:
- summarize: User wants a summary (1-line, three_bullets, 5-sentence format)
- sentiment_analysis: Analyze emotional tone/sentiment
- code_explanation: Explain code, find bugs, analyze complexity
- text_extraction: Just extract/transcribe text from files
- youtube_transcript: Fetch YouTube video transcript
- question_answer: Answer specific questions about content
- general_chat: Casual conversation, greetings, help requests

IMPORTANT RULES:
1. If user request is ambiguous (e.g., "analyze", "check this", "do something"), return confidence < 0.5
2. If multiple tasks are equally plausible, list them in possible_intents and return confidence < 0.7
3. Only return high confidence (>0.7) if the request EXPLICITLY mentions the task
4. "Analyze" without context is ALWAYS ambiguous - could be sentiment, summary, or other tasks

FEW-SHOT EXAMPLES:

Example 1:
Input: "Summarize this article"
Output: {{"intent": "summarize", "confidence": 0.95, "reasoning": "Explicit request to summarize"}}

Example 2:
Input: "What's the sentiment here?"
Output: {{"intent": "sentiment_analysis", "confidence": 0.9, "reasoning": "Direct sentiment question"}}

Example 3:
Input: "Explain this" [with code snippet extracted]
Output: {{"intent": "code_explanation", "confidence": 0.85, "reasoning": "Code content with explain request"}}

Example 4:
Input: "What does this say?" [with image]
Output: {{"intent": "text_extraction", "confidence": 0.8, "reasoning": "Simple extraction request"}}

Example 5:
Input: "Analyze this text"
Output: {{"intent": "unclear", "confidence": 0.3, "possible_intents": ["sentiment_analysis", "summarize"], "reasoning": "Ambiguous request - 'analyze' could mean sentiment, summary, or other tasks"}}

Example 6:
Input: "What are the action items from this meeting?"
Output: {{"intent": "question_answer", "confidence": 0.9, "reasoning": "Specific extraction question about action items"}}

CONVERSATION CONTEXT:
{conversation_context if conversation_context else "No prior context"}

USER REQUEST TO ANALYZE:
{content_to_analyze}

Respond ONLY with valid JSON in this format:
{{
    "intent": "task_name or 'unclear'",
    "confidence": 0.0-1.0,
    "possible_intents": ["intent1", "intent2"],
    "reasoning": "brief explanation"
}}"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call Groq LLM for analysis."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower for more deterministic intent classification
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback for API errors
            return json.dumps({
                "intent": "unclear",
                "confidence": 0.2,
                "possible_intents": ["general_chat"],
                "reasoning": f"API error: {str(e)}"
            })
    
    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured analysis."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = json.loads(response)
            
            # Ensure required fields
            analysis.setdefault('confidence', 0.5)
            analysis.setdefault('reasoning', 'No reasoning provided')
            analysis.setdefault('possible_intents', [])
            
            return analysis
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                'intent': 'unclear',
                'confidence': 0.3,
                'possible_intents': [],
                'reasoning': 'Failed to parse LLM response'
            }
    
    def _create_execution_plan(
        self,
        intent: str,
        user_input: str,
        extracted_content: Optional[str]
    ) -> Dict[str, Any]:
        """Create execution plan for the Executor Agent."""
        
        content = extracted_content or user_input
        
        plan = {
            'task': intent,
            'input': content,
            'user_query': user_input,
            'parameters': {}
        }
        
        # Add task-specific parameters
        if intent == IntentType.SUMMARIZE:
            plan['parameters'] = {
                'formats': ['one_line', 'three_bullets', 'five_sentence']
            }
        elif intent == IntentType.SENTIMENT:
            plan['parameters'] = {
                'return_confidence': True,
                'return_justification': True
            }
        elif intent == IntentType.CODE_EXPLAIN:
            plan['parameters'] = {
                'detect_language': True,
                'find_bugs': True,
                'analyze_complexity': True
            }
        elif intent == IntentType.QUESTION_ANSWER:
            plan['parameters'] = {
                'question': user_input,
                'context': content
            }
        elif intent == IntentType.EXTRACT:
            # Simple text extraction - return cleaned text with metadata
            plan['parameters'] = {
                'confidence': 1.0,
                'clean_text': True
            }
        elif intent == IntentType.YOUTUBE:
            # Extract YouTube URL from input text
            extracted_url = extract_youtube_url(user_input)
            if not extracted_url:
                extracted_url = user_input.strip()  # Fallback if no URL found
            
            plan['parameters'] = {
                'url': extracted_url,
                'return_transcript': True,
                'include_timestamps': False
            }
        elif intent == IntentType.GENERAL_CHAT:
        # Conversational response
            plan['parameters'] = {
                'be_helpful': True,
                'context': content
            }
        
        return plan
    
    def _generate_clarification_question(
        self,
        analysis: Dict[str, Any],
        user_input: str
    ) -> str:
        """Generate a clarification question based on uncertain intent."""
        
        possible_intents = analysis.get('possible_intents', [])
        
        if len(possible_intents) >= 2:
            # Multiple possible intents
            intent_labels = {
                IntentType.SUMMARIZE: "a summary",
                IntentType.SENTIMENT: "sentiment analysis",
                IntentType.CODE_EXPLAIN: "code explanation",
                IntentType.QUESTION_ANSWER: "answer a specific question",
                IntentType.EXTRACT: "text extraction",
                IntentType.YOUTUBE: "fetch YouTube transcript",
                IntentType.GENERAL_CHAT: "have a conversation"
            }
            
            options = [intent_labels.get(i, i) for i in possible_intents[:3]]
            
            if len(options) == 2:
                return f"Would you like {options[0]} or {options[1]}?"
            else:
                options_str = ", ".join(options[:-1]) + f", or {options[-1]}"
                return f"What would you like me to do: {options_str}?"
        
        # Generic unclear request
        return "What would you like me to do with this content? (e.g., summarize, analyze sentiment, explain code," \
        "answer your questions, extract text, or transcribe the video?)"
    
    def _default_to_summarize(
        self,
        user_input: str,
        extracted_content: Optional[str]
    ) -> Dict[str, Any]:
        """
        Default to summarization after max clarification attempts.
        Safety fallback to avoid stuck conversations.
        """
        plan = self._create_execution_plan(
            intent=IntentType.SUMMARIZE,
            user_input=user_input,
            extracted_content=extracted_content
        )
        
        return {
            'action': 'execute',
            'intent': IntentType.SUMMARIZE,
            'confidence': 0.6,
            'plan': plan,
            'clarification_question': None,
            'reasoning': 'Defaulting to summarization after max clarification attempts'
        }


# Global instance
planner_agent = PlannerAgent()