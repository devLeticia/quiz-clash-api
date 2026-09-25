import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from langchain_core.documents import Document
from pydantic import BaseModel, Field, HttpUrl, field_validator

from quiz_clash.agents.question_generator import generate_questions_from_topic
from quiz_clash.api.validation import (
    read_upload_within_limit,
    safe_temp_filename,
    validate_content_type,
)
from quiz_clash.core.rate_limiter import limiter
from quiz_clash.ingestion.audio_loader import load_audio
from quiz_clash.ingestion.document_loader import load_document
from quiz_clash.ingestion.image_loader import load_image
from quiz_clash.ingestion.url_loader import load_url
from quiz_clash.schemas.question import Question
from quiz_clash.services.quiz_service import generate_quiz_from_documents

router = APIRouter()

RATE_LIMIT = RATE_LIMIT = "5/minute;30/hour;100/day"


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
        if isinstance(value, str) and "://" not in value:
            return f"https://{value}"
        return value


class QuizResponse(BaseModel):
    questions: list[Question]


@router.post("/from-topic", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_topic(request: Request, body: TopicRequest):
    questions = generate_questions_from_topic(
        topic=body.topic,
        num_questions=body.num_questions,
        language=body.language,
    )
    return QuizResponse(questions=questions)


@router.post("/from-document", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_document(
    request: Request,
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    file_bytes = read_upload_within_limit(file)
    detected_mime = validate_content_type(file_bytes, file.filename, category="document")

    tmp_path = None
    if detected_mime == "application/pdf":
        tmp_name = safe_temp_filename(detected_mime)
        tmp_dir = Path(tempfile.gettempdir())
        with open(tmp_dir / tmp_name, "wb") as tmp:
            tmp.write(file_bytes)
        tmp_path = str(tmp_dir / tmp_name)

    try:
        docs = load_document(
            file_bytes,
            filename=file.filename,
            detected_mime=detected_mime,
            tmp_path_for_pdf=tmp_path,
        )
        questions = generate_quiz_from_documents(docs, num_questions, language)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    return QuizResponse(questions=questions)


@router.post("/from-image", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_image(
    request: Request,
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    image_bytes = read_upload_within_limit(file)
    validate_content_type(image_bytes, file.filename, category="image")
    docs = load_image(image_bytes, content_type=file.content_type, source_name=file.filename)
    questions = generate_quiz_from_documents(docs, num_questions, language)
    return QuizResponse(questions=questions)


@router.post("/from-url", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_url(request: Request, body: URLRequest):
    docs = load_url(str(body.url), language=body.language)
    questions = generate_quiz_from_documents(docs, body.num_questions, body.language)
    return QuizResponse(questions=questions)


class PastedTextRequest(BaseModel):
    text: str = Field(min_length=1)
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = "English (en-US)"


@router.post("/from-text", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_text(request: Request, body: PastedTextRequest):
    docs = [Document(page_content=body.text, metadata={"source": "pasted_text"})]
    questions = generate_quiz_from_documents(docs, body.num_questions, body.language)
    return QuizResponse(questions=questions)


@router.post("/from-audio", response_model=QuizResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_audio(
    request: Request,
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    audio_bytes = read_upload_within_limit(file)
    validate_content_type(audio_bytes, file.filename, category="audio")
    docs = load_audio(audio_bytes, filename=file.filename)
    questions = generate_quiz_from_documents(docs, num_questions, language)
    return QuizResponse(questions=questions)
