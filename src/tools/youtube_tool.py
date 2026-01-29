"""
YouTube transcript fetching tool using youtube-transcript-api.

Handles:
- YouTube video URLs (various formats)
- Transcript extraction
- Fallback messages for unavailable transcripts
- Language detection
"""
from typing import Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import re


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If URL is already just the video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    return None


def fetch_youtube_transcript(url: str) -> Dict[str, Any]:
    """
    Fetch transcript from YouTube video.
    
    Assignment requirement: Detect URL → fetch transcript (or fallback message)
    
    Args:
        url: YouTube video URL or video ID
    
    Returns:
        {
            'transcript': str,
            'video_id': str,
            'language': str,
            'duration': float,
            'success': bool,
            'error': str or None
        }
    """
    # Extract video ID
    video_id = extract_video_id(url)
    
    if not video_id:
        return {
            'transcript': '',
            'video_id': '',
            'language': 'unknown',
            'duration': 0.0,
            'success': False,
            'error': 'Invalid YouTube URL. Could not extract video ID.'
        }
    
    try:
        # New API: instantiate and use fetch() instead of get_transcript()
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id)
        
        # Extract text and duration
        transcript_parts = []
        total_duration = 0.0
        
        for entry in transcript_list:
            # Entry is an object, not a dict - use attributes
            text = entry.text.strip() if hasattr(entry, 'text') else ''
            if text:
                transcript_parts.append(text)
            
            # Track duration
            start = entry.start if hasattr(entry, 'start') else 0
            duration = entry.duration if hasattr(entry, 'duration') else 0
            end_time = start + duration
            if end_time > total_duration:
                total_duration = end_time
        
        # Combine transcript
        full_transcript = ' '.join(transcript_parts)
        
        # Clean up transcript
        cleaned_transcript = clean_youtube_transcript(full_transcript)
        
        # Try to get language info
        try:
            transcript_info = api.list(video_id)
            language = 'en'  # Default
            for transcript in transcript_info:
                if hasattr(transcript, 'language_code'):
                    language = transcript.language_code
                    break
        except Exception:
            language = 'unknown'
        
        return {
            'transcript': cleaned_transcript,
            'video_id': video_id,
            'language': language,
            'duration': round(total_duration, 2),
            'success': True,
            'error': None
        }
    
    except TranscriptsDisabled:
        return {
            'transcript': '',
            'video_id': video_id,
            'language': 'unknown',
            'duration': 0.0,
            'success': False,
            'error': 'Transcripts are disabled for this video.'
        }
    
    except NoTranscriptFound:
        return {
            'transcript': '',
            'video_id': video_id,
            'language': 'unknown',
            'duration': 0.0,
            'success': False,
            'error': 'No transcript available for this video. The video may not have captions.'
        }
    
    except VideoUnavailable:
        return {
            'transcript': '',
            'video_id': video_id,
            'language': 'unknown',
            'duration': 0.0,
            'success': False,
            'error': 'Video is unavailable or private.'
        }
    
    except Exception as e:
        return {
            'transcript': '',
            'video_id': video_id,
            'language': 'unknown',
            'duration': 0.0,
            'success': False,
            'error': f'Failed to fetch transcript: {str(e)}'
        }


def clean_youtube_transcript(text: str) -> str:
    """
    Clean up YouTube transcript text.
    
    Removes auto-generated artifacts, fixes formatting.
    """
    if not text:
        return ''
    
    import re
    
    # Remove music/sound notations like [Music], [Applause]
    text = re.sub(r'\[.*?\]', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove repeated words (common in auto-captions)
    words = text.split()
    cleaned_words = []
    prev_word = None
    
    for word in words:
        if word != prev_word:
            cleaned_words.append(word)
        prev_word = word
    
    text = ' '.join(cleaned_words)
    
    return text.strip()
