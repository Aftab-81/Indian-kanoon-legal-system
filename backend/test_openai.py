from openai import OpenAI
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a custom HTTP client without proxies
http_client = httpx.Client()

# Initialize the client with the custom HTTP client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    http_client=http_client
)

# Test the connection
try:
    completion = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, are you working?"}
        ]
    )
    print("Connection successful!")
    print(f"Response: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error connecting to OpenAI: {e}")