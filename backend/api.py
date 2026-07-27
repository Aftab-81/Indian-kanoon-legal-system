from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pdf_processor import LegalDocumentProcessor
from case_extractor import CaseExtractor
from case_index import CaseIndex
from ikapi import IKApi, FileStorage
from exceptions import InvalidPDFError, OpenAIExtractionError
import os
import json
import time
import uuid
import argparse
from serpapi import GoogleSearch
from logger_setup import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure upload folder
UPLOAD_FOLDER = './Uploads'
RESULTS_FOLDER = './Results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Initialize processors
processor = LegalDocumentProcessor()
extractor = CaseExtractor()

# Initialize the case index
case_index = CaseIndex()

# Rebuild the index on startup
case_index.rebuild_index(RESULTS_FOLDER)

# Initialize Indian Kanoon API
ik_storage = FileStorage('./IKResults')

# Create a mock args object for IKApi
class IKArgs:
    def __init__(self, token):
        self.token = token
        self.maxcites = 5
        self.maxcitedby = 5
        self.orig = False
        self.maxpages = 2
        self.pathbysrc = True
        self.numworkers = 1
        self.addedtoday = False
        self.fromdate = None
        self.todate = None
        self.sortby = "mostrecent"

# Create directory for IK results
os.makedirs('./IKResults', exist_ok=True)

# Helper functions
def extract_party_names(title):
    """Extract party names from case title (e.g., "A vs B")"""
    vs_patterns = [" vs ", " versus ", " v. "]
    for pattern in vs_patterns:
        if pattern in title:
            parts = title.split(pattern, 1)
            if len(parts) == 2:
                return (parts[0].strip(), parts[1].strip())
    return None

def calculate_similarity(text1, text2):
    """Calculate simple text similarity ratio"""
    # Convert to sets of words for comparison
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0
        
    # Jaccard similarity: intersection / union
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

# Replace the find_duplicate_case function with this optimized version
def find_duplicate_case(case_details):
    """
    Check if a case with similar details already exists in the Results folder
    Returns the filename if found, None otherwise
    """
    # Use the index to find duplicates
    return case_index.find_duplicate(case_details)

# Helper function to extract sections from content - MOVED HERE BEFORE USAGE
def extract_section(content, section_type, proportion):
    """Extract a section of the content based on the section type"""
    if not content:
        return ""
    
    # Simple rule-based extraction based on content proportion
    # In a real implementation, this would use more sophisticated NLP
    lines = content.split('\n')
    total_lines = len(lines)
    
    if section_type == "facts":
        # Facts are usually at the beginning
        start = int(total_lines * 0.05)  # Skip the first 5% (usually headers)
        end = int(total_lines * (0.05 + proportion))
    elif section_type == "issues":
        # Issues usually follow facts
        start = int(total_lines * 0.25)
        end = int(total_lines * (0.25 + proportion))
    elif section_type == "arguments":
        # Arguments usually follow issues
        start = int(total_lines * 0.35)
        end = int(total_lines * (0.35 + proportion))
    elif section_type == "analysis":
        # Analysis usually follows arguments
        start = int(total_lines * 0.55)
        end = int(total_lines * (0.55 + proportion))
    elif section_type == "decision":
        # Decision is usually at the end
        start = int(total_lines * 0.8)
        end = total_lines
    else:
        # Default to the whole content
        start = 0
        end = total_lines
    
    # Ensure bounds are valid
    start = max(0, min(start, total_lines - 1))
    end = max(start + 1, min(end, total_lines))
    
    # Extract the section
    section = '\n'.join(lines[start:end])
    return section

