import os
import json
import re
import requests
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
from email import policy
from email.parser import BytesParser
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import faiss
from fastapi import UploadFile

load_dotenv()

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Constants
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CHARS = 500_000
CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 100

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "legal-json-api",
    "Content-Type": "application/json"
}

# ------------------------------------
# 📄 Extract Text from Multiple Files
# ------------------------------------
def extract_text_from_file(file: UploadFile) -> str:
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file.filename.endswith(".docx"):
        doc = Document(file.file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif file.filename.endswith(".eml"):
        msg = BytesParser(policy=policy.default).parse(file.file)
        return msg.get_body(preferencelist=('plain')).get_content()
    else:
        return "Unsupported file format"

# ------------------------------------
# ✂️ Chunking Function
# ------------------------------------
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# ------------------------------------
# 🔍 FAISS Search Setup
# ------------------------------------
def build_faiss_index(chunks):
    embeddings = model.encode(chunks)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))
    return index, embeddings, chunks

def search_similar_chunks(question, chunks, embeddings, top_k=5):
    question_vector = model.encode([question])
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings).astype("float32"))
    distances, indices = index.search(np.array(question_vector).astype("float32"), top_k)
    return [chunks[i] for i in indices[0]]

# ------------------------------------
# 💬 Ask OpenRouter with Context
# ------------------------------------
def ask_openrouter(document_text, question_input, model_name="anthropic/claude-3-haiku"):
    chunks = chunk_text(document_text)
    index, embeddings, chunk_list = build_faiss_index(chunks)

    questions = re.split(r'\n+|(?<=[?])\s+', question_input.strip())
    questions = [q.strip() for q in questions if q.strip()]
    responses = {}

    for idx, question in enumerate(questions):
        relevant_chunks = search_similar_chunks(question, chunk_list, embeddings)
        context = "\n---\n".join(relevant_chunks)

        prompt = f"""
Given the following extracted contract/policy clauses:

\"\"\"{context}\"\"\"

Answer the question clearly using ONLY the above content.

Question: {question}

Respond in a clean JSON with key "Q{idx+1}".
"""
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        try:
            res = requests.post(API_URL, headers=HEADERS, json=payload)
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"]
                json_resp = json.loads(content)
                responses.update(json_resp)
            else:
                responses[f"Q{idx+1}"] = f"Error: {res.status_code}"
        except Exception as e:
            responses[f"Q{idx+1}"] = str(e)

    return responses
