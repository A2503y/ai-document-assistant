import hashlib
import os
from pathlib import Path
import re
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..models.document import Document
from ..services.chunker import PageTextChunker
from ..services.embedding import generate_embeddings
from ..services.pdf_parser import PDFPage, PDFParsingError, extract_pages
from ..services.preprocessor import normalize_text
from ..services.vectordb import delete_document, document_exists, store_embeddings


router = APIRouter()
chunker = PageTextChunker()


class DuplicateDocumentError(ValueError):
    pass


def sanitize_filename(filename: str | None) -> str:
    name = Path(filename or "document.pdf").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(". ")
    if not name:
        name = "document.pdf"
    if Path(name).suffix.lower() != ".pdf":
        raise ValueError("Only files with a .pdf extension are allowed.")
    return name


def save_upload_to_temporary_file(file: UploadFile) -> tuple[Path, str]:
    settings.ensure_directories()
    temporary_path = settings.upload_dir / f".{uuid.uuid4().hex}.pdf"
    hasher = hashlib.sha256()
    total_bytes = 0
    try:
        with temporary_path.open("wb") as destination:
            while block := file.file.read(1024 * 1024):
                total_bytes += len(block)
                if total_bytes > settings.max_upload_bytes:
                    raise ValueError(f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB upload limit.")
                hasher.update(block)
                destination.write(block)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    if total_bytes == 0:
        temporary_path.unlink(missing_ok=True)
        raise ValueError("The uploaded file is empty.")
    return temporary_path, hasher.hexdigest()


@router.post("/upload")
def upload_pdf(file: UploadFile = File(...)):
    if file.content_type and file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    temporary_path: Path | None = None
    final_path: Path | None = None
    content_hash: str | None = None
    owns_document = False
    indexed = False
    try:
        filename = sanitize_filename(file.filename)
        temporary_path, content_hash = save_upload_to_temporary_file(file)
        pages = extract_pages(temporary_path)
        normalized_pages = [
            PDFPage(page.page_number, normalize_text(page.text))
            for page in pages
            if normalize_text(page.text)
        ]
        document = Document.create(
            temporary_path,
            content_hash=content_hash,
            document_name=filename,
        )
        if document_exists(document.document_id):
            raise DuplicateDocumentError("This PDF has already been indexed.")
        owns_document = True
        final_path = settings.upload_dir / f"{document.document_id[:12]}_{filename}"
        os.replace(temporary_path, final_path)
        temporary_path = None
        document.file_path = final_path
        chunks = chunker.chunk_pages(document, normalized_pages)
        if not chunks:
            raise PDFParsingError("The PDF contains no extractable text.")
        store_embeddings(generate_embeddings(chunks))
        indexed = True
    except DuplicateDocumentError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (PDFParsingError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="The PDF could not be processed.") from error
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
        if owns_document and not indexed and content_hash:
            delete_document(content_hash)
            if final_path:
                final_path.unlink(missing_ok=True)

    return {
        "message": "PDF uploaded successfully.",
        "document_id": document.document_id,
        "filename": document.document_name,
        "total_chunks": len(chunks),
    }
