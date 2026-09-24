import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile
from langchain_core.documents import Document
from pydantic import BaseModel, Field, HttpUrl, field_validator

from quiz_clash.agents.question_generator import generate_questions_from_topic
from quiz_clash.ingestion.document_loader import load_document
from quiz_clash.ingestion.image_loader import load_image
from quiz_clash.ingestion.url_loader import load_url
from quiz_clash.schemas.question import Question
from quiz_clash.services.quiz_service import generate_quiz_from_documents

router = APIRouter()


class TopicRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = "English (en-US)"

    @field_validator("topic")
    @classmethod
    def topic_must_contain_enough_letters(cls, value: str) -> str:
        letters = re.findall(r"[a-zA-ZÀ-ÿ]", value)
        if len(letters) < 3:
            raise ValueError(
                "Topic must contain at least 3 letters"
                " (numbers or symbols alone are not valid topics)"
            )
        return value


class URLRequest(BaseModel):
    url: HttpUrl
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = "English (en-US)"

    @field_validator("url", mode="before")
    @classmethod
    def add_scheme_if_missing(cls, value: str) -> str:
        if isinstance(value, str) and not value.startswith(("http://", "https://")):
            return f"https://{value}"
        return value


class QuizResponse(BaseModel):
    questions: list[Question]


@router.post("/from-topic", response_model=QuizResponse)
def create_quiz_from_topic(request: TopicRequest):
    questions = generate_questions_from_topic(
        topic=request.topic,
        num_questions=request.num_questions,
        language=request.language,
    )
    return QuizResponse(questions=questions)


@router.post("/from-document", response_model=QuizResponse)
def create_quiz_from_document(
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    file_bytes = file.file.read()
    suffix = Path(file.filename).suffix.lower()

    tmp_path = None
    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

    try:
        docs = load_document(file_bytes, filename=file.filename, tmp_path_for_pdf=tmp_path)
        questions = generate_quiz_from_documents(docs, num_questions, language)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    return QuizResponse(questions=questions)


@router.post("/from-image", response_model=QuizResponse)
def create_quiz_from_image(
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    image_bytes = file.file.read()
    docs = load_image(image_bytes, content_type=file.content_type, source_name=file.filename)
    questions = generate_quiz_from_documents(docs, num_questions, language)
    return QuizResponse(questions=questions)


@router.post("/from-url", response_model=QuizResponse)
def create_quiz_from_url(request: URLRequest):
    docs = load_url(str(request.url), language=request.language)
    questions = generate_quiz_from_documents(docs, request.num_questions, request.language)
    return QuizResponse(questions=questions)


class PastedTextRequest(BaseModel):
    text: str = Field(min_length=1)
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = "English (en-US)"


@router.post("/from-text", response_model=QuizResponse)
def create_quiz_from_text(request: PastedTextRequest):
    docs = [Document(page_content=request.text, metadata={"source": "pasted_text"})]
    questions = generate_quiz_from_documents(docs, request.num_questions, request.language)
    return QuizResponse(questions=questions)
