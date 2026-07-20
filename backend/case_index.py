import json
import os

class CaseIndex:
    def __init__(self):
        self.index_file = 'case_index.json'
        self.cases = {}  # Changed from self.index to self.cases
        self.load_index()
    
    def load_index(self):
        """Load the case index from file"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r') as f:
                    self.cases = json.load(f)  # Changed from self.index
        except Exception as e:
            print(f"Error loading index: {str(e)}")
            self.cases = {}
    
    def save_index(self):
        """Save the case index to file"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.cases, f, indent=2)  # Changed from self.index
        except Exception as e:
            print(f"Error saving index: {str(e)}")
    
    def add_case(self, filename, case_details):
        """Add a case to the index"""
        try:
            # Helper function to extract text value
            def get_text_value(content):
                """Extract text value from content that might be a dict or string"""
                if isinstance(content, dict):
                    if 'Value' in content:
                        return content['Value']
                    return str(content)
                return str(content) if content else ""
            
            # Extract values safely
            title = get_text_value(case_details.get('Case Title & Citation', ''))
            facts = get_text_value(case_details.get('Facts of the Case', ''))
            
            # Create a searchable text representation
            document = f"Title: {title}\nFacts: {facts[:500]}"
            
            self.cases[filename] = {  # Changed from self.index
                'title': title,
                'facts_preview': facts[:500],
                'document': document,
                'full_details': case_details
            }
            
            self.save_index()
            
        except Exception as e:
            print(f"Error adding case to index: {str(e)}")
            # Don't fail the whole operation if indexing fails
    
    def find_duplicate(self, case_details):
        """Find if a similar case already exists"""
        try:
            # Helper function to extract text value
            def get_text_value(content):
                """Extract text value from content that might be a dict or string"""
                if isinstance(content, dict):
                    if 'Value' in content:
                        return content['Value']
                    return str(content)
                return str(content) if content else ""
            
            new_title = get_text_value(case_details.get('Case Title & Citation', '')).lower()
            
            # Search through existing cases
            for filename, indexed_case in self.cases.items():  # Changed from self.index
                existing_title = indexed_case['title'].lower()
                
                # Check title similarity
                title_similarity = self._calculate_similarity(new_title, existing_title)
                
                if title_similarity > 0.8:  # 80% similarity threshold
                    return filename
            
            return None
            
        except Exception as e:
            print(f"Error finding duplicate: {str(e)}")
            return None
    
    def remove_case(self, filename):
        """Remove a case from the index"""
        try:
            if filename in self.cases:  # Changed from self.index
                del self.cases[filename]
                self.save_index()
        except Exception as e:
            print(f"Error removing case from index: {str(e)}")
    
    def rebuild_index(self, results_folder):
        """Rebuild the entire index from the Results folder"""
        try:
            self.cases = {}  # Changed from self.index
            
            for filename in os.listdir(results_folder):
                if filename.endswith('_summary.json'):
                    filepath = os.path.join(results_folder, filename)
                    with open(filepath, 'r') as f:
                        case_details = json.load(f)
                    self.add_case(filename, case_details)
            
            print(f"Index rebuilt with {len(self.cases)} cases")  # Changed from self.index
        except Exception as e:
            print(f"Error rebuilding index: {str(e)}")
    
    def _calculate_similarity(self, text1, text2):
        """Calculate Jaccard similarity between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0