# API Routes
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Endpoint to upload a PDF file for processing
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.endswith('.pdf'):
            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}.pdf"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            
            try:
                # Extract text from PDF (now treating as a single judgment)
                logger.info(f"Processing PDF: {file.filename}")
                cases = processor.process_document(file_path)
                logger.info(f"Extracted {len(cases)} case(s) from {file.filename}")
                
                # Process the judgment and save results
                logger.info(f"Starting case extraction with OpenAI for {file.filename}")
                case_results = extractor.process_cases(cases, file_path)
                logger.info(f"Extracted {len(case_results)} case result(s) for {file.filename}")
                
                case_summaries = []
                for i, (case_details, filename) in enumerate(case_results, 1):
                    # Check if this case already exists in Results folder
                    existing_file = find_duplicate_case(case_details)
                    
                    if existing_file:
                        # Use the existing file instead of creating a new one
                        logger.info(f"Case already exists as {existing_file}")
                        with open(os.path.join(RESULTS_FOLDER, existing_file), 'r') as f:
                            existing_case_data = json.load(f)
                        
                        case_summaries.append({
                            'id': i,
                            'title': existing_case_data.get('Case Title & Citation', f'Judgment {i}'),
                            'file': existing_file,
                            'status': "already analyzed"
                        })
                    else:
                        # Save to JSON file
                        output_file = os.path.join(RESULTS_FOLDER, filename)
                        with open(output_file, "w") as f:
                            json.dump(case_details, f, indent=2)
                        
                        # Add to index
                        case_index.add_case(filename, case_details)
                        
                        case_summaries.append({
                            'id': i,
                            'title': case_details.get('Case Title & Citation', f'Judgment {i}'),
                            'file': filename,
                            'status': "newly analyzed"
                        })
                
                # Clean up the uploaded file since we don't need it anymore
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Successfully processed judgment',
                    'cases': case_summaries
                })
                
            except InvalidPDFError as e:
                try:
                    os.remove(file_path)
                except:
                    pass
                logger.error(f"Invalid PDF Error: {str(e)}", exc_info=True)
                return jsonify({'error': f'Invalid or corrupted PDF. Unable to extract text. {str(e)}'}), 400
                
            except OpenAIExtractionError as e:
                try:
                    os.remove(file_path)
                except:
                    pass
                logger.error(f"OpenAI API Error: {str(e)}", exc_info=True)
                return jsonify({'error': f'OpenAI API extraction failed: {str(e)}'}), 502
                
            except Exception as e:
                # Clean up on error
                try:
                    os.remove(file_path)
                except:
                    pass
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                return jsonify({'error': f'Internal processing error: {str(e)}'}), 500
        
        return jsonify({'error': 'Invalid file format. Please upload a PDF file'}), 400
        
    except Exception as e:
        logger.error(f"Upload endpoint error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/google-search', methods=['POST'])
def google_search():
    """Endpoint to search Google using SerpAPI with restriction to legal terms"""
    # Check if GoogleSearch is available
    if GoogleSearch is None:
        return jsonify({
            'success': False, 
            'error': 'SerpAPI package not properly installed. Please run: pip install google-search-results'
        }), 500
    
    data = request.json
    logger.info(f"Received Google search request: {data}")
    
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    # Get API key from environment variable or request
    api_key = data.get('api_key') or os.environ.get('SERPAPI_API_KEY')
    
    if not api_key:
        return jsonify({'error': 'API key not found'}), 400
    
    original_query = data['query']
    
    # List of legal-related keywords to check against
    legal_keywords = [
        "law", "legal", "court", "judge", "judgment", "judicial", "justice", 
        "statute", "legislation", "constitution", "rights", "plaintiff", 
        "defendant", "petition", "appeal", "verdict", "ruling", "precedent",
        "jurisprudence", "jurisdiction", "litigation", "tribunal", "attorney",
        "advocate", "counsel", "prosecution", "defense", "bail", "tort", 
        "contract", "criminal", "civil", "property", "evidence", "testimony",
        "witness", "affidavit", "decree", "injunction", "writ", "summons"
    ]
    
    # Check if the query contains any legal terms
    contains_legal_term = any(keyword in original_query.lower() for keyword in legal_keywords)
    
    # If the query doesn't contain legal terms, check if it's a legal concept that might not be in our keywords
    if not contains_legal_term:
        # We'll proceed but add legal context to the search
        modified_query = f"{original_query} legal law court case"
        logger.info(f"Modified query to include legal context: {modified_query}")
    else:
        # Query already has legal terms, use as is
        modified_query = original_query
    
    logger.info(f"Searching Google for: {modified_query}")
    
    # Optional parameters
    engine = data.get('engine', 'google')
    num_results = data.get('num_results', 10)
    
    try:
        # Set up search parameters
        params = {
            "engine": engine,
            "q": modified_query,
            "api_key": api_key,
            "num": num_results,
            # Add a filter to focus on legal websites
            "lr": "lang_en",  # Restrict to English results
        }
        
        # Add any additional parameters from the request
        for key, value in data.items():
            if key not in ['query', 'api_key', 'engine', 'num_results']:
                params[key] = value
        
        # Perform the search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract organic results
        if 'organic_results' in results:
            # Post-process results to filter out non-legal content if needed
            filtered_results = []
            for result in results['organic_results']:
                # Check if the result seems to be related to legal content
                title = result.get('title', '').lower()
                snippet = result.get('snippet', '').lower()
                combined_text = title + ' ' + snippet
                
                # If the original query had legal terms or the result contains legal terms, include it
                if contains_legal_term or any(keyword in combined_text for keyword in legal_keywords):
                    filtered_results.append(result)
            
            return jsonify({
                'success': True,
                'results': filtered_results,
                'search_metadata': results.get('search_metadata', {}),
                'original_query': original_query,
                'modified_query': modified_query
            })
        else:
            return jsonify({
                'success': True,
                'results': [],
                'message': 'No results found'
            })
            
    except Exception as e:
        logger.error(f"Google search error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_existing_pdf():
    """
    Endpoint to process an existing PDF file (already on the server)
    """
    data = request.json
    if not data or 'file_path' not in data:
        return jsonify({'error': 'No file path provided'}), 400
    
    file_path = data['file_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    if not file_path.endswith('.pdf'):
        return jsonify({'error': 'Invalid file format. Please provide a PDF file'}), 400
    
    try:
        # Extract text from PDF (now treating as a single judgment)
        cases = processor.process_document(file_path)
        
        # Process the judgment and save results
        case_results = extractor.process_cases(cases, file_path)
        
        case_summaries = []
        for i, (case_details, filename) in enumerate(case_results, 1):
            # Save to JSON file
            output_file = os.path.join(RESULTS_FOLDER, filename)
            
            # Only write if the file doesn't exist
            if not os.path.exists(output_file):
                with open(output_file, "w") as f:
                    json.dump(case_details, f, indent=2)
                status = "newly analyzed"
            else:
                status = "already analyzed"
            
            case_summaries.append({
                'id': i,
                'title': case_details.get('Case Title & Citation', f'Judgment {i}'),
                'file': filename,
                'status': status
            })
        
        return jsonify({
            'success': True,
            'message': 'Successfully processed judgment',
            'cases': case_summaries
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cases', methods=['GET'])
def get_cases():
    """
    Endpoint to get a list of all processed cases
    """
    try:
        case_files = [f for f in os.listdir(RESULTS_FOLDER) if f.endswith('_summary.json')]
        cases = []
        
        for i, file in enumerate(case_files, 1):
            file_path = os.path.join(RESULTS_FOLDER, file)
            with open(file_path, 'r') as f:
                case_data = json.load(f)
                
            # Extract case ID from filename - this is causing the issue
            # The new filenames don't follow the old pattern with case_1, case_2, etc.
            # Let's use the index instead
            cases.append({
                'id': i,
                'title': case_data.get('Case Title & Citation', f'Case {i}'),
                'file': file
            })
        
        # Sort cases by ID
        cases.sort(key=lambda x: x['id'])
        
        return jsonify(cases)
    
    except Exception as e:
        print(f"Error in get_cases: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/case/<case_file>', methods=['GET'])
def get_case_details(case_file):
    """
    Endpoint to get details of a specific case
    """
    try:
        file_path = os.path.join(RESULTS_FOLDER, case_file)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Case not found'}), 404
            
        with open(file_path, 'r') as f:
            case_data = json.load(f)
            
        return jsonify(case_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/case/<filename>', methods=['DELETE'])
def delete_case(filename):
    """Delete a case file and remove it from the index"""
    try:
        # Validate filename to prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({"success": False, "error": "Invalid filename"}), 400
            
        # Build the full path to the file
        file_path = os.path.join(RESULTS_FOLDER, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "File not found"}), 404
            
        # Delete the file
        os.remove(file_path)
        
        # Also delete the corresponding PDF if it exists
        pdf_filename = filename.replace('_summary.json', '.pdf')
        pdf_path = os.path.join(RESULTS_FOLDER, pdf_filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        # Remove from the index
        case_index.remove_case(filename)
        
        return jsonify({"success": True, "message": "Case deleted successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/case/<case_file>/remarks', methods=['POST'])
def update_case_remarks(case_file):
    """
    Endpoint to update remarks for a specific case
    """
    try:
        # Validate filename to prevent directory traversal
        if '..' in case_file or '/' in case_file or '\\' in case_file:
            return jsonify({"success": False, "error": "Invalid filename"}), 400
            
        # Get the remarks from the request
        data = request.json
        if not data or 'remarks' not in data:
            return jsonify({"success": False, "error": "No remarks provided"}), 400
            
        remarks = data['remarks']
        
        # Build the full path to the file
        file_path = os.path.join(RESULTS_FOLDER, case_file)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "File not found"}), 404
            
        # Read the existing case data
        with open(file_path, 'r') as f:
            case_data = json.load(f)
            
        # Update the remarks
        case_data['Remarks'] = remarks
        
        # Write the updated data back to the file
        with open(file_path, 'w') as f:
            json.dump(case_data, f, indent=2)
            
        return jsonify({"success": True, "message": "Remarks updated successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Indian Kanoon API Routes
@app.route('/api/ik-search', methods=['POST'])
def ik_search():
    """Endpoint to search Indian Kanoon"""
    data = request.json
    print(f"Received search request: {data}")
    
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    # Use environment variable for token if not provided
    token = data.get('token') or os.environ.get('INDIA_KANNON_API_KEY')
    print(f"Using token: {token[:5]}...{token[-5:] if token else None}")
    
    if not token:
        return jsonify({'error': 'API token not found'}), 400
    
    query = data['query']
    print(f"Searching for: {query}")
    
    # Optional parameters
    max_pages = data.get('max_pages', 2)
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    
    # Initialize IKApi with the token
    args = IKArgs(token)
    args.maxpages = min(max_pages, 10)  # Limit to 10 pages max
    args.fromdate = from_date
    args.todate = to_date
    
    ikapi = IKApi(args, ik_storage)
    
    try:
        # Perform the search
        print("Calling IKApi search...")
        results = ikapi.search(query, 0, args.maxpages)
        print(f"Search results received (length: {len(results) if results else 0})")
        
        # Parse the JSON results
        parsed_results = json.loads(results)
        
        # Ensure we're returning the docs array
        if 'docs' in parsed_results and isinstance(parsed_results['docs'], list):
            return jsonify({
                'success': True,
                'results': parsed_results['docs']  # Return just the docs array
            })
        else:
            return jsonify({
                'success': True,
                'results': parsed_results  # Return the whole object if no docs array
            })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ik-document/<int:doc_id>', methods=['GET'])
def ik_document(doc_id):
    """Endpoint to fetch a specific document from Indian Kanoon"""
    # Use environment variable for token if not provided in request
    token = request.args.get('token') or os.environ.get('INDIA_KANNON_API_KEY')
    
    if not token:
        return jsonify({'error': 'API token not found'}), 400
    
    # Initialize IKApi with the token
    args = IKArgs(token)
    ikapi = IKApi(args, ik_storage)
    
    try:
        # Fetch the document
        doc_result = ikapi.fetch_doc(doc_id)
        
        # Print the raw response for debugging
        print("Raw document response:", doc_result)
        
        # Parse the JSON result
        parsed_doc = json.loads(doc_result)
        
        # Print the entire document structure for debugging
        print("Document structure keys:", list(parsed_doc.keys()))
        
        # Extract the document content
        # First check if the content is directly in the 'doc' field
        content = ''
        if 'doc' in parsed_doc and parsed_doc['doc']:
            content = parsed_doc['doc']
        # Check other possible field names
        elif 'text' in parsed_doc:
            content = parsed_doc['text']
        elif 'content' in parsed_doc:
            content = parsed_doc['content']
        elif 'judgment' in parsed_doc:
            content = parsed_doc['judgment']
        
        # Clean up the content
        if content:
            content = content.strip()
            import re
            # Replace common block tags with newlines to preserve structure
            content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</p>', '\n\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</div>', '\n\n', content, flags=re.IGNORECASE)
            # Remove all other HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Decode HTML entities if any
            import html as html_lib
            content = html_lib.unescape(content)
            # Clean up extra newlines and spaces
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.strip()
            
        # Use the CaseExtractor to process the content with OpenAI LLM
        # This reuses the same extraction logic used for PDF uploads
        case_details = {}
        if content:
            try:
                # Use the existing CaseExtractor class
                case_details = extractor.extract_case_details(content)
                
                # Add the title, court and date from the API response if available
                if 'title' in parsed_doc and not case_details.get('Case Title & Citation'):
                    case_details['Case Title & Citation'] = parsed_doc.get('title', '')
                    
                if 'court' in parsed_doc and not case_details.get('Bench / Court'):
                    case_details['Bench / Court'] = parsed_doc.get('court', '')
                    
                if 'date' in parsed_doc and not case_details.get('Date'):
                    case_details['Date'] = parsed_doc.get('date', '')
                    
                print("AI-extracted case details:", case_details)
            except Exception as e:
                print(f"Error using AI extraction: {str(e)}")
                # Fall back to rule-based extraction if AI fails
                case_details = {
                    "Case Title & Citation": parsed_doc.get('title', ''),
                    "Bench / Court": parsed_doc.get('court', ''),
                    "Date": parsed_doc.get('date', ''),
                    "Facts of the Case": extract_section(content, "facts", 0.2),
                    "Issues Framed": extract_section(content, "issues", 0.1),
                    "Arguments by Parties": extract_section(content, "arguments", 0.2),
                    "Court's Analysis / Reasoning": extract_section(content, "analysis", 0.3),
                    "Final Decision (Ratio Decidendi)": extract_section(content, "decision", 0.2),
                    "Obiter Dicta (if present)": "Not specified in the document"
                }
        else:
            # If no content is available, use metadata from the API response
            case_details = {
                "Case Title & Citation": parsed_doc.get('title', ''),
                "Bench / Court": parsed_doc.get('court', ''),
                "Date": parsed_doc.get('date', ''),
                "Facts of the Case": "Not available in the document",
                "Issues Framed": "Not available in the document",
                "Arguments by Parties": "Not available in the document",
                "Court's Analysis / Reasoning": "Not available in the document",
                "Final Decision (Ratio Decidendi)": "Not available in the document",
                "Obiter Dicta (if present)": "Not specified in the document"
            }
        
        # Format each section with HTML
        formatted_sections = {}
        import re
        for key, value in case_details.items():
            if key == "Confidence":
                # Skip the confidence scores
                continue
                
            if value and isinstance(value, str) and value.strip() and value != "Not specified in the document" and value != "Not available in the document":
                if key in ["Case Title & Citation", "Bench / Court", "Date"]:
                    # Strip any HTML tags from title and court, and do not add paragraph tags
                    # because CaseDetails.jsx renders these as plain text
                    clean_val = re.sub(r'<[^>]+>', '', value).strip()
                    # Also unescape HTML entities like &amp;
                    import html as html_lib
                    clean_val = html_lib.unescape(clean_val)
                    formatted_sections[key] = clean_val
                else:
                    # Replace newlines with <br> tags
                    formatted_value = value.replace('\n', '<br>')
                    # Add paragraph tags
                    formatted_value = '<p>' + formatted_value.replace('<br><br>', '</p><p>') + '</p>'
                    formatted_sections[key] = formatted_value
            else:
                formatted_sections[key] = "Not specified in the document"
        
        # Also keep the original full content for reference
        if content:
            # Format the full content with HTML (content is already stripped of original HTML)
            formatted_content = content.replace('\n', '<br>')
            formatted_content = '<p>' + formatted_content.replace('<br><br>', '</p><p>') + '</p>'
        else:
            formatted_content = "<p>No content available for this document.</p>"
        
        # Clean title for structured doc as well
        clean_title = re.sub(r'<[^>]+>', '', parsed_doc.get('title', '')).strip()
        import html as html_lib
        clean_title = html_lib.unescape(clean_title)
        
        # Create the structured document
        structured_doc = {
            'title': clean_title,
            'court': parsed_doc.get('court', ''),
            'date': parsed_doc.get('date', ''),
            'content': formatted_content,  # Keep the full content
            'sections': formatted_sections  # Add the structured sections
        }
        
        # Return the structured document
        return jsonify({
            'success': True,
            'document': structured_doc
        })
    except Exception as e:
        print("Error fetching document:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/ik-test', methods=['GET'])
def ik_test():
    """Test endpoint for Indian Kanoon API connectivity"""
    token = os.environ.get('INDIA_KANNON_API_KEY')
    if not token:
        return jsonify({'error': 'API token not found'}), 400
    
    args = IKArgs(token)
    ikapi = IKApi(args, ik_storage)
    
    try:
        # Try a simple search
        results = ikapi.search("test", 0, 1)
        return jsonify({
            'success': True,
            'message': 'Connection successful',
            'response_length': len(results) if results else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ik-save-document', methods=['POST'])
def save_ik_document():
    """Endpoint to save an Indian Kanoon document to the Results folder"""
    data = request.json
    
    if not data or 'document' not in data:
        return jsonify({'error': 'No document provided'}), 400
    
    document = data['document']
    
    try:
        # Extract case details from the document
        case_details = {}
        
        # Use the sections if available, otherwise use the document fields
        if 'sections' in document and document['sections']:
            case_details = document['sections']
        else:
            # Create basic case details from document fields
            case_details = {
                'Case Title & Citation': document.get('title', ''),
                'Bench / Court': document.get('court', ''),
                'Facts of the Case': 'Extracted from Indian Kanoon',
                'Issues Framed': 'See full document for details',
                'Arguments by Parties': 'See full document for details',
                'Court\'s Analysis / Reasoning': 'See full document for details',
                'Final Decision (Ratio Decidendi)': 'See full document for details',
                'Obiter Dicta (if present)': 'Not specified in the document'
            }
        
        # Add source information
        case_details['Source'] = 'Indian Kanoon'
        
        # Generate a unique filename
        filename = f"{uuid.uuid4().hex}_summary.json"
        
        # Check if this case already exists
        existing_file = find_duplicate_case(case_details)
        
        if existing_file:
            # Return the existing file information
            with open(os.path.join(RESULTS_FOLDER, existing_file), 'r') as f:
                existing_case_data = json.load(f)
                
            return jsonify({
                'success': True,
                'message': 'Case already exists in the database',
                'file': existing_file,
                'title': existing_case_data.get('Case Title & Citation', 'Existing Case')
            })
        
        # Save to JSON file
        output_file = os.path.join(RESULTS_FOLDER, filename)
        with open(output_file, "w") as f:
            json.dump(case_details, f, indent=2)
        
        # Add to index
        case_index.add_case(filename, case_details)
        
        return jsonify({
            'success': True,
            'message': 'Document saved successfully',
            'file': filename,
            'title': case_details.get('Case Title & Citation', 'Indian Kanoon Document')
        })
        
    except Exception as e:
        print(f"Error saving document: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Changed to explicit port 8000


