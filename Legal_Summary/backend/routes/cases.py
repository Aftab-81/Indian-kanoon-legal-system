from logger_setup import get_logger
logger = get_logger(__name__)

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from schemas import Preferences, SummarizeResponse, DetailedResponse
from services import generate_summary, generate_detailed_summary
from utils.pdf_extractor import extract_text_from_pdf, extract_text_with_metadata
import json
import os
from datetime import datetime

# ── Evaluation event logger (fire-and-forget, never raises) ────────────────
try:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / 'evaluation'))
    from event_logger import log_event_async as _log_summary_event
except Exception:
    def _log_summary_event(*a, **k): pass

# Storage directory for summaries
HISTORY_DIR = "./history"
os.makedirs(HISTORY_DIR, exist_ok=True)

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    pdf_file: UploadFile = File(...),
    preferences: str = Form(...)
):
    """Accept PDF and preferences, return summary based on length/focus."""
    try:
        logger.info(f"\n[API] Received PDF: {pdf_file.filename}, Size: {pdf_file.size} bytes")
        logger.info(f"[API] Preferences: {preferences}")
        
        # Parse preferences JSON
        prefs_dict = json.loads(preferences)
        preferences_obj = Preferences(**prefs_dict)
        
        logger.info(f"[API] Parsed preferences: length={preferences_obj.summary_length}, areas={preferences_obj.focus_area}, lang={preferences_obj.output_language}")
        
        # Extract text with quality metrics
        extraction_result = extract_text_with_metadata(pdf_file.file)
        case_text = extraction_result["text"]
        extraction_quality = extraction_result["quality"]
        
        if not case_text.strip():
            raise HTTPException(status_code=400, detail="PDF contains no extractable text")
        
        logger.info(f"[API] Extracted text length: {len(case_text)} chars")
        
        # Warn if extraction quality is low
        if extraction_quality["quality_level"] == "low":
            logger.warning(f"[API] WARNING: Low extraction quality - {extraction_quality['issues']}")
        
        # Generate summary using GPT with quality metrics
        logger.info(f"[API] Calling GPT for summary generation...")
        result = generate_summary(preferences_obj.dict(), case_text, extraction_quality)
        
        logger.info(f"[API] Summary generated successfully")
        logger.info(f"[API] Result metadata: {result.get('metadata', {}).get('case_title', 'N/A')}")

        # ── Log for real-time evaluation ──────────────────────────────
        _summary_text = ""
        if isinstance(result, dict):
            _summary_text = result.get("summary") or result.get("brief_summary") or ""
        elif hasattr(result, "summary"):
            _summary_text = getattr(result, "summary", "") or ""
        _log_summary_event(
            module="summary",
            user_input=f"Summarize: {pdf_file.filename}",
            response=str(_summary_text)[:3000],
            contexts=[case_text[:3000]],
            meta={"filename": pdf_file.filename,
                  "length": prefs_dict.get("summary_length", ""),
                  "focus": prefs_dict.get("focus_area", "")}
        )

        return result
    except json.JSONDecodeError:
        logger.info(f"[API] ERROR: Invalid preferences JSON")
        raise HTTPException(status_code=400, detail="Invalid preferences JSON")
    except ValueError as ve:
        logger.info(f"[API] ERROR: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.info(f"[API] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize/detailed", response_model=DetailedResponse)
async def detailed_summary(
    pdf_file: UploadFile = File(...),
    output_language: str = Form("english"),
    focus_areas: str = Form("[]")  # Accept focus areas as JSON string
):
    """Accept PDF and return comprehensive detailed summary with focus area filtering."""
    try:
        logger.info(f"\n[API] Detailed analysis for: {pdf_file.filename}")
        logger.info(f"[API] Output language: {output_language}")
        logger.info(f"[API] Focus areas: {focus_areas}")
        
        # Validate language
        if output_language not in ["english", "marathi"]:
            raise HTTPException(status_code=400, detail="Language must be 'english' or 'marathi'")
        
        # Parse focus areas
        try:
            focus_list = json.loads(focus_areas)
        except:
            focus_list = []
        
        # Extract text with quality metrics
        extraction_result = extract_text_with_metadata(pdf_file.file)
        case_text = extraction_result["text"]
        extraction_quality = extraction_result["quality"]
        
        if not case_text.strip():
            raise HTTPException(status_code=400, detail="PDF contains no extractable text")
        
        # Warn if extraction quality is low
        if extraction_quality["quality_level"] == "low":
            logger.warning(f"[API] WARNING: Low extraction quality - {extraction_quality['issues']}")
        
        # Log detected language
        detected_lang = extraction_quality.get("detected_language", "unknown")
        logger.info(f"[API] Detected document language: {detected_lang}")
        
        # Generate detailed summary using GPT with quality metrics and focus areas
        logger.info(f"[API] Calling GPT for detailed analysis...")
        result = generate_detailed_summary(case_text, extraction_quality, output_language, focus_list)
        
        logger.info(f"[API] Detailed analysis completed")
        logger.info(f"[API] Result: {result.get('case_title', 'N/A')}")
        
        return result
    except ValueError as ve:
        logger.info(f"[API] ERROR: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.info(f"[API] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history():
    """Get list of all saved summaries"""
    try:
        history_files = []
        
        if os.path.exists(HISTORY_DIR):
            for filename in os.listdir(HISTORY_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(HISTORY_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        # Extract summary info
                        history_files.append({
                            'id': filename.replace('.json', ''),
                            'case_title': data.get('metadata', {}).get('case_title') or data.get('case_title', 'Untitled'),
                            'case_number': data.get('metadata', {}).get('case_number') or data.get('case_number', ''),
                            'summary_type': data.get('summary_type', 'quick'),
                            'created_at': data.get('created_at', '')
                        })
                    except Exception as e:
                        logger.info(f"[API] ERROR reading history file {filename}: {str(e)}")
                        continue
        
        # Sort by creation date (newest first)
        history_files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {'history': history_files}
    except Exception as e:
        logger.info(f"[API] ERROR fetching history: {str(e)}")
        return {'history': []}

@router.get("/history/{summary_id}")
async def get_summary_detail(summary_id: str):
    """Get detailed content of a specific summary"""
    try:
        filepath = os.path.join(HISTORY_DIR, f"{summary_id}.json")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Summary not found")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Summary not found")
    except Exception as e:
        logger.info(f"[API] ERROR fetching summary {summary_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{summary_id}")
async def delete_summary(summary_id: str):
    """Delete a specific summary"""
    try:
        filepath = os.path.join(HISTORY_DIR, f"{summary_id}.json")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Summary not found")
        
        os.remove(filepath)
        
        return {'success': True, 'message': 'Summary deleted successfully'}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Summary not found")
    except Exception as e:
        logger.info(f"[API] ERROR deleting summary {summary_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
