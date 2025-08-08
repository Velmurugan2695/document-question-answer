from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils import extract_text_from_file, ask_openrouter, send_to_hackrx

app = FastAPI()

# Enable CORS (for external frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Home Page - HTML form
@app.get("/", response_class=HTMLResponse)
async def main():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Legal Document Q&A</title>
    </head>
    <body>
        <h2>Upload Legal Document and Ask Questions</h2>
        <form action="/ask" method="post" enctype="multipart/form-data">
            <label>Upload Document:</label><br>
            <input type="file" name="file" required><br><br>
            <label>Questions (one per line):</label><br>
            <textarea name="question" rows="10" cols="80" required></textarea><br><br>
            <input type="submit" value="Ask">
        </form>
    </body>
    </html>
    """

# Q&A Processing
@app.post("/ask")
async def ask_question(file: UploadFile = File(...), question: str = Form(...)):
    try:
        text = extract_text_from_file(file)
        response_dict = ask_openrouter(text, question)
        return JSONResponse(content=response_dict)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Webhook for HackRx to call us
@app.post("/webhook")
async def webhook(request: Request):
    """
    HackRx will send us JSON: { "documents": "url", "questions": [...] }
    We'll process and return the answers.
    """
    try:
        data = await request.json()
        doc_url = data.get("documents")
        questions = data.get("questions", [])
        hackrx_response = send_to_hackrx(doc_url, questions)
        return JSONResponse(content=hackrx_response)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Optional: endpoint to send to HackRx manually
@app.post("/send_to_hackrx")
async def send_to_hackrx_api(document_url: str = Form(...), questions: str = Form(...)):
    try:
        questions_list = [q.strip() for q in questions.split("\n") if q.strip()]
        resp = send_to_hackrx(document_url, questions_list)
        return JSONResponse(content=resp)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
