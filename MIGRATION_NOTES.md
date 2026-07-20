# OpenAI API Migration Notes

## Problem
The backend was using the old OpenAI API syntax (`openai.ChatCompletion`) which is deprecated in `openai>=1.0.0`.

## Solution
Updated all backend code to use the new OpenAI client syntax.

### Changes Made

#### 1. Old Syntax (Deprecated)
```python
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[...]
)
```

#### 2. New Syntax (Current)
```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[...]
)
```

### Updated Files

- ✅ `backend/case_extractor.py` - Main case extraction logic
- ✅ `backend/pdf_processor.py` - PDF processing with GPT
- ✅ `backend/requirements.txt` - Updated to `openai>=1.0.0`

### How to Update

Run the update script to install the new OpenAI package:

```batch
update_openai.bat
```

Or update all dependencies at once:

```batch
update_all_deps.bat
```

### Testing After Update

1. Stop all running backend services
2. Run `update_openai.bat` or `update_all_deps.bat`
3. Restart all services using `start_all.bat`
4. Test case upload and processing functionality

### Troubleshooting

**Error: "You tried to access openai.ChatCompletion"**
- Solution: Run `update_openai.bat` and restart backend

**Error: "No module named 'openai'"**
- Solution: Activate venv and run `pip install openai>=1.0.0`

**Error: API key not found**
- Solution: Check `.env` files in each backend folder

### References

- [OpenAI Python SDK Migration Guide](https://github.com/openai/openai-python/discussions/742)
- [OpenAI v1.0.0 Changelog](https://github.com/openai/openai-python/releases/tag/v1.0.0)
