from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils import extract_text_from_file, ask_openrouter

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
        <h2>Upload Legal Document (.pdf, .docx, .eml) and Ask Questions</h2>
        <form action="/ask" method="post" enctype="multipart/form-data">
            <label for="file">Upload Document:</label><br>
            <input type="file" id="file" name="file" accept=".pdf,.docx,.eml" required><br><br>

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
        # ✅ Extract content from any supported file type
        text = extract_text_from_file(file)

        # Call OpenRouter with the document text and questions
        response_dict = ask_openrouter(text, question)

        # Format result as readable HTML
        formatted_response = "<h2>Response:</h2>"
        for key, value in response_dict.items():
            formatted_response += f"<h3>{key}</h3>"

            if isinstance(value, list):
                formatted_response += "<ul>"
                for item in value:
                    formatted_response += f"<li>{item}</li>"
                formatted_response += "</ul>"

            elif isinstance(value, dict):
                formatted_response += "<ul>"
                for subkey, subval in value.items():
                    formatted_response += f"<li><strong>{subkey}:</strong> {subval}</li>"
                formatted_response += "</ul>"

            else:
                formatted_response += f"<p>{value}</p>"

        formatted_response += "<br><a href='/'>Ask More Questions</a>"
        return HTMLResponse(content=formatted_response)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
