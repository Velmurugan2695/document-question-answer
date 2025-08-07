from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils import extract_text_from_pdf, ask_openrouter

app = FastAPI()

# Enable CORS (for external frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set specific origins
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
            <label for="file">Upload PDF:</label><br>
            <input type="file" id="file" name="file" accept=".pdf" required><br><br>

            <label for="question">Questions (one per line):</label><br>
            <textarea id="question" name="question" rows="10" cols="80" placeholder="Write each question on a new line..." required></textarea><br><br>

            <input type="submit" value="Ask">
        </form>
    </body>
    </html>
    """

# Q&A Processing
@app.post("/ask")
async def ask_question(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    try:
        # Extract and read PDF content
        text = extract_text_from_pdf(file.file)

        # Ask OpenRouter
        response_dict = ask_openrouter(text, question)

        # Format result as readable HTML
        formatted_response = "<h2>Response:</h2><ul>"
        for key, value in response_dict.items():
            formatted_response += f"<li><strong>{key}:</strong> {value}</li>"
        formatted_response += "</ul><a href='/'>Ask More Questions</a>"

        return HTMLResponse(content=formatted_response)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
