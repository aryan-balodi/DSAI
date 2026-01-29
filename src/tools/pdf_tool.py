"""
PDF extraction tool using PyPDF2 and pdfplumber with OCR fallback.

Handles:
- Text-based PDFs (PyPDF2)
- Complex layouts (pdfplumber)
- Scanned PDFs (pdf2image + OCR fallback)
- Token counting for RAG decision
"""
from typing import Dict, Any
from pathlib import Path
import PyPDF2
import pdfplumber
from pdf2image import convert_from_path

from src.utils.config import settings


def count_tokens(text: str) -> int:
    """Approximate token count (1 token ≈ 4 chars)."""
    return len(text) // 4


def extract_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract text from PDF with multiple fallback strategies.
    
    Args:
        file_path: Absolute path to PDF file
    
    Returns:
        {
            'text': str,
            'pages': int,
            'tokens': int,
            'strategy': str,
            'success': bool,
            'error': str or None
        }
    """
    if not Path(file_path).exists():
        return {
            'text': '',
            'pages': 0,
            'tokens': 0,
            'strategy': 'none',
            'success': False,
            'error': f'File not found: {file_path}'
        }
    
    # Strategy 1: Try PyPDF2 (fastest for simple PDFs)
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = '\n'.join(text_parts)
            
            # Check if extraction was successful (not just whitespace)
            if full_text.strip():
                tokens = count_tokens(full_text)
                return {
                    'text': full_text.strip(),
                    'pages': num_pages,
                    'tokens': tokens,
                    'strategy': 'pypdf2',
                    'success': True,
                    'error': None
                }
    except Exception as e:
        pass  # Try next strategy
    
    # Strategy 2: Try pdfplumber (better for complex layouts)
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            num_pages = len(pdf.pages)
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = '\n'.join(text_parts)
            
            if full_text.strip():
                tokens = count_tokens(full_text)
                return {
                    'text': full_text.strip(),
                    'pages': num_pages,
                    'tokens': tokens,
                    'strategy': 'pdfplumber',
                    'success': True,
                    'error': None
                }
    except Exception as e:
        pass  # Try OCR fallback
    
    # Strategy 3: OCR fallback for scanned PDFs
    try:
        from src.tools.ocr_tool import extract_image_text
        
        # Convert PDF pages to images
        images = convert_from_path(file_path, dpi=200)
        num_pages = len(images)
        
        text_parts = []
        for i, image in enumerate(images):
            # Save temp image
            temp_path = f'/tmp/pdf_page_{i}.png'
            image.save(temp_path, 'PNG')
            
            # OCR the image
            ocr_result = extract_image_text(temp_path)
            if ocr_result['success'] and ocr_result['text']:
                text_parts.append(ocr_result['text'])
        
        full_text = '\n'.join(text_parts)
        
        if full_text.strip():
            tokens = count_tokens(full_text)
            return {
                'text': full_text.strip(),
                'pages': num_pages,
                'tokens': tokens,
                'strategy': 'ocr_fallback',
                'success': True,
                'error': None
            }
    except Exception as e:
        return {
            'text': '',
            'pages': 0,
            'tokens': 0,
            'strategy': 'failed',
            'success': False,
            'error': f'All extraction strategies failed: {str(e)}'
        }
    
    # All strategies failed
    return {
        'text': '',
        'pages': 0,
        'tokens': 0,
        'strategy': 'failed',
        'success': False,
        'error': 'Unable to extract text from PDF'
    }


def chunk_pdf_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list:
    """
    Split PDF text into chunks for RAG processing.
    
    Used when PDF is too large for direct LLM context.
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text)
        i += (chunk_size - overlap)  # Overlap for context continuity
    
    return chunks
