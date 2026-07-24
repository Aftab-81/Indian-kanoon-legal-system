from logger_setup import get_logger
logger = get_logger(__name__)

import PyPDF2
from typing import BinaryIO, Dict, Any
import re

def detect_language(text: str) -> str:
    """Detect the primary language of the text."""
    # Hindi unicode range: \u0900-\u097F
    # Marathi unicode range: \u0900-\u097F (same as Hindi, uses Devanagari)
    # English: ASCII range
    
    hindi_marathi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(re.findall(r'[\w]', text))
    
    if total_chars == 0:
        return "unknown"
    
    devanagari_ratio = hindi_marathi_chars / total_chars
    english_ratio = english_chars / total_chars
    
    if devanagari_ratio > 0.3:
        # Check for Marathi-specific markers
        marathi_markers = ['महाराष्ट्र', 'मुंबई', 'पुणे', 'नागपूर']
        if any(marker in text for marker in marathi_markers):
            return "marathi"
        return "hindi"
    elif english_ratio > 0.5:
        return "english"
    else:
        return "mixed"

def clean_text(text: str, language: str = "english") -> str:
    """Clean and normalize extracted text for multiple languages."""
    # Remove excessive whitespace (works for all languages)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove page numbers and headers/footers patterns
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # Fix hyphenated words at line breaks (English specific)
    if language == "english":
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # Normalize quotes (all languages)
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Normalize Devanagari characters (Hindi/Marathi)
    if language in ["hindi", "marathi", "mixed"]:
        # Remove zero-width characters common in Devanagari text
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
        # Normalize nukta combinations
        text = re.sub(r'[\u093C]', '\u093C', text)
    
    return text.strip()

def extract_metadata_from_pdf(pdf_reader: PyPDF2.PdfReader) -> Dict[str, Any]:
    """Extract PDF metadata for quality assessment."""
    metadata = {
        "num_pages": len(pdf_reader.pages),
        "has_metadata": pdf_reader.metadata is not None,
        "extractable_pages": 0,
        "total_chars": 0,
        "avg_chars_per_page": 0,
        "detected_language": "unknown"
    }
    
    all_text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text and len(page_text.strip()) > 50:
            metadata["extractable_pages"] += 1
            metadata["total_chars"] += len(page_text)
            all_text += page_text
    
    if metadata["extractable_pages"] > 0:
        metadata["avg_chars_per_page"] = metadata["total_chars"] / metadata["extractable_pages"]
    
    # Detect language from extracted text
    if all_text:
        metadata["detected_language"] = detect_language(all_text)
    
    return metadata

def assess_extraction_quality(metadata: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Assess the quality of text extraction."""
    quality_score = 100.0
    issues = []
    
    # Check page extraction rate
    if metadata["num_pages"] > 0:
        extraction_rate = metadata["extractable_pages"] / metadata["num_pages"]
        if extraction_rate < 0.5:
            quality_score -= 30
            issues.append("Low extraction rate - document may be scanned")
        elif extraction_rate < 0.8:
            quality_score -= 15
            issues.append("Moderate extraction rate - some pages unreadable")
    
    # Check average characters per page (adjusted for different scripts)
    min_chars_threshold = 500
    if metadata["detected_language"] in ["hindi", "marathi", "mixed"]:
        # Devanagari characters may appear denser
        min_chars_threshold = 400
    
    if metadata["avg_chars_per_page"] < min_chars_threshold:
        quality_score -= 20
        issues.append("Low text density - possible OCR required")
    
    # Check for garbled text patterns (adjusted for Devanagari)
    if metadata["detected_language"] in ["hindi", "marathi", "mixed"]:
        # Allow more special chars for Devanagari combining marks
        garbled_ratio = len(re.findall(r'[^\w\s.,;:!?\-()\'\"।॥\u0900-\u097F]+', text)) / max(len(text), 1)
    else:
        garbled_ratio = len(re.findall(r'[^\w\s.,;:!?\-()\'\"]+', text)) / max(len(text), 1)
    
    if garbled_ratio > 0.05:
        quality_score -= 25
        issues.append("High rate of special characters - possible encoding issues")
    
    # Check text length
    if len(text) < 1000:
        quality_score -= 20
        issues.append("Very short document - may be incomplete")
    
    quality_score = max(0, min(100, quality_score))
    
    return {
        "extraction_quality_score": round(quality_score, 2),
        "quality_level": "high" if quality_score >= 80 else "medium" if quality_score >= 50 else "low",
        "issues": issues,
        "text_length": len(text),
        "word_count": len(text.split()),
        "detected_language": metadata["detected_language"]
    }

def extract_text_from_pdf(pdf_file: BinaryIO) -> str:
    """Extract text content from uploaded PDF file with enhanced multi-language processing."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = []
        
        # First pass: detect language
        sample_text = ""
        for i, page in enumerate(pdf_reader.pages[:3]):  # Sample first 3 pages
            page_text = page.extract_text()
            if page_text:
                sample_text += page_text
        
        detected_lang = detect_language(sample_text) if sample_text else "english"
        
        # Second pass: extract and clean with language-aware cleaning
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                cleaned_text = clean_text(page_text, detected_lang)
                if cleaned_text:
                    text_content.append(cleaned_text)
        
        full_text = "\n\n".join(text_content)
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from PDF. The document may be scanned or image-based. Please use OCR software first.")
        
        return full_text
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

def extract_text_with_metadata(pdf_file: BinaryIO) -> Dict[str, Any]:
    """Extract text and provide quality metrics with language detection."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = []
        
        # Extract metadata
        pdf_metadata = extract_metadata_from_pdf(pdf_reader)
        detected_lang = pdf_metadata["detected_language"]
        
        logger.info(f"[PDF Extractor] Pages: {pdf_metadata['num_pages']}, Extractable: {pdf_metadata['extractable_pages']}")
        logger.info(f"[PDF Extractor] Detected language: {detected_lang}")
        
        # Extract text with language-aware cleaning
        for idx, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                cleaned_text = clean_text(page_text, detected_lang)
                if cleaned_text:
                    text_content.append(cleaned_text)
                    if idx == 0:  # Log first page sample
                        logger.info(f"[PDF Extractor] First page sample (200 chars): {cleaned_text[:200]}")
        
        full_text = "\n\n".join(text_content)
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from PDF")
        
        logger.info(f"[PDF Extractor] Total extracted text length: {len(full_text)} characters")
        logger.info(f"[PDF Extractor] Word count: {len(full_text.split())}")
        
        # Assess quality
        quality_assessment = assess_extraction_quality(pdf_metadata, full_text)
        
        logger.info(f"[PDF Extractor] Quality score: {quality_assessment['extraction_quality_score']}%")
        logger.info(f"[PDF Extractor] Quality level: {quality_assessment['quality_level']}")
        if quality_assessment['issues']:
            logger.info(f"[PDF Extractor] Issues: {quality_assessment['issues']}")
        
        return {
            "text": full_text,
            "metadata": pdf_metadata,
            "quality": quality_assessment
        }
    except Exception as e:
        logger.info(f"[PDF Extractor] ERROR: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
