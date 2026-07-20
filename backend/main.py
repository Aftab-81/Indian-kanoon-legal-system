from pdf_processor import LegalDocumentProcessor
from case_extractor import CaseExtractor
import json
import os
import time

def main():
    processor = LegalDocumentProcessor()
    extractor = CaseExtractor()
    
    # Use relative path for PDF
    pdf_path = "./Merged.pdf"  # Changed from "./Documents/Merged.pdf"
    
    # Verify if PDF file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        print("Please ensure the PDF file is placed in the Documents folder")
        return
        
    try:
        # Extract cases from PDF
        cases = processor.process_document(pdf_path)
        print(f"Found {len(cases)} cases in the document")
        
        # Create output directory if it doesn't exist using relative path
        results_dir = "./Results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Process each case and save results
        case_results = extractor.process_cases(cases, pdf_path)
        
        for i, (case_details, filename) in enumerate(case_results, 1):
            # Save to JSON file with relative path
            output_file = os.path.join(results_dir, filename)
            
            # Only write the file if it doesn't already exist
            if not os.path.exists(output_file):
                with open(output_file, "w") as f:
                    json.dump(case_details, f, indent=2)
                print(f"Case {i} details saved to {output_file}")
            else:
                print(f"Case {i} details already exist at {output_file}")
            
    except Exception as e:
        print(f"Error processing document: {str(e)}")

if __name__ == "__main__":
    main()