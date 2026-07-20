import openai
import json
from typing import Dict, Any, List
import time
import re
import httpx
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class CaseExtractor:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=self.api_key)  # Initialize the client

    def extract_case_details(self, case_text: str) -> Dict[str, str]:
        """
        Extract the 8 key fields from a legal case using LLM
        """
        if not case_text:
            return self._create_error_response()
            
        # Increase truncation limit to approximately 25,000 words (about 150,000 chars)
        # We'll use a more conservative 100,000 chars to ensure we stay within token limits
        truncated_text = case_text[:100000]
        
        # Count words to verify we're handling the requested amount
        word_count = len(truncated_text.split())
        print(f"Processing approximately {word_count} words")
        
        # Prepare the prompt for the LLM with clearer instructions
        prompt = f"""
        Analyze this legal case text and extract the following components with special attention to dates.
        Respond ONLY with a JSON object containing these exact keys and their corresponding values.
        
        IMPORTANT: 
        1. For the Case Title & Citation, include the complete citation
        2. Extract the exact date in "DD Month YYYY" format if available
        3. If only year is available, include both the date field and year in citation
        4. Search for date patterns like "on DD Month, YYYY", "[YYYY]", "YYYY INSC", etc.

        Required JSON structure:
        {{
            "Case Title & Citation": "full case title with citation",
            "Date": "DD Month YYYY",  // Exact date in this format
            "Bench / Court": "court name and judges",
            "Facts of the Case": "concise summary of facts",
            "Issues Framed": "main legal issues",
            "Arguments by Parties": "key arguments",
            "Court's Analysis / Reasoning": "court's analysis",
            "Final Decision (Ratio Decidendi)": "final decision",
            "Obiter Dicta (if present)": "any obiter dicta or Not specified in the document",
            "Confidence": {{
                "Case Title & Citation": 95,
                "Bench / Court": 90,
                "Facts of the Case": 85,
                "Issues Framed": 80,
                "Arguments by Parties": 75,
                "Court's Analysis / Reasoning": 85,
                "Final Decision (Ratio Decidendi)": 90,
                "Obiter Dicta (if present)": 60
            }}
        }}

        Case text:
        {truncated_text}
        """

        try:
            response = self.client.chat.completions.create(  # Updated syntax
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": """You are a legal expert analyzing Indian Supreme Court judgments. 
                    Extract the following information and provide confidence scores (0-100) for each field:
                    1. Case Title & Citation
                    2. Bench / Court
                    3. Date
                    4. Facts of the Case
                    5. Issues Framed
                    6. Arguments by Parties
                    7. Court's Analysis / Reasoning
                    8. Final Decision (Ratio Decidendi)
                    9. Obiter Dicta (if present)
                    
                    Return a JSON object with these fields and a 'Confidence' object with scores for each field."""},
                    {"role": "user", "content": f"Extract case details from:\n\n{case_text[:8000]}"}  # Limit text length
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure all required fields are present
            required_fields = [
                "Case Title & Citation", "Bench / Court", "Facts of the Case",
                "Issues Framed", "Arguments by Parties", "Court's Analysis / Reasoning",
                "Final Decision (Ratio Decidendi)", "Obiter Dicta (if present)", "Confidence"
            ]
            
            for field in required_fields:
                if field not in result:
                    if field == "Confidence":
                        # Initialize confidence object if missing
                        result["Confidence"] = {
                            "Case Title & Citation": 50,
                            "Bench / Court": 50,
                            "Facts of the Case": 50,
                            "Issues Framed": 50,
                            "Arguments by Parties": 50,
                            "Court's Analysis / Reasoning": 50,
                            "Final Decision (Ratio Decidendi)": 50,
                            "Obiter Dicta (if present)": 50
                        }
                    else:
                        result[field] = "Not specified in the document"
            
            return result
            
        except Exception as e:
            print(f"Error extracting case details: {str(e)}")
            return self._create_error_response()
            
            response_text = completion.choices[0].message.content
            
            try:
                case_details = json.loads(response_text if response_text is not None else "")
            except json.JSONDecodeError as json_err:
                print(f"JSON parsing error: {str(json_err)}")
                cleaned_text = self._clean_json_text(response_text if response_text is not None else "")
                try:
                    case_details = json.loads(cleaned_text)
                except Exception as e:
                    print(f"Failed to parse cleaned JSON: {str(e)}")
                    return self._extract_fallback_method(case_text)

            # Validate and ensure all fields are present
            required_fields = [
                "Case Title & Citation", "Bench / Court", "Facts of the Case",
                "Issues Framed", "Arguments by Parties", "Court's Analysis / Reasoning",
                "Final Decision (Ratio Decidendi)", "Obiter Dicta (if present)"
            ]
            
            # Ensure all fields exist and have valid content
            for field in required_fields:
                if field not in case_details or not case_details[field] or \
                   case_details[field].isspace() or \
                   case_details[field].lower() in ["null", "none", "undefined"]:
                    case_details[field] = "Not specified in the document."
            
            return case_details
            
        except Exception as e:
            print(f"API call failed: {str(e)}")
            return self._extract_fallback_method(case_text)

    def _extract_fallback_method(self, case_text: str) -> Dict[str, str]:
        """
        Fallback method to extract case details when the primary method fails
        """
        print("Using fallback extraction method...")
        result = {}
        fields = [
            "Case Title & Citation", "Bench / Court", "Facts of the Case",
            "Issues Framed", "Arguments by Parties", "Court's Analysis / Reasoning",
            "Final Decision (Ratio Decidendi)", "Obiter Dicta (if present)"
        ]
        
        # Process text in larger chunks for the fallback method
        text_chunk = case_text[:25000]  # Increased chunk size
        
        for field in fields:
            try:
                field_prompt = f"""
                Extract only the {field} from this legal case text.
                Provide a clear, concise response.
                If the information is not found, respond with exactly "Not specified in the document."

                Case text:
                {text_chunk}
                """
                
                completion = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a legal expert. Provide clear, direct answers."},
                        {"role": "user", "content": field_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000,  # Increased token limit for response
                    extra_headers={
                        "HTTP-Referer": "https://legal-case-comprehension.com",
                        "X-Title": "Legal Case Comprehension System"
                    }
                )
                
                field_content = completion.choices[0].message.content.strip() if completion.choices[0].message.content else "Not specified in the document"
                
                # Clean up the response
                if field_content.lower().startswith(field.lower()):
                    field_content = field_content[len(field):].strip()
                    for sep in [":", "-", "="]:
                        if field_content.startswith(sep):
                            field_content = field_content[1:].strip()
                
                if not field_content or field_content.isspace():
                    field_content = "Not specified in the document."
                
                result[field] = field_content
                time.sleep(2)  # Delay between field extractions
                
            except Exception as e:
                print(f"Failed to extract {field}: {str(e)}")
                result[field] = "Not specified in the document."
        
        return result
    
    # The rest of the methods remain unchanged
    def _clean_json_text(self, text: str) -> str:
        """
        Clean the response text to ensure it's valid JSON
        """
        # Remove markdown code block indicators if present
        text = re.sub(r'```json', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        # If text doesn't start with {, try to find the first {
        if not text.startswith('{'):
            start_idx = text.find('{')
            if start_idx >= 0:
                text = text[start_idx:]
        
        # If text doesn't end with }, try to find the last }
        if not text.endswith('}'):
            end_idx = text.rfind('}')
            if end_idx >= 0:
                text = text[:end_idx+1]
        
        return text
    
    def _create_structured_response(self, text: str) -> Dict[str, str]:
        """
        Create a structured response from unstructured text by looking for key fields
        """
        result = {}
        fields = [
            "Case Title & Citation", "Bench / Court", "Facts of the Case",
            "Issues Framed", "Arguments by Parties", "Court's Analysis / Reasoning",
            "Final Decision (Ratio Decidendi)", "Obiter Dicta"
        ]
        
        # Try to extract each field from the text
        for field in fields:
            field_name = field
            if field == "Obiter Dicta":
                field_name = "Obiter Dicta (if present)"
                
            # Look for the field in the text
            field_start = text.find(field)
            if field_start >= 0:
                next_field_start = len(text)
                for next_field in fields:
                    if next_field != field:
                        pos = text.find(next_field, field_start + len(field))
                        if pos > field_start and pos < next_field_start:
                            next_field_start = pos
                
                field_content = text[field_start + len(field):next_field_start].strip()
                # Remove common separators
                for sep in [":", "-", "="]:
                    if field_content.startswith(sep):
                        field_content = field_content[1:].strip()
                
                result[field_name] = field_content
            else:
                result[field_name] = "Not specified in the document."
        
        return result
    
    def _create_error_response(self) -> Dict[str, str]:
        """
        Create a standard error response
        """
        return {
            "Case Title & Citation": "Unable to extract - API error",
            "Bench / Court": "Unable to extract - API error",
            "Facts of the Case": "Unable to extract - API error",
            "Issues Framed": "Unable to extract - API error",
            "Arguments by Parties": "Unable to extract - API error",
            "Court's Analysis / Reasoning": "Unable to extract - API error",
            "Final Decision (Ratio Decidendi)": "Unable to extract - API error",
            "Obiter Dicta (if present)": "Unable to extract - API error"
        }
    
    def process_cases(self, cases: List[str], file_path: str = None) -> List[tuple]:
        """
        Process a single case from a PDF and extract details
        Returns a list with one tuple (case_details, filename)
        """
        results = []
        
        # We should only have one case per PDF now
        case = cases[0]
        
        print(f"Extracting details for judgment...")
        
        # Extract fingerprint if present
        fingerprint = None
        if case.startswith("DOCUMENT_FINGERPRINT:"):
            first_line_end = case.find('\n')
            if first_line_end > 0:
                fingerprint_line = case[:first_line_end]
                fingerprint = fingerprint_line.replace("DOCUMENT_FINGERPRINT:", "").strip()
                # Remove the fingerprint line from the case text
                case = case[first_line_end+1:]
        
        # Generate a filename for this case based on the PDF name
        if file_path:
            base_name = os.path.basename(file_path)
            filename = f"{os.path.splitext(base_name)[0]}_summary.json"
        else:
            # Fallback if no file path is provided
            filename = f"judgment_{fingerprint}_summary.json" if fingerprint else f"judgment_summary.json"
        
        # Check if this case analysis already exists
        existing_file = self._find_existing_case_file(case)
        if existing_file:
            print(f"Analysis for this judgment already exists. Using existing analysis...")
            with open(existing_file, 'r') as f:
                case_details = json.load(f)
            results.append((case_details, os.path.basename(existing_file)))
            return results
            
        # Extract the 8 key fields using LLM
        case_details = self.extract_case_details(case)
        results.append((case_details, filename))
        
        return results
    
    def _find_existing_case_file(self, case_text: str) -> str:
        """
        Find the filename of an existing case analysis that matches this case
        """
        results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Results")
        if not os.path.exists(results_dir):
            return ""
            
        # Extract key identifying information from the case
        case_signature = self._generate_case_signature(case_text)
        
        best_match = None
        best_score = 0.7  # Minimum threshold for considering a match
        
        for filename in os.listdir(results_dir):
            if filename.endswith('_summary.json'):
                try:
                    with open(os.path.join(results_dir, filename), 'r') as f:
                        existing_case = json.load(f)
                        
                        # Compare title and facts to find the best match
                        title_score = self._text_similarity(
                            existing_case.get("Case Title & Citation", ""), 
                            case_signature
                        )
                        
                        facts_score = self._text_similarity(
                            existing_case.get("Facts of the Case", "")[:200], 
                            case_text[:200]
                        )
                        
                        # Calculate combined score with more weight on title
                        score = (title_score * 0.7) + (facts_score * 0.3)
                        
                        if score > best_score:
                            best_score = score
                            best_match = os.path.join(results_dir, filename)
                except Exception as e:
                    print(f"Error checking existing case file {filename}: {str(e)}")
                    continue
                    
        return best_match if best_match else ""
    
    def _generate_case_signature(self, case_text: str) -> str:
        """
        Generate a signature for a case based on its content
        """
        # Look for parties (X vs Y pattern)
        parties_match = re.search(r'([A-Za-z\s\.]+)\s+(?:versus|vs\.)\s+([A-Za-z\s\.]+)', case_text[:1000])
        parties = parties_match.group(0) if parties_match else ""
        
        # Look for case numbers
        case_number_match = re.search(r'(?:CIVIL|CRIMINAL|WRIT PETITION|APPEAL) NO\.\s*\d+\s*OF\s*\d{4}', case_text[:1000])
        case_number = case_number_match.group(0) if case_number_match else ""
        
        # Get the first 200 characters as a basic signature
        signature = case_text[:200]
        
        if case_number:
            signature = case_number + " " + signature
            
        if parties:
            signature = parties + " " + signature
            
        return signature
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate a simple similarity score between two text strings
        """
        if not text1 or not text2:
            return 0
            
        # Convert to lowercase and remove punctuation
        text1 = re.sub(r'[^\w\s]', '', text1.lower())
        text2 = re.sub(r'[^\w\s]', '', text2.lower())
        
        # Split into words
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0