class InvalidPDFError(Exception):
    """Exception raised when a PDF is invalid, corrupted, or cannot be parsed."""
    pass

class OpenAIExtractionError(Exception):
    """Exception raised when OpenAI API extraction fails."""
    pass
