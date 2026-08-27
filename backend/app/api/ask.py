from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.llm import LLMProviderError, MissingAPIKeyError
from app.services.rag import NoContextError, answer_question
from app.services.vectordb import indexed_document_ids


router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    document_id: str | None = None
    document_ids: list[str] | None = Field(default=None, max_length=20)
    top_k: int = Field(default=4, ge=1, le=settings.max_retrieved_chunks)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty.")
        return value.strip()

    @field_validator("document_id")
    @classmethod
    def document_id_must_not_be_blank(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("document_ids")
    @classmethod
    def document_ids_must_not_be_blank(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not cleaned:
            raise ValueError("document_ids must contain at least one ID.")
        return cleaned

    @model_validator(mode="after")
    def only_one_selection_style(self):
        if self.document_id and self.document_ids:
            raise ValueError("Use document_id or document_ids, not both.")
        return self


class SourceResponse(BaseModel):
    document_id: str
    filename: str
    page_number: int | None
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    available_ids = indexed_document_ids()
    if not available_ids:
        raise HTTPException(status_code=404, detail="No documents have been indexed yet.")

    selected_ids = [request.document_id] if request.document_id else (request.document_ids or [])
    missing_ids = sorted(set(selected_ids) - available_ids)
    if missing_ids:
        raise HTTPException(status_code=404, detail="One or more selected documents were not found.")

    try:
        return answer_question(request.question, request.top_k, selected_ids or None)
    except NoContextError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MissingAPIKeyError as error:
        raise HTTPException(status_code=503, detail="LLM service is not configured.") from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail="LLM service could not generate an answer.") from error
