import PyPDF2
import re
from typing import List, Dict, Tuple
import os
import hashlib
from openai import OpenAI

class LegalDocumentProcessor:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

        # Minimum case length (in characters)
        self.min_case_length = 800
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using PyPDF2
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def _get_document_fingerprint(self, text: str) -> str:
        """
        Generate a fingerprint for the document to identify it uniquely
        """
        # Get the first 1000 characters and hash them
        text_sample = text[:1000].strip()
        return hashlib.md5(text_sample.encode()).hexdigest()
    
    def process_document(self, pdf_path: str) -> List[str]:
        """
        Process PDF document - treat each PDF as a single judgment
        """
        # Extract text
        full_text = self.extract_text_from_pdf(pdf_path)
        
        # Generate a fingerprint for the document
        fingerprint = self._get_document_fingerprint(full_text)
        
        # Add fingerprint to the beginning of the text
        full_text_with_fingerprint = f"DOCUMENT_FINGERPRINT: {fingerprint}\n{full_text}"
        
        # Return as a single case
        return [full_text_with_fingerprint]

    def enhance_extraction_with_gpt(self, text):
        """Use GPT to enhance text extraction if available"""
        if not self.client:
            return text
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Clean and format this legal text, preserving structure."},
                    {"role": "user", "content": text[:4000]}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT enhancement failed: {e}")
            return text