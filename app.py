from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils import extract_text_from_pdf, ask_openrouter

app = FastAPI()

# Enable CORS if using external frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def main():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Legal Document QA</title>
    </head>
    <body>
        <h2>Upload Legal Document and Ask Multiple Questions</h2>
        <form action="/ask" method="post" enctype="multipart/form-data">
            <label for="file">Upload PDF:</label><br>
            <input type="file" id="file" name="file" accept=".pdf" required><br><br>

            <label for="question">Questions (one per line):</label><br>
            <textarea id="question" name="question" rows="10" cols="80" required></textarea><br><br>

            <input type="submit" value="Ask">
        </form>
    </body>
    </html>
    """

@app.post("/ask")
async def ask_question(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    try:
        contents = await file.read()
        text = extract_text_from_pdf(file.file)
        response = ask_openrouter(text, question)
        return JSONResponse(content={"response": response})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
