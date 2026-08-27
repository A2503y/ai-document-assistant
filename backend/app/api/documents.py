from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.services.document_service import list_documents, remove_document


router = APIRouter()


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    document_type: str | None
    uploaded_at: str | None
    page_count: int | None
    chunk_count: int


@router.get("/documents", response_model=list[DocumentResponse])
def get_documents():
    return list_documents()


@router.delete("/documents/{document_id}", status_code=204)
def delete_document_endpoint(document_id: str):
    if not remove_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(status_code=204)
