"""
OCR tool using Tesseract with EasyOCR fallback.

Handles:
- JPG, PNG images
- Code screenshots (Test Case 3)
- Confidence scoring
- Fallback strategy for low-confidence results
"""
from typing import Dict, Any
from pathlib import Path
import pytesseract
from PIL import Image

from src.utils.config import settings


def extract_image_text(file_path: str) -> Dict[str, Any]:
    """
    Extract text from image using OCR.
    
    Assignment requirement: Return cleaned transcript + OCR confidence
    
    Strategy:
    1. Try Tesseract (fast, local)
    2. If confidence < 0.7, try EasyOCR (slower, more accurate)
    
    Args:
        file_path: Absolute path to image file (JPG/PNG)
    
    Returns:
        {
            'text': str,
            'confidence': float,
            'strategy': str,
            'success': bool,
            'error': str or None
        }
    """
    if not Path(file_path).exists():
        return {
            'text': '',
            'confidence': 0.0,
            'strategy': 'none',
            'success': False,
            'error': f'File not found: {file_path}'
        }
    
    # Strategy 1: Tesseract OCR
    try:
        image = Image.open(file_path)
        
        # Get detailed OCR data with confidence
        ocr_data = pytesseract.image_to_data(
            image,
            lang=settings.tesseract_lang,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text and calculate average confidence
        text_parts = []
        confidences = []
        
        for i, word in enumerate(ocr_data['text']):
            if word.strip():  # Ignore empty strings
                text_parts.append(word)
                conf = int(ocr_data['conf'][i])
                if conf > 0:  # -1 means no confidence data
                    confidences.append(conf)
        
        # Combine text
        extracted_text = ' '.join(text_parts)
        
        # Calculate average confidence (0-100 scale to 0-1 scale)
        avg_confidence = (sum(confidences) / len(confidences) / 100) if confidences else 0.0
        
        # Clean up text
        cleaned_text = clean_ocr_text(extracted_text)
        
        # Check if confidence is acceptable
        threshold = settings.ocr_confidence_threshold
        
        if cleaned_text and avg_confidence >= threshold:
            return {
                'text': cleaned_text,
                'confidence': round(avg_confidence, 2),
                'strategy': 'tesseract',
                'success': True,
                'error': None
            }
        elif cleaned_text and avg_confidence < threshold:
            # Low confidence - try EasyOCR fallback
            return try_easyocr_fallback(file_path, cleaned_text, avg_confidence)
        else:
            # No text extracted
            return try_easyocr_fallback(file_path, '', 0.0)
    
    except Exception as e:
        # Tesseract failed - try EasyOCR
        return try_easyocr_fallback(file_path, '', 0.0)


def try_easyocr_fallback(
    file_path: str,
    tesseract_text: str,
    tesseract_confidence: float
) -> Dict[str, Any]:
    """
    Fallback to EasyOCR for low-confidence or failed Tesseract results.
    """
    try:
        import easyocr
        
        # Initialize EasyOCR reader (cached after first use)
        reader = easyocr.Reader(['en'], gpu=False)
        
        # Perform OCR
        results = reader.readtext(file_path)
        
        # Extract text and confidences
        text_parts = []
        confidences = []
        
        for (bbox, text, conf) in results:
            if text.strip():
                text_parts.append(text)
                confidences.append(conf)
        
        # Combine text
        extracted_text = ' '.join(text_parts)
        cleaned_text = clean_ocr_text(extracted_text)
        
        # Calculate average confidence
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        
        if cleaned_text:
            return {
                'text': cleaned_text,
                'confidence': round(avg_confidence, 2),
                'strategy': 'easyocr_fallback',
                'success': True,
                'error': None
            }
    except ImportError:
        # EasyOCR not available - return Tesseract result
        if tesseract_text:
            return {
                'text': tesseract_text,
                'confidence': tesseract_confidence,
                'strategy': 'tesseract_only',
                'success': True,
                'error': 'EasyOCR not installed, used Tesseract with low confidence'
            }
    except Exception as e:
        if tesseract_text:
            return {
                'text': tesseract_text,
                'confidence': tesseract_confidence,
                'strategy': 'tesseract_only',
                'success': True,
                'error': f'EasyOCR failed: {str(e)}'
            }
    
    # Both strategies failed
    return {
        'text': tesseract_text if tesseract_text else '',
        'confidence': tesseract_confidence,
        'strategy': 'failed',
        'success': bool(tesseract_text),
        'error': 'OCR extraction failed'
    }


def clean_ocr_text(text: str) -> str:
    """
    Clean up OCR-extracted text.
    
    Removes artifacts, fixes spacing, normalizes whitespace.
    """
    if not text:
        return ''
    
    import re
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common OCR artifacts
    text = text.replace('|', 'I')  # Common mistake
    text = text.replace('O', '0')  # In code contexts
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text
