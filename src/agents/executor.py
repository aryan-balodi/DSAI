"""
Executor Agent: Executes tasks based on plans from the Planner Agent.

Key responsibilities:
1. Receive execution plan from Planner
2. Route to appropriate tool based on task type
3. Execute task and return structured results
4. Handle errors with fallbacks and partial results

Design: Uses faster Groq model (llama-3.1-8b-instant) for execution tasks.
Separates concerns - Planner thinks, Executor does.
"""
from typing import Dict, Any, Optional
from groq import Groq
import json

from src.utils.config import settings
from src.agents.planner import IntentType


class ExecutorAgent:
    """
    Executor Agent for task execution.
    
    Receives plans from Planner and invokes appropriate tools.
    Each task returns structured output matching assignment requirements.
    """
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.executor_model  # Faster model for execution
    
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task based on the plan from Planner.
        
        Args:
            plan: {
                'task': str,
                'input': str,
                'user_query': str,
                'parameters': Dict
            }
        
        Returns:
            {
                'success': bool,
                'task': str,
                'result': Any,
                'metadata': Dict,
                'error': str or None
            }
        """
        # INPUT VALIDATION
        if not plan:
            return {
                'success': False,
                'task': 'unknown',
                'result': None,
                'metadata': {},
                'error': 'Plan is None or empty'
            }
        
        if 'task' not in plan:
            return {
                'success': False,
                'task': 'unknown',
                'result': None,
                'metadata': {},
                'error': 'Plan missing required field: task'
            }
        
        task = plan.get('task')
        task_input = plan.get('input', '')
        parameters = plan.get('parameters', {})
        
        # Validate required input for certain tasks
        if task in [IntentType.SUMMARIZE, IntentType.SENTIMENT, IntentType.CODE_EXPLAIN]:
            if not task_input or not isinstance(task_input, str):
                return {
                    'success': False,
                    'task': task,
                    'result': None,
                    'metadata': {},
                    'error': f'Task {task} requires non-empty text input'
                }
        
        try:
            # Route to appropriate task handler
            if task == IntentType.SUMMARIZE:
                result = self._execute_summarization(task_input, parameters)
            elif task == IntentType.SENTIMENT:
                result = self._execute_sentiment_analysis(task_input, parameters)
            elif task == IntentType.CODE_EXPLAIN:
                result = self._execute_code_explanation(task_input, parameters)
            elif task == IntentType.EXTRACT:
                result = self._execute_text_extraction(task_input, parameters)
            elif task == IntentType.YOUTUBE:
                result = self._execute_youtube_transcript(parameters)
            elif task == IntentType.QUESTION_ANSWER:
                result = self._execute_question_answer(task_input, parameters)
            elif task == IntentType.GENERAL_CHAT:
                result = self._execute_general_chat(task_input, parameters)
            elif task == IntentType.AUDIO_TRANSCRIBE_SUMMARIZE:
                result = self._execute_audio_transcribe_summarize(task_input, parameters)
            else:
                return {
                    'success': False,
                    'task': task,
                    'result': None,
                    'metadata': {},
                    'error': f'Unknown task type: {task}'
                }
            
            return {
                'success': True,
                'task': task,
                'result': result,
                'metadata': {'model_used': self.model},
                'error': None
            }
        
        except Exception as e:
            # Graceful error handling - return partial results if possible
            return {
                'success': False,
                'task': task,
                'result': None,
                'metadata': {'error_type': type(e).__name__},
                'error': str(e)
            }
    
    def _execute_summarization(
        self,
        content: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assignment requirement: 1-line + 3 bullets + 5-sentence summary.
        
        Returns structured summary in all three formats.
        """
        formats = parameters.get('formats', ['one_line', 'three_bullets', 'five_sentence'])
        
        prompt = f"""Summarize the following content in exactly three formats:

1. ONE-LINE SUMMARY: A single concise sentence (max 20 words)
2. THREE BULLETS: Exactly 3 bullet points covering key points
3. FIVE-SENTENCE SUMMARY: Exactly 5 sentences providing comprehensive overview

Content to summarize:
{content}

Respond in this JSON format:
{{
    "one_line": "your one-line summary here",
    "three_bullets": [
        "first key point",
        "second key point",
        "third key point"
    ],
    "five_sentence": "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
}}"""
        
        response = self._call_llm(prompt, max_tokens=1500)
        
        try:
            # Clean response - sometimes LLM adds markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith('```'):
                # Remove markdown code blocks
                cleaned_response = cleaned_response.split('```')[1]
                if cleaned_response.startswith('json'):
                    cleaned_response = cleaned_response[4:]
                cleaned_response = cleaned_response.strip()
            
            summary = json.loads(cleaned_response)
            
            # Check if response is an error
            if summary.get('error'):
                return {
                    'one_line': 'Summary generation failed',
                    'three_bullets': ['LLM', 'call', 'failed'],
                    'five_sentence': summary.get('message', 'Unknown error')
                }
            
            return summary
        except json.JSONDecodeError:
            # Fallback parsing if LLM doesn't return valid JSON
            return {
                'one_line': 'Summary generation failed',
                'three_bullets': ['Unable to parse', 'LLM response', 'as JSON'],
                'five_sentence': response[:500] if response else 'No summary generated'
            }
    
    def _execute_sentiment_analysis(
        self,
        content: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assignment requirement: Label + confidence + justification.
        """
        prompt = f"""Analyze the sentiment of the following content.

Content:
{content}

Respond in this JSON format:
{{
    "label": "positive|negative|neutral|mixed",
    "confidence": 0.0-1.0,
    "justification": "one-line explanation of why this sentiment"
}}"""
        
        response = self._call_llm(prompt, max_tokens=300)
        
        try:
            sentiment = json.loads(response)
            # Ensure confidence is a float
            sentiment['confidence'] = float(sentiment.get('confidence', 0.5))
            return sentiment
        except (json.JSONDecodeError, ValueError):
            # Fallback
            return {
                'label': 'neutral',
                'confidence': 0.5,
                'justification': 'Unable to analyze sentiment reliably'
            }
    
    def _execute_code_explanation(
        self,
        code: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assignment requirement: Explain code, detect bugs, mention time complexity.
        """
        prompt = f"""Analyze the following code and provide:
1. Programming language detection
2. Explanation of what the code does
3. Any bugs or issues found
4. Time complexity analysis

Code:
{code}

Respond in this JSON format:
{{
    "language": "detected language",
    "explanation": "clear explanation of what the code does",
    "bugs": ["bug 1", "bug 2"] or [] if no bugs,
    "time_complexity": "O(n) or similar notation with brief explanation"
}}"""
        
        response = self._call_llm(prompt, max_tokens=1000)
        
        try:
            analysis = json.loads(response)
            return analysis
        except json.JSONDecodeError:
            # Fallback
            return {
                'language': 'unknown',
                'explanation': response[:500] if response else 'Unable to explain code',
                'bugs': [],
                'time_complexity': 'Unable to determine'
            }
    
    def _execute_text_extraction(
        self,
        content: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simple text extraction - just return the content with metadata.
        Actual OCR happens in tools layer (Step 3).
        """
        return {
            'extracted_text': content,
            'confidence': parameters.get('confidence', 1.0),
            'cleaned': True
        }
    
    def _execute_youtube_transcript(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetch YouTube transcript and optionally summarize.
        
        Uses youtube_tool.py for transcript fetching.
        """
        url = parameters.get('url', '')
        summarize = parameters.get('summarize', False)
        
        # Validate URL format
        if not url or ('youtube.com' not in url.lower() and 'youtu.be' not in url.lower()):
            return {
                'url': url,
                'transcript': None,
                'success': False,
                'error': 'Invalid or missing YouTube URL'
            }
        
        try:
            # Import and use YouTube tool
            from src.tools.youtube_tool import fetch_youtube_transcript
            
            result = fetch_youtube_transcript(url)
            
            # Check if fetching succeeded
            if not result.get('success', False):
                return {
                    'url': url,
                    'video_id': result.get('video_id', 'unknown'),
                    'transcript': None,
                    'success': False,
                    'error': result.get('error', 'Unknown error fetching transcript')
                }
            
            transcript = result.get('transcript', '')
            video_id = result.get('video_id', 'unknown')
            duration = result.get('duration', 0)
            language = result.get('language', 'unknown')
            
            # If summarize requested, generate summary
            summary = None
            if summarize and transcript:
                summary_result = self._execute_summarize(
                    content=transcript,
                    parameters={'format': 'comprehensive'}
                )
                summary = summary_result.get('summary', {})
            
            return {
                'url': url,
                'video_id': video_id,
                'transcript': transcript,
                'summary': summary,
                'duration': duration,
                'language': language,
                'success': True,
                'error': None,
                'metadata': {
                    'transcript_length': len(transcript),
                    'word_count': len(transcript.split())
                }
            }
        
        except ImportError as e:
            return {
                'url': url,
                'transcript': None,
                'success': False,
                'error': f'YouTube tool not available: {str(e)}'
            }
        
        except Exception as e:
            return {
                'url': url,
                'transcript': None,
                'success': False,
                'error': f'Error processing YouTube URL: {str(e)}'
            }
    
    def _execute_question_answer(
        self,
        content: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Answer specific questions about content.
        Uses RAG if content is large (handled in orchestration layer).
        """
        question = parameters.get('question', '')
        context = parameters.get('context', content)
        
        prompt = f"""Answer the following question based on the provided context.
Be specific and concise.

Question: {question}

Context:
{context}

Provide a clear, direct answer:"""
        
        response = self._call_llm(prompt, max_tokens=500)
        
        return {
            'question': question,
            'answer': response.strip(),
            'context_used': len(context)
        }
    
    def _execute_general_chat(
        self,
        user_input: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assignment requirement: Friendly, helpful conversational response.
        """
        context = parameters.get('context', '')
        
        prompt = f"""You are a helpful AI assistant. Respond to the user in a friendly, conversational way.

User: {user_input}

{"Additional context: " + context if context else ""}

Respond naturally and helpfully:"""
        
        response = self._call_llm(prompt, max_tokens=400, temperature=0.7)
        
        return {
            'response': response.strip()
        }
    
    def _execute_audio_transcribe_summarize(
        self,
        content: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assignment requirement: Audio → transcribe → summarize (3 formats) + duration.
        
        Transcription happens in audio_tool.py (Step 3) using Groq Whisper.
        This method receives the transcribed text and summarizes it.
        """
        # If content is empty, transcription hasn't happened yet
        if not content or content == '':
            return {
                'transcript': 'Transcription pending - audio_tool.py not yet implemented',
                'summary': None,
                'duration': None,
                'status': 'pending_tool_implementation'
            }
        
        # Content is the transcribed text - now summarize it
        summary = self._execute_summarization(content, parameters)
        
        return {
            'transcript': content,
            'summary': summary,
            'duration': parameters.get('duration', 'unknown'),
            'word_count': len(content.split())
        }
    
    def _call_llm(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.4
    ) -> str:
        """
        Call Groq LLM for task execution.
        Uses faster executor model for efficiency.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            # Return valid JSON on error for safe parsing
            error_response = {
                "error": True,
                "message": str(e),
                "type": type(e).__name__
            }
            return json.dumps(error_response)


# Global instance
executor_agent = ExecutorAgent()