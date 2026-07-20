import requests
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api"
SAMPLE_PDF_PATH = "admin_judgement_file_judgement_pdf_2025_volume 3_Part II_2025_3_325-340_1743053872 (1).pdf"  # Update with your test PDF path

def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_summarize_short():
    """Test short summary with focus on facts."""
    print_section("TEST 1: Short Summary - Focus on Facts")
    
    preferences = {
        "summary_length": "short",
        "focus_area": ["facts", "evidence"]
    }
    
    try:
        with open(SAMPLE_PDF_PATH, 'rb') as pdf:
            files = {'pdf_file': pdf}
            data = {'preferences': json.dumps(preferences)}
            
            response = requests.post(f"{BASE_URL}/summarize", files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            print("✓ Success!")
            print(json.dumps(result, indent=2))
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
    except FileNotFoundError:
        print(f"✗ PDF file not found: {SAMPLE_PDF_PATH}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def test_summarize_medium():
    """Test medium summary with multiple focus areas."""
    print_section("TEST 2: Medium Summary - Multiple Focus Areas")
    
    preferences = {
        "summary_length": "medium",
        "focus_area": ["arguments", "legal reasoning", "precedents"]
    }
    
    try:
        with open(SAMPLE_PDF_PATH, 'rb') as pdf:
            files = {'pdf_file': pdf}
            data = {'preferences': json.dumps(preferences)}
            
            response = requests.post(f"{BASE_URL}/summarize", files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            print("✓ Success!")
            print(f"\nCase Title: {result['metadata']['case_title']}")
            print(f"Court: {result['metadata']['court_name']}")
            print(f"Judges: {', '.join(result['metadata']['judge_names'])}")
            print(f"\nSummary:\n{result['metadata']['summary']}")
            print(f"\nSections: {', '.join(result['metadata']['sections_invoked'])}")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
    except FileNotFoundError:
        print(f"✗ PDF file not found: {SAMPLE_PDF_PATH}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def test_summarize_detailed():
    """Test detailed summary."""
    print_section("TEST 3: Detailed Summary")
    
    preferences = {
        "summary_length": "detailed",
        "focus_area": ["facts", "arguments", "evidence", "legal reasoning", "precedents"]
    }
    
    try:
        with open(SAMPLE_PDF_PATH, 'rb') as pdf:
            files = {'pdf_file': pdf}
            data = {'preferences': json.dumps(preferences)}
            
            response = requests.post(f"{BASE_URL}/summarize", files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            print("✓ Success!")
            print(f"\nDetailed Available: {result['detailed_available']}")
            print(f"\nFull Metadata:\n{json.dumps(result['metadata'], indent=2)}")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
    except FileNotFoundError:
        print(f"✗ PDF file not found: {SAMPLE_PDF_PATH}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def test_detailed_endpoint():
    """Test the comprehensive detailed summary endpoint."""
    print_section("TEST 4: Comprehensive Detailed Summary Endpoint")
    
    try:
        with open(SAMPLE_PDF_PATH, 'rb') as pdf:
            files = {'pdf_file': pdf}
            
            response = requests.post(f"{BASE_URL}/summarize/detailed", files=files)
            
        if response.status_code == 200:
            result = response.json()
            print("✓ Success!")
            
            # Print key sections
            print(f"\n📋 Case Title: {result['case_title']}")
            print(f"\n📅 Important Dates:")
            print(json.dumps(result['important_dates'], indent=2))
            
            print(f"\n⚖️ Court & Judge:")
            print(json.dumps(result['court_and_judge'], indent=2))
            
            print(f"\n📜 Charges & Sections:")
            for charge in result['charges_and_sections'][:3]:  # First 3
                print(f"  - {charge['section']}: {charge['description']}")
            
            print(f"\n📝 Brief Facts:")
            print(f"{result['brief_facts'][:300]}...")
            
            print(f"\n❓ Key Issues:")
            for issue in result['key_issues'][:2]:  # First 2
                print(f"  - {issue}")
            
            print(f"\n⚡ Risk Flags:")
            print(json.dumps(result['risk_flags'], indent=2))
            
            print(f"\n👥 Extracted Entities:")
            print(f"  Accused: {', '.join(result['extracted_entities'].get('accused', []))}")
            print(f"  Victim: {', '.join(result['extracted_entities'].get('victim', []))}")
            print(f"  Witnesses: {', '.join(result['extracted_entities'].get('witnesses', [])[:5])}")
            
            print(f"\n📄 One-Page Summary for Judges:")
            print(result['one_page_summary_for_judges'])
            
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
    except FileNotFoundError:
        print(f"✗ PDF file not found: {SAMPLE_PDF_PATH}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def create_sample_pdf_guide():
    """Print guide for creating sample PDF."""
    print_section("Setup: Sample PDF Required")
    print("""
To run these tests, you need a legal case PDF file.

Options:
1. Place your own case PDF at: d:\\Projects\\Judge_Project\\Backend\\sample_case.pdf
2. Or update SAMPLE_PDF_PATH variable in this script to point to your PDF
3. Download sample from: https://main.sci.gov.in/judgments (Supreme Court of India)

Sample PDF structure should contain:
- Case title and details
- Court name and judges
- Facts of the case
- Arguments (prosecution/defense)
- Evidence details
- Legal reasoning
- Final judgment

Once ready, run: python test_demo.py
    """)

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                   CASE SUMMARIZATION BACKEND - DEMO TESTS                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check if sample PDF exists
    if not Path(SAMPLE_PDF_PATH).exists():
        create_sample_pdf_guide()
        exit(1)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL.rsplit('/', 1)[0]}/docs")
        if response.status_code != 200:
            print("⚠️  Warning: Server might not be running at http://localhost:8000")
            print("   Start server: python app.py\n")
    except:
        print("✗ Error: Cannot connect to server at http://localhost:8000")
        print("   Make sure to start the server first: python app.py\n")
        exit(1)
    
    # Run all tests
    try:
        test_summarize_short()
        test_summarize_medium()
        test_summarize_detailed()
        test_detailed_endpoint()
        
        print_section("All Tests Completed")
        print("✓ Demo testing finished successfully!")
        
    except KeyboardInterrupt:
        print("\n\n✗ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {str(e)}")
