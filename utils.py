import os
import json
import re
import requests
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "legal-json-api",
    "Content-Type": "application/json"
}

MAX_CHARS = 500_000

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def trim_text(text, max_chars=MAX_CHARS):
    return text[:max_chars]

def ask_openrouter(document_text, question_input, model="anthropic/claude-3-haiku"):
    if len(document_text) > MAX_CHARS:
        document_text = trim_text(document_text)

    # 🔍 Smartly detect questions using newlines or '?'
    questions = re.split(r'\n+|(?<=[?])\s+', question_input.strip())
    questions = [q.strip() for q in questions if q.strip()]

    # 📄 Format questions with serial numbers
    formatted_questions = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(questions)])

    prompt = f"""
You are a legal assistant. Given a legal document and multiple questions, your task is to:
1. Answer each question accurately based on the document.
2. Respond in clean JSON format with keys as "Q1", "Q2", etc.
3. Return each answer on its own line with proper JSON formatting.

Document:
\"\"\"{document_text}\"\"\"

Questions:
\"\"\"{formatted_questions}\"\"\"

Only respond in this format:
{{
  "Q1": "Answer to question 1",
  "Q2": "Answer to question 2",
  ...
}}
"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        res = requests.post(API_URL, headers=HEADERS, json=payload)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            # Try parsing to validate it's proper JSON
            parsed = json.loads(content)
            return parsed
        else:
            return {"error": f"Error {res.status_code}: {res.text}"}
    except Exception as e:
        return {"error": str(e)}
