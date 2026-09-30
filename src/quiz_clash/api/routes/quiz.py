import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.documents import Document
from pydantic import BaseModel, Field, HttpUrl, field_validator

from quiz_clash.agents.question_generator import generate_questions_from_topic
from quiz_clash.api.validation import (
    read_upload_within_limit,
    safe_temp_filename,
    validate_content_type,
)
from quiz_clash.core.exceptions import QuestionAlreadyAnsweredError, QuizNotFoundError
from quiz_clash.core.quiz_store import (
    create_participant,
    get_answers,
    get_participant_id,
    get_question,
    get_quiz,
    record_answer,
    save_quiz,
)
from quiz_clash.core.rate_limiter import limiter
from quiz_clash.ingestion.audio_loader import load_audio
from quiz_clash.ingestion.document_loader import load_document
from quiz_clash.ingestion.image_loader import load_image
from quiz_clash.ingestion.url_loader import load_url
from quiz_clash.schemas.question import (
    Question,
    QuestionPublic,
    shuffle_answer_positions,
    to_public,
)
from quiz_clash.services.quiz_service import generate_quiz_from_documents

router = APIRouter()

RATE_LIMIT = "5/minute;30/hour;100/day"
bearer_scheme = HTTPBearer(auto_error=False)


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


class QuizCreateResponse(BaseModel):
    quiz_id: str
    questions: list[QuestionPublic]


def _build_quiz_response(questions: list[Question]) -> QuizCreateResponse:
    """Shuffle answer positions, store the full quiz (with answers) server-side,
    and return only the public view (no correct answers) to the client."""
    import uuid

    shuffled = shuffle_answer_positions(questions)
    quiz_id = uuid.uuid4().hex
    save_quiz(quiz_id, shuffled)
    return QuizCreateResponse(quiz_id=quiz_id, questions=[to_public(q) for q in shuffled])


@router.post("/from-topic", response_model=QuizCreateResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_topic(request: Request, body: TopicRequest):
    questions = generate_questions_from_topic(
        topic=body.topic,
        num_questions=body.num_questions,
        language=body.language,
    )
    return _build_quiz_response(questions)


@router.post("/from-document", response_model=QuizCreateResponse)
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

    return _build_quiz_response(questions)


@router.post("/from-image", response_model=QuizCreateResponse)
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
    return _build_quiz_response(questions)


@router.post("/from-url", response_model=QuizCreateResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_url(request: Request, body: URLRequest):
    docs = load_url(str(body.url), language=body.language)
    questions = generate_quiz_from_documents(docs, body.num_questions, body.language)
    return _build_quiz_response(questions)


class PastedTextRequest(BaseModel):
    text: str = Field(min_length=1)
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = "English (en-US)"


@router.post("/from-text", response_model=QuizCreateResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_from_text(request: Request, body: PastedTextRequest):
    docs = [Document(page_content=body.text, metadata={"source": "pasted_text"})]
    questions = generate_quiz_from_documents(docs, body.num_questions, body.language)
    return _build_quiz_response(questions)


@router.post("/from-audio", response_model=QuizCreateResponse)
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
    return _build_quiz_response(questions)


class AnswerRequest(BaseModel):
    question_id: str
    selected_option_index: int = Field(ge=0, le=3)


class AnswerResponse(BaseModel):
    correct: bool


class ParticipantTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _require_participant(quiz_id: str, credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="A participant bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    participant_id = get_participant_id(quiz_id, credentials.credentials)
    if participant_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid participant token for this quiz.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return participant_id


@router.post("/{quiz_id}/participants", response_model=ParticipantTokenResponse)
@limiter.limit(RATE_LIMIT)
def create_quiz_participant(request: Request, quiz_id: str):
    token = create_participant(quiz_id)
    if token is None:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found.")
    return ParticipantTokenResponse(access_token=token)


@router.post("/{quiz_id}/answer", response_model=AnswerResponse)
@limiter.limit(RATE_LIMIT)
def submit_answer(
    request: Request,
    quiz_id: str,
    body: AnswerRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if get_quiz(quiz_id) is None:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found.")
    participant_id = _require_participant(quiz_id, credentials)

    question = get_question(quiz_id, body.question_id)
    if question is None:
        raise QuizNotFoundError(f"Question '{body.question_id}' not found in quiz '{quiz_id}'.")

    is_correct = body.selected_option_index == question.correct_option_index

    recorded = record_answer(
        quiz_id,
        participant_id,
        body.question_id,
        body.selected_option_index,
        is_correct,
    )
    if not recorded:
        raise QuestionAlreadyAnsweredError(f"Question '{body.question_id}' was already answered.")

    return AnswerResponse(correct=is_correct)


class QuestionResult(BaseModel):
    id: str
    question: str
    options: list[str]
    answered: bool
    selected_option_index: int | None = None
    correct_option_index: int | None = None
    correct: bool | None = None


class QuizResultsResponse(BaseModel):
    quiz_id: str
    total_questions: int
    answered_count: int
    correct_count: int
    results: list[QuestionResult]


@router.get("/{quiz_id}/results", response_model=QuizResultsResponse)
@limiter.limit(RATE_LIMIT)
def get_quiz_results(
    request: Request,
    quiz_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    questions = get_quiz(quiz_id)
    if questions is None:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found.")

    participant_id = _require_participant(quiz_id, credentials)
    answers = get_answers(quiz_id, participant_id)
    results = []
    correct_count = 0

    for q in questions:
        answer = answers.get(q.id)
        if answer is None:
            results.append(
                QuestionResult(id=q.id, question=q.question, options=q.options, answered=False)
            )
            continue

        results.append(
            QuestionResult(
                id=q.id,
                question=q.question,
                options=q.options,
                answered=True,
                selected_option_index=answer["selected_option_index"],
                correct_option_index=q.correct_option_index,
                correct=answer["correct"],
            )
        )
        if answer["correct"]:
            correct_count += 1

    return QuizResultsResponse(
        quiz_id=quiz_id,
        total_questions=len(questions),
        answered_count=len(answers),
        correct_count=correct_count,
        results=results,
    )
