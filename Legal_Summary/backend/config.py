from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def validate_api_key(self):
        """Validate that API key is set before making requests."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please:\n"
                "1. Create a .env file in the Backend folder\n"
                "2. Add: OPENAI_API_KEY=your_api_key_here\n"
                "3. Get your API key from: https://platform.openai.com/api-keys"
            )

settings = Settings()
