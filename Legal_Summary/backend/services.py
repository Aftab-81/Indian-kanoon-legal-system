from logger_setup import get_logger
logger = get_logger(__name__)

from typing import Dict, Any, List
from schemas import Metadata
from openai import OpenAI
from config import settings
import json
import re
import os
from datetime import datetime
import uuid

client = OpenAI(api_key=settings.openai_api_key)

HISTORY_DIR = "./history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def save_to_history(data, summary_type='quick'):
    """Save summary to history with unique ID"""
    try:
        # Generate unique ID
        summary_id = str(uuid.uuid4())
        
        # Add metadata
        data['id'] = summary_id
        data['summary_type'] = summary_type
        data['created_at'] = datetime.now().isoformat()
        
        # Save to file
        filepath = os.path.join(HISTORY_DIR, f"{summary_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[History] Saved summary {summary_id} to history")
        return summary_id
    except Exception as e:
        logger.info(f"[History] ERROR saving to history: {str(e)}")
        return None

def calculate_summary_confidence(
    gpt_response: Dict[str, Any],
    case_text: str,
    extraction_quality: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate comprehensive confidence score for case summary quality.
    
    Scoring Methodology:
    ====================
    1. PDF Extraction Quality (25% weight) - Measures source document readability
    2. Metadata Completeness (20% weight) - Checks if key case information is present
    3. Content Quality (20% weight) - Evaluates summary text quality and specificity
    4. Legal Terminology (15% weight) - Validates legal context and vocabulary
    5. Summary Length Appropriateness (10% weight) - Checks compression ratio
    6. Data Validation (10% weight) - Validates dates, sections, and structure
    
    Total: 100 points
    Thresholds: High (≥85), Medium (≥65), Low (<65)
    """
    confidence_score = 100.0
    confidence_factors = {}
    detailed_breakdown = {}
    
    # ========== FACTOR 1: PDF EXTRACTION QUALITY (25 points) ==========
    extraction_score = extraction_quality.get("extraction_quality_score", 50)
    factor_1_score = (extraction_score / 100) * 25
    confidence_factors["extraction_quality"] = round(extraction_score, 2)
    detailed_breakdown["extraction_quality"] = {
        "score": round(factor_1_score, 2),
        "max_points": 25,
        "percentage": round(extraction_score, 2),
        "description": "PDF text extraction quality and readability"
    }
    
    # ========== FACTOR 2: METADATA COMPLETENESS (20 points) ==========
    required_fields = {
        "case_title": 5,
        "court_name": 4,
        "case_number": 3,
        "judge_names": 4,
        "date_of_judgement": 2,
        "sections_invoked": 2
    }
    
    metadata_score = 0
    missing_fields = []
    
    for field, points in required_fields.items():
        value = gpt_response.get(field)
        if value and value not in ["Unknown Case", "Unknown Court", "N/A", "Not Available", ""]:
            # Additional validation for lists
            if isinstance(value, list):
                if len(value) > 0:
                    metadata_score += points
                else:
                    missing_fields.append(field)
            else:
                metadata_score += points
        else:
            missing_fields.append(field)
    
    completeness_percentage = (metadata_score / 20) * 100
    confidence_factors["metadata_completeness"] = round(completeness_percentage, 2)
    detailed_breakdown["metadata_completeness"] = {
        "score": round(metadata_score, 2),
        "max_points": 20,
        "percentage": round(completeness_percentage, 2),
        "missing_fields": missing_fields,
        "description": "Presence of essential case metadata"
    }
    
    # ========== FACTOR 3: CONTENT QUALITY (20 points) ==========
    summary = gpt_response.get("summary", "")
    content_score = 20.0
    content_issues = []
    
    # Sub-metric 3a: Minimum length check (5 points)
    word_count = len(summary.split())
    if word_count < 10:
        content_score -= 5
        content_issues.append("Summary too short (< 10 words)")
    elif word_count < 20:
        content_score -= 2
        content_issues.append("Summary somewhat short")
    
    # Sub-metric 3b: Generic terms penalty (7 points)
    generic_terms = [
        "allegedly", "reportedly", "may have", "possibly", 
        "unclear", "unknown", "not specified", "not mentioned"
    ]
    generic_count = sum(summary.lower().count(term) for term in generic_terms)
    generic_penalty = min(generic_count * 1.5, 7)
    content_score -= generic_penalty
    if generic_count > 0:
        content_issues.append(f"Contains {generic_count} generic/uncertain terms")
    
    # Sub-metric 3c: Information density (5 points)
    # Check for specific legal information (dates, sections, names)
    has_dates = bool(re.search(r'\d{4}|\d{1,2}/\d{1,2}/\d{2,4}', summary))
    has_sections = bool(re.search(r'section|ipc|crpc|act|article', summary.lower()))
    has_proper_nouns = bool(re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', summary))
    
    density_score = sum([has_dates * 2, has_sections * 2, has_proper_nouns * 1])
    if density_score < 3:
        content_score -= (5 - density_score)
        content_issues.append("Low information density")
    
    # Sub-metric 3d: Completeness indicators (3 points)
    completeness_indicators = [
        any(word in summary.lower() for word in ["convicted", "acquitted", "dismissed", "allowed", "sentenced"]),
        any(word in summary.lower() for word in ["prosecution", "defense", "petitioner", "respondent"]),
        any(word in summary.lower() for word in ["evidence", "witness", "testimony", "proof"])
    ]
    completeness_bonus = sum(completeness_indicators)
    if completeness_bonus < 2:
        content_score -= (3 - completeness_bonus)
        content_issues.append("Missing key case elements")
    
    content_score = max(0, content_score)
    confidence_factors["content_quality"] = round((content_score / 20) * 100, 2)
    detailed_breakdown["content_quality"] = {
        "score": round(content_score, 2),
        "max_points": 20,
        "percentage": round((content_score / 20) * 100, 2),
        "word_count": word_count,
        "issues": content_issues,
        "description": "Summary content quality and specificity"
    }
    
    # ========== FACTOR 4: LEGAL TERMINOLOGY (15 points) ==========
    legal_terms = {
        "court_terms": ["court", "judge", "justice", "bench", "tribunal"],
        "case_terms": ["case", "appeal", "petition", "writ", "suit", "matter"],
        "legal_process": ["hearing", "trial", "evidence", "witness", "testimony", "argument"],
        "legal_sections": ["section", "article", "act", "code", "ipc", "crpc", "cpc"],
        "decisions": ["held", "observed", "directed", "ordered", "convicted", "acquitted"]
    }
    
    terminology_score = 0
    terms_found = {}
    
    for category, terms in legal_terms.items():
        found_count = sum(1 for term in terms if term in summary.lower())
        if found_count > 0:
            terminology_score += min(found_count * 0.5, 3)  # Max 3 points per category
        terms_found[category] = found_count
    
    terminology_score = min(terminology_score, 15)
    confidence_factors["legal_terminology"] = round((terminology_score / 15) * 100, 2)
    detailed_breakdown["legal_terminology"] = {
        "score": round(terminology_score, 2),
        "max_points": 15,
        "percentage": round((terminology_score / 15) * 100, 2),
        "terms_by_category": terms_found,
        "description": "Presence of legal vocabulary and terminology"
    }
    
    # ========== FACTOR 5: SUMMARY LENGTH APPROPRIATENESS (10 points) ==========
    doc_length = len(case_text.split())
    summary_length = len(summary.split())
    
    length_score = 10.0
    
    if doc_length > 0:
        compression_ratio = (summary_length / doc_length) * 100
        
        # Optimal range: 1% to 10% of original document
        if 1 <= compression_ratio <= 10:
            # Perfect range - no penalty
            length_score = 10.0
        elif compression_ratio < 1:
            # Too compressed - might be missing information
            length_score = max(compression_ratio * 10, 2)
        else:
            # Too verbose - might be redundant
            penalty = min((compression_ratio - 10) * 0.5, 8)
            length_score = max(10 - penalty, 2)
        
        confidence_factors["compression_ratio"] = round(compression_ratio, 2)
    else:
        compression_ratio = 0
        length_score = 5
    
    detailed_breakdown["length_appropriateness"] = {
        "score": round(length_score, 2),
        "max_points": 10,
        "percentage": round((length_score / 10) * 100, 2),
        "compression_ratio": round(compression_ratio, 2),
        "doc_words": doc_length,
        "summary_words": summary_length,
        "description": "Summary length relative to source document"
    }
    
    # ========== FACTOR 6: DATA VALIDATION (10 points) ==========
    validation_score = 10.0
    validation_issues = []
    
    # Sub-metric 6a: Date format validation (3 points)
    date_value = gpt_response.get("date_of_judgement", "")
    if date_value and date_value not in ["N/A", "Not Available"]:
        if not re.match(r'\d{4}-\d{2}-\d{2}', date_value):
            validation_score -= 3
            validation_issues.append("Invalid date format")
    
    # Sub-metric 6b: Judge names format (2 points)
    judges = gpt_response.get("judge_names", [])
    if isinstance(judges, list) and len(judges) > 0:
        # Check if judges have proper titles
        has_titles = any(any(title in str(judge).lower() for title in ["justice", "hon'ble", "judge"]) for judge in judges)
        if not has_titles:
            validation_score -= 1
            validation_issues.append("Judge names lack proper titles")
    
    # Sub-metric 6c: Sections format (2 points)
    sections = gpt_response.get("sections_invoked", [])
    if isinstance(sections, list) and len(sections) > 0:
        # Check if sections mention act/code
        has_act_reference = any(any(act in str(section).lower() for act in ["ipc", "crpc", "act", "code"]) for section in sections)
        if not has_act_reference:
            validation_score -= 1
            validation_issues.append("Sections lack act/code references")
    
    # Sub-metric 6d: Case title format (3 points)
    case_title = gpt_response.get("case_title", "")
    if case_title and case_title not in ["Unknown Case", "Not Available"]:
        # Check for proper case title format (should have vs/v./versus)
        if not any(sep in case_title.lower() for sep in ["vs", "v.", "versus", "vs."]):
            validation_score -= 2
            validation_issues.append("Case title missing party separator")
    else:
        validation_score -= 3
        validation_issues.append("Case title missing")
    
    validation_score = max(0, validation_score)
    confidence_factors["data_validation"] = round((validation_score / 10) * 100, 2)
    detailed_breakdown["data_validation"] = {
        "score": round(validation_score, 2),
        "max_points": 10,
        "percentage": round((validation_score / 10) * 100, 2),
        "issues": validation_issues,
        "description": "Format and structure validation of extracted data"
    }
    
    # ========== CALCULATE FINAL SCORE ==========
    final_score = (
        factor_1_score +
        metadata_score +
        content_score +
        terminology_score +
        length_score +
        validation_score
    )
    
    final_score = max(0, min(100, final_score))
    
    # Determine confidence level with clear thresholds
    if final_score >= 85:
        confidence_level = "high"
        reliability = "Excellent - Results are highly reliable"
    elif final_score >= 65:
        confidence_level = "medium"
        reliability = "Good - Review recommended for critical decisions"
    else:
        confidence_level = "low"
        reliability = "Caution - Manual verification strongly recommended"
    
    return {
        "overall_confidence": round(final_score, 2),
        "confidence_level": confidence_level,
        "reliability_assessment": reliability,
        "factors": confidence_factors,
        "detailed_breakdown": detailed_breakdown,
        "recommendations": _generate_confidence_recommendations(final_score, confidence_factors, detailed_breakdown)
    }

def _generate_confidence_recommendations(score: float, factors: Dict, breakdown: Dict) -> List[str]:
    """Generate actionable recommendations based on detailed confidence analysis."""
    recommendations = []
    
    # Extraction quality recommendations
    if factors.get("extraction_quality", 100) < 70:
        recommendations.append("⚠️ PDF Quality: Use higher quality PDF or OCR software for better text extraction")
    
    # Metadata completeness recommendations
    metadata_breakdown = breakdown.get("metadata_completeness", {})
    missing = metadata_breakdown.get("missing_fields", [])
    if missing:
        recommendations.append(f"📋 Missing Metadata: {', '.join(missing)} - Verify document completeness")
    
    # Content quality recommendations
    content_breakdown = breakdown.get("content_quality", {})
    content_issues = content_breakdown.get("issues", [])
    if content_issues:
        recommendations.append(f"✍️ Content Quality: {'; '.join(content_issues)}")
    
    # Legal terminology recommendations
    if factors.get("legal_terminology", 100) < 60:
        recommendations.append("⚖️ Legal Context: Limited legal terminology - Verify document is a legal case judgment")
    
    # Compression ratio recommendations
    compression = factors.get("compression_ratio", 5)
    if compression < 1:
        recommendations.append("📉 Summary Length: Summary may be too brief - Consider detailed analysis")
    elif compression > 15:
        recommendations.append("📈 Summary Length: Summary may be too verbose - Consider shorter version")
    
    # Data validation recommendations
    validation_breakdown = breakdown.get("data_validation", {})
    validation_issues = validation_breakdown.get("issues", [])
    if validation_issues:
        recommendations.append(f"✓ Data Validation: {'; '.join(validation_issues)}")
    
    # Overall recommendations based on score
    if score >= 85:
        recommendations.insert(0, "✅ High Confidence: Summary is reliable and comprehensive")
    elif score >= 65:
        recommendations.insert(0, "⚠️ Medium Confidence: Review summary for accuracy before critical use")
    else:
        recommendations.insert(0, "❌ Low Confidence: Manual review and verification strongly recommended")
    
    # Specific actionable items
    if score < 85:
        if metadata_breakdown.get("percentage", 100) < 80:
            recommendations.append("🔍 Action: Cross-verify case details with original document")
        if content_breakdown.get("word_count", 0) < 20:
            recommendations.append("🔍 Action: Request detailed summary for complete analysis")
    
    return recommendations

def _build_summary_prompt(case_text: str, preferences: Dict[str, Any]) -> str:
    """Build GPT prompt based on user preferences."""
    length = preferences.get("summary_length", "short")
    focus_areas = preferences.get("focus_area", [])
    output_language = preferences.get("output_language", "english")
    
    length_instructions = {
        "short": "Provide a concise 3-5 sentence summary focusing on the core outcome.",
        "medium": "Provide a moderate 8-12 sentence summary covering key facts, arguments, and decision.",
        "detailed": "Provide a comprehensive summary covering all major aspects: facts, procedure, arguments, evidence, reasoning, and conclusion."
    }
    
    focus_instruction = ""
    if focus_areas:
        focus_instruction = f"\nPrioritize these aspects: {', '.join(focus_areas)}."
    
    # Language-specific instructions
    if output_language == "marathi":
        language_instruction = "\n\nIMPORTANT: Provide the summary field in PROPER Marathi language using correct Devanagari script. Use standard Unicode characters only. Keep all other field names and metadata in English."
    else:
        language_instruction = "\n\nProvide all content in English language."
    
    prompt = f"""You are an expert legal analyst fluent in Marathi and English. Analyze this Indian legal case document and extract key information with proper Unicode encoding.

{length_instructions.get(length, length_instructions['short'])}
{focus_instruction}
{language_instruction}

INSTRUCTIONS:
1. Read the document carefully and extract EXACT information as it appears
2. For case_title: Copy the exact case name from the document preserving original script
3. For court_name: Extract court name exactly as written (if Marathi, keep in Marathi; if English, keep in English)
4. For case_number: Copy the case/appeal number exactly
5. For judge_names: List all judges with proper titles (e.g., ["न्या. ए.बी. शाह", "न्या. सी.डी. पटेल"] or ["Justice A.B. Shah", "Justice C.D. Patel"])
6. For date_of_judgement: Convert to YYYY-MM-DD format
7. For court_composition: E.g., "Single Judge", "Division Bench", "Full Bench", etc. If missing, use "Not Available"
8. For citations: List all citations found (e.g. ["2005(1)AWC911"]). If none, use []
9. For case_category: E.g., "Criminal Appeal", "Civil Writ Petition", etc. If missing, use "Not Available"
10. For sections_invoked: List ALL legal sections mentioned exactly as they appear
11. For summary: Write in the requested language using proper Unicode characters
12. Use ONLY standard Unicode Devanagari characters (U+0900 to U+097F range)
13. Avoid any special symbols, placeholders, or encoding artifacts

Case Document Text:
{case_text[:15000]}

Return ONLY this JSON structure with clean Unicode text:
{{
  "case_title": "exact case title",
  "court_name": "exact court name",
  "case_number": "exact case number",
  "judge_names": ["list of judges with proper names"],
  "date_of_judgement": "YYYY-MM-DD",
  "jurisdiction": "India",
  "court_composition": "composition or Not Available",
  "citations": ["list of citations"],
  "case_category": "category or Not Available",
  "summary": "clean summary in requested language",
  "sections_invoked": ["list of sections"]
}}"""

    return prompt

def _build_detailed_prompt(case_text: str, output_language: str = "english", focus_areas: List[str] = None) -> str:
    """Build GPT prompt for detailed extraction with focus area filtering."""
    
    if output_language == "marathi":
        language_instruction = """
LANGUAGE: Provide all descriptive content (facts, arguments, analysis, observations) in PROPER Marathi using correct Devanagari script (Unicode range U+0900 to U+097F).
- Use standard Marathi spelling and grammar
- Avoid any encoding artifacts or special symbols
- Keep JSON field names, legal section numbers in English
- Write dates in YYYY-MM-DD format
- Names can be in original script from document
"""
    else:
        language_instruction = """
LANGUAGE: Provide all content in clear English.
If source is Hindi/Marathi, translate to proper English while preserving legal accuracy and names.
"""
    
    # Build focus area instruction
    focus_instruction = ""
    if focus_areas and len(focus_areas) > 0:
        focus_mapping = {
            "facts": "brief_facts, important_dates, extracted_entities",
            "arguments": "arguments, key_issues",
            "evidence": "evidence_summary, charges_and_sections",
            "legal reasoning": "legal_analysis, decision_summary",
            "precedents": "precedents_cited"
        }
        
        included_sections = []
        for area in focus_areas:
            if area in focus_mapping:
                included_sections.extend(focus_mapping[area].split(", "))
        
        if included_sections:
            focus_instruction = f"\n\nFOCUS PRIORITY: Pay special attention to extracting detailed information for these sections: {', '.join(set(included_sections))}."
            
            # If precedents not in focus, explicitly mention to skip
            if "precedents" not in focus_areas:
                focus_instruction += "\nIMPORTANT: User has NOT requested precedents - return empty array for precedents_cited."
    
    prompt = f"""You are an expert legal analyst fluent in Marathi, Hindi, and English. Perform comprehensive analysis using proper Unicode encoding.

{language_instruction}
{focus_instruction}

EXTRACTION REQUIREMENTS:
1. Read the ENTIRE document carefully
2. Extract information preserving original script where appropriate
3. For dates: Always use YYYY-MM-DD format
4. Use clean Unicode characters only - no encoding artifacts
5. For Marathi output: Use standard Devanagari Unicode (क not क़, ं not ﮮ, etc.)
6. For missing info: Use "Not Available"
7. For sections not in user's focus: Provide minimal/empty data

Case Document Text:
{case_text[:20000]}

Return ONLY clean JSON with proper Unicode encoding:
{{
  "case_title": "exact title from document",
  "important_dates": {{
    "incident_date": "YYYY-MM-DD or Not Available",
    "fir_date": "YYYY-MM-DD or Not Available",
    "judgement_date": "YYYY-MM-DD or Not Available"
  }},
  "court_and_judge": {{
    "court_name": "exact court name",
    "judge_names": ["proper judge names with titles"]
  }},
  "charges_and_sections": [
    {{"section": "Section with Act name", "description": "brief description"}}
  ],
  "brief_facts": "5-10 sentence chronological summary",
  "key_issues": [
    "Legal questions addressed by court"
  ],
  "arguments": {{
    "prosecution": "Prosecution arguments summary",
    "defense": "Defense arguments summary"
  }},
  "evidence_summary": {{
    "witnesses": [
      {{"name": "Witness designation", "role": "role", "reliability": "High/Medium/Low"}}
    ],
    "material_evidence": ["list of evidence"]
  }},
  "legal_analysis": "Court's reasoning (3-5 sentences minimum)",
  "precedents_cited": [
    {{"case": "Case Name (Year)", "principle": "legal principle"}}
  ],
  "decision_summary": {{
    "final_order": "Court's final order",
    "sentence": "Sentence if applicable",
    "important_observations": "Key court observations"
  }},
  "one_page_summary_for_judges": "Comprehensive 10-15 line summary",
  "risk_flags": {{
    "missing_evidence": ["gaps in evidence"],
    "contradictions": ["contradictions found"],
    "procedural_lapses": ["procedural issues"]
  }},
  "extracted_entities": {{
    "accused": ["accused names"],
    "victim": ["victim names"],
    "witnesses": ["witness list"],
    "locations": ["locations mentioned"],
    "dates": ["significant dates in YYYY-MM-DD"]
  }}
}}"""
    
    return prompt

def _call_gpt(prompt: str) -> Dict[str, Any]:
    """Call OpenAI API and parse JSON response."""
    try:
        # Validate API key is set
        settings.validate_api_key()
        
        logger.info(f"[GPT] Calling OpenAI API with model: {settings.openai_model}")
        logger.info(f"[GPT] Prompt length: {len(prompt)} characters")
        
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a legal document analyzer specializing in Indian law. Always respond with valid JSON only. Extract information accurately from the provided text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        logger.info(f"[GPT] Response received, length: {len(content)} characters")
        logger.info(f"[GPT] Response preview: {content[:200]}...")
        
        parsed = json.loads(content)
        logger.info(f"[GPT] JSON parsed successfully, keys: {list(parsed.keys())}")
        
        return parsed
    except json.JSONDecodeError as je:
        logger.info(f"[GPT] ERROR: Invalid JSON response")
        logger.info(f"[GPT] Response was: {content[:500]}")
        raise ValueError(f"GPT returned invalid JSON: {str(je)}")
    except Exception as e:
        logger.info(f"[GPT] ERROR: {str(e)}")
        raise ValueError(f"OpenAI API error: {str(e)}")

def generate_summary(preferences: Dict[str, Any], case_text: str, extraction_quality: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate summary using GPT based on preferences."""
    prompt = _build_summary_prompt(case_text, preferences)
    gpt_response = _call_gpt(prompt)
    
    # Calculate confidence score
    if extraction_quality is None:
        extraction_quality = {"extraction_quality_score": 75}
    
    confidence = calculate_summary_confidence(gpt_response, case_text, extraction_quality)
    
    metadata = {
        "case_title": gpt_response.get("case_title", "Unknown Case"),
        "court_name": gpt_response.get("court_name", "Unknown Court"),
        "case_number": gpt_response.get("case_number", "N/A"),
        "judge_names": gpt_response.get("judge_names", []),
        "date_of_judgement": gpt_response.get("date_of_judgement", "N/A"),
        "jurisdiction": gpt_response.get("jurisdiction", "India"),
        "court_composition": gpt_response.get("court_composition", "Not Available"),
        "citations": gpt_response.get("citations", []),
        "case_category": gpt_response.get("case_category", "Not Available"),
        "summary": gpt_response.get("summary", "Not Available"),
        "sections_invoked": gpt_response.get("sections_invoked", [])
    }
    
    result = {
        "metadata": metadata,
        "detailed_available": True,
        "confidence_score": confidence
    }
    
    # Save to history
    save_to_history(result, 'quick')
    
    return result

def generate_detailed_summary(case_text: str, extraction_quality: Dict[str, Any] = None, output_language: str = "english", focus_areas: List[str] = None) -> Dict[str, Any]:
    """Generate detailed summary using GPT with focus area filtering."""
    prompt = _build_detailed_prompt(case_text, output_language, focus_areas)
    detailed = _call_gpt(prompt)
    
    # Calculate confidence for detailed summary
    if extraction_quality is None:
        extraction_quality = {"extraction_quality_score": 75}
    
    # Assess detailed summary completeness
    required_sections = [
        "case_title", "important_dates", "court_and_judge", "charges_and_sections",
        "brief_facts", "key_issues", "arguments", "evidence_summary",
        "legal_analysis", "decision_summary"
    ]
    
    filled_sections = sum(1 for section in required_sections if detailed.get(section))
    completeness_score = (filled_sections / len(required_sections)) * 100
    
    detailed_confidence = {
        "overall_confidence": round(min(extraction_quality.get("extraction_quality_score", 75), completeness_score), 2),
        "confidence_level": "high" if completeness_score >= 80 else "medium" if completeness_score >= 60 else "low",
        "sections_completed": f"{filled_sections}/{len(required_sections)}",
        "completeness_percentage": round(completeness_score, 2)
    }
    
    # Filter sections based on focus areas
    if focus_areas and len(focus_areas) > 0:
        # If precedents not in focus, clear precedents_cited
        if "precedents" not in focus_areas:
            detailed["precedents_cited"] = []
        
        # Similar filtering for other areas (optional - you can make it strict or lenient)
        # For now, we'll just filter precedents since that's the main issue
    
    # Ensure all expected fields exist with defaults
    result = {
        "case_title": detailed.get("case_title", "Unknown Case"),
        "important_dates": detailed.get("important_dates", {}),
        "court_and_judge": detailed.get("court_and_judge", {}),
        "charges_and_sections": detailed.get("charges_and_sections", []),
        "brief_facts": detailed.get("brief_facts", ""),
        "key_issues": detailed.get("key_issues", []),
        "arguments": detailed.get("arguments", {}),
        "evidence_summary": detailed.get("evidence_summary", {}),
        "legal_analysis": detailed.get("legal_analysis", ""),
        "precedents_cited": detailed.get("precedents_cited", []),
        "decision_summary": detailed.get("decision_summary", {}),
        "one_page_summary_for_judges": detailed.get("one_page_summary_for_judges", ""),
        "risk_flags": detailed.get("risk_flags", {}),
        "extracted_entities": detailed.get("extracted_entities", {}),
        "confidence_score": detailed_confidence
    }
    
    # Save to history
    save_to_history(result, 'detailed')
    
    return result