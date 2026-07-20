from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Preferences(BaseModel):
    summary_length: str  # short / medium / detailed
    focus_area: Optional[List[str]] = []
    output_language: Optional[str] = "english"  # english / marathi

class SummarizeRequest(BaseModel):
    preferences: Preferences
    # case_text will be provided from PDF extraction

class Metadata(BaseModel):
    case_title: Optional[str]
    court_name: Optional[str]
    case_number: Optional[str]
    judge_names: Optional[List[str]]
    date_of_judgement: Optional[str]
    jurisdiction: Optional[str]
    summary: Optional[str]
    sections_invoked: Optional[List[str]] = []

class ConfidenceScore(BaseModel):
    overall_confidence: float
    confidence_level: str  # high / medium / low
    reliability_assessment: Optional[str] = None
    factors: Optional[Dict[str, float]] = {}
    detailed_breakdown: Optional[Dict[str, Any]] = {}
    recommendations: Optional[List[str]] = []

class SummarizeResponse(BaseModel):
    metadata: Metadata
    # flag to indicate detailed summary is available (button)
    detailed_available: bool = True
    confidence_score: Optional[ConfidenceScore] = None

class DetailedRequest(BaseModel):
    case_input: Optional[Dict[str, Any]] = None

class DetailedConfidenceScore(BaseModel):
    overall_confidence: float
    confidence_level: str
    sections_completed: str
    completeness_percentage: float

class DetailedResponse(BaseModel):
    case_title: Optional[str]
    important_dates: Optional[Dict[str, Optional[str]]]
    court_and_judge: Optional[Dict[str, Any]]
    charges_and_sections: Optional[List[Dict[str, str]]]
    brief_facts: Optional[str]
    key_issues: Optional[List[str]]
    arguments: Optional[Dict[str, str]]
    evidence_summary: Optional[Dict[str, Any]]
    legal_analysis: Optional[str]
    precedents_cited: Optional[List[Dict[str, str]]]
    decision_summary: Optional[Dict[str, Any]]
    one_page_summary_for_judges: Optional[str]
    risk_flags: Optional[Dict[str, Any]]
    extracted_entities: Optional[Dict[str, Any]]
    confidence_score: Optional[DetailedConfidenceScore] = None
