"""
Input processing layer for file type detection and content extraction.
Routes to appropriate extraction tool without performing the extraction itself.
"""
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import mimetypes


class InputType:
    """Enumeration of supported input types."""
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    AUDIO = "audio"
    YOUTUBE = "youtube"
    UNKNOWN = "unknown"


class InputProcessor:
    """
    Analyzes input and determines extraction strategy.
    
    Design: Separation of concerns - this class detects type,
    actual extraction happens in dedicated tool modules.
    """
    
    # Supported file extensions mapping
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    PDF_EXTENSIONS = {'.pdf'}
    AUDIO_EXTENSIONS = {'.mp3', ".wav", ".m4a"}
    
    def __init__(self):
        # Initialize mimetypes for better detection
        mimetypes.init()
    
    def detect_input_type(
        self,
        text_input: Optional[str] = None,
        file_path: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Detect input type and return metadata.
        
        Returns:
            (input_type, metadata_dict)
        """
        metadata = {}
        
        # Check for YouTube URL in text
        if text_input and self._is_youtube_url(text_input):
            metadata['url'] = text_input.strip()
            return InputType.YOUTUBE, metadata
        
        # Check file input
        if file_path or filename:
            file_name = filename or Path(file_path).name
            file_ext = Path(file_name).suffix.lower()
            
            metadata['filename'] = file_name
            metadata['extension'] = file_ext
            
            if file_path:
                metadata['path'] = file_path
                metadata['size_bytes'] = Path(file_path).stat().st_size
            
            # Determine type by extension
            if file_ext in self.IMAGE_EXTENSIONS:
                return InputType.IMAGE, metadata
            elif file_ext in self.PDF_EXTENSIONS:
                return InputType.PDF, metadata
            elif file_ext in self.AUDIO_EXTENSIONS:
                return InputType.AUDIO, metadata
        
        # Default to text input
        if text_input:
            metadata['length'] = len(text_input)
            return InputType.TEXT, metadata
        
        return InputType.UNKNOWN, metadata
    
    def _is_youtube_url(self, text: str) -> bool:
        """Check if text contains a YouTube URL."""
        text_lower = text.lower().strip()
        youtube_domains = [
            'youtube.com/watch',
            'youtu.be/',
            'm.youtube.com',
            'youtube.com/v/',
            'youtube.com/embed/'
        ]
        return any(domain in text_lower for domain in youtube_domains)
    
    def validate_file_size(
        self,
        input_type: str,
        size_bytes: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate file size against limits.
        
        Returns:
            (is_valid, error_message)
        """
        # Size limits in bytes
        MAX_SIZES = {
            InputType.IMAGE: 10 * 1024 * 1024,  # 10MB
            InputType.PDF: 50 * 1024 * 1024,    # 50MB
            InputType.AUDIO: 25 * 1024 * 1024,  # 25MB (Groq Whisper limit)
        }
        
        max_size = MAX_SIZES.get(input_type)
        if not max_size:
            return True, None
        
        if size_bytes > max_size:
            max_mb = max_size / (1024 * 1024)
            return False, f"File too large. Max size for {input_type}: {max_mb}MB"
        
        return True, None
    
    def prepare_extraction_request(
        self,
        input_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare request object for extraction tools.
        
        Returns structured request with routing information.
        """
        return {
            'type': input_type,
            'metadata': metadata,
            'extraction_tool': self._get_tool_name(input_type),
            'requires_processing': input_type != InputType.TEXT
        }
    
    def _get_tool_name(self, input_type: str) -> str:
        """Map input type to tool name."""
        tool_mapping = {
            InputType.IMAGE: 'ocr_tool',
            InputType.PDF: 'pdf_tool',
            InputType.AUDIO: 'audio_tool',
            InputType.YOUTUBE: 'youtube_tool',
            InputType.TEXT: 'none'
        }
        return tool_mapping.get(input_type, 'unknown')


# Global instance
input_processor = InputProcessor()