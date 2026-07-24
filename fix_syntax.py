import glob
files = ['rbackend/backend.py', 'Legal_QA/legal-qa-system/backend/app.py', 'Legal_Summary/backend/app.py', 'indiankanoon-mcp/ui/app.py']
import re

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace('str(e, exc_info=True)}")', 'str(e)}", exc_info=True)')
    content = content.replace('str(e, exc_info=True)', 'str(e)')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
