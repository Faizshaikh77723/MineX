import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from fastapi import Response

from backend.rag.llm_orchestrator import generate_answer, warmup_model
from backend.rag.retriever import retrieve_context
from backend.rag.vector_store import build_vector_store
from backend.ingestion.parser_digital import parse_digital_pdf
from backend.rag.retriever import retrieve_context, reset_retriever

app = FastAPI(
    title="MineX - Ministry of Coal Document Intelligence",
    version="1.0.0"
)

# --- BULLETPROOF CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = Path("data/uploads")
EXTRACTED_DIR = Path("data/extracted")
CHROMA_DIR = Path("data/chromadb_store")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# Pre-warm model on startup
@app.on_event("startup")
def on_startup():
    warmup_model()

# -------------------------------------------------------------
# Data Models
# -------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    query: str
    answer: str
    retrieved_context: str
    is_report: bool = False
    download_url: str | None = None

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.get("/")
def serve_frontend():
    """Serves the frontend directly on port 8000."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>index.html not found in project root.</h1>", status_code=404)
@app.get("/image_4e3d50.jpg")
def serve_background():
    """Serves the coal mine background image to the frontend."""
    image_path = Path("image_4e3d50.jpg")
    if image_path.exists():
        return FileResponse(image_path)
    return Response(status_code=404)

@app.get("/favicon.ico")
def serve_favicon():
    """Silently ignores the browser's request for a tab icon to prevent terminal spam."""
    return Response(status_code=204)

@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "MineX RAG Gateway", "model": "coal_ai_model"}

@app.get("/api/documents")
def list_documents():
    """Returns a list of all ingested PDF documents."""
    docs = []
    if UPLOAD_DIR.exists():
        for file in UPLOAD_DIR.glob("*.pdf"):
            stats = file.stat()
            docs.append({
                "filename": file.name,
                "size_kb": round(stats.st_size / 1024, 2),
                "status": "Indexed in ChromaDB"
            })
    return {"documents": docs}

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Processes RAG queries and triggers the Report Engine if requested."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        context = retrieve_context(request.query)
        result = generate_answer(request.query)
        
        # Expose the download link if a PDF was generated
        download_url = None
        if result.get("pdf_filename"):
            download_url = f"/api/reports/{result['pdf_filename']}"

        return ChatResponse(
            query=request.query,
            answer=result["answer"],
            retrieved_context=context,
            is_report=result["is_report"],
            download_url=download_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """Ingests, parses (with OCR fallback), and vectorizes PDFs."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    md_filename = f"{Path(file.filename).stem}.md"
    output_md_path = EXTRACTED_DIR / md_filename
    reset_retriever()
    try:
        parse_digital_pdf(str(file_path), str(output_md_path))
        build_vector_store(str(output_md_path), str(CHROMA_DIR))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    return {"status": "success", "message": f"Successfully ingested {file.filename}"}

@app.get("/api/reports/{filename}")
def download_report(filename: str):
    """Serves the generated PDF file for download."""
    report_path = Path("data/generated_reports") / filename
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found.")
        
    return FileResponse(
        path=str(report_path),
        filename=filename,
        media_type="application/pdf"
    )