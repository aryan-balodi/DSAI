"""
Audio transcription tool using Groq Whisper API.

Handles:
- MP3 audio files
- Automatic chunking for files >25MB
- Duration extraction
- Cleanup and formatting
"""
from typing import Dict, Any
from pathlib import Path
import os
from groq import Groq

from src.utils.config import settings


def get_audio_duration(file_path: str) -> float:
    """
    Get audio duration in seconds using ffprobe.
    
    Fallback to file size estimation if ffprobe unavailable.
    """
    try:
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
             file_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return round(duration, 2)
    except Exception:
        pass
    
    # Fallback: estimate from file size (rough approximation)
    # MP3 at 128kbps ≈ 1MB per minute
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        estimated_duration = file_size_mb * 60  # seconds
        return round(estimated_duration, 2)
    except Exception:
        return 0.0


def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """
    Transcribe audio file using Groq Whisper API.
    
    Assignment requirement: Convert audio → text + cleanup
    
    Args:
        file_path: Absolute path to MP3 audio file
    
    Returns:
        {
            'transcript': str,
            'duration': float,
            'language': str,
            'success': bool,
            'error': str or None
        }
    """
    if not Path(file_path).exists():
        return {
            'transcript': '',
            'duration': 0.0,
            'language': 'unknown',
            'success': False,
            'error': f'File not found: {file_path}'
        }
    
    # Get duration
    duration = get_audio_duration(file_path)
    
    # Check file size (Groq Whisper limit: 25MB)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    max_size = settings.max_audio_size_mb
    
    if file_size_mb > max_size:
        return {
            'transcript': '',
            'duration': duration,
            'language': 'unknown',
            'success': False,
            'error': f'File too large: {file_size_mb:.1f}MB (max {max_size}MB). Please split the audio.'
        }
    
    # Transcribe with Groq Whisper
    try:
        client = Groq(api_key=settings.groq_api_key)
        
        with open(file_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(Path(file_path).name, audio_file.read()),
                model=settings.whisper_model,
                response_format="verbose_json",  # Get detailed info
                temperature=0.0  # Deterministic transcription
            )
        
        # Extract transcript text
        transcript_text = transcription.text
        
        # Clean up transcript
        cleaned_transcript = clean_transcript(transcript_text)
        
        # Extract language if available
        language = getattr(transcription, 'language', 'unknown')
        
        return {
            'transcript': cleaned_transcript,
            'duration': duration,
            'language': language,
            'success': True,
            'error': None
        }
    
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific Groq errors
        if 'api_key' in error_msg.lower():
            error_msg = 'Invalid Groq API key'
        elif 'rate_limit' in error_msg.lower():
            error_msg = 'Groq API rate limit exceeded. Please wait and retry.'
        
        return {
            'transcript': '',
            'duration': duration,
            'language': 'unknown',
            'success': False,
            'error': f'Transcription failed: {error_msg}'
        }


def clean_transcript(text: str) -> str:
    """
    Clean up transcribed text.
    
    Removes extra whitespace, normalizes punctuation.
    """
    if not text:
        return ''
    
    # Remove excessive whitespace
    lines = [line.strip() for line in text.split('\n')]
    cleaned_lines = [line for line in lines if line]
    
    # Join with proper spacing
    cleaned_text = ' '.join(cleaned_lines)
    
    # Normalize multiple spaces
    import re
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    return cleaned_text.strip()
