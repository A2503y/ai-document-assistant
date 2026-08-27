from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT

app = FastAPI(
    title="AI PDF ASSISTANT",
    description="An AI-powered PDF assistant",
    version="1.0.0"
)

FRONTEND_DIR = PROJECT_ROOT / "frontend"


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

from app.api.upload import router as upload_router
from app.api.ask import router as ask_router
from app.api.documents import router as documents_router

app.include_router(upload_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
