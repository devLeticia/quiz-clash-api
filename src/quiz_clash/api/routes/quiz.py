import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from quiz_clash.agents.question_generator import (
    generate_questions,
    generate_questions_from_topic,
)
from quiz_clash.ingestion.pdf_loader import load_pdf
from quiz_clash.rag.chunking import split_documents
from quiz_clash.rag.vector_store import build_vector_store, select_diverse_chunks
from quiz_clash.schemas.question import Question

router = APIRouter()


class TopicRequest(BaseModel):
    topic: str
    num_questions: int = 5
    language: str = "English (en-US)"


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


@router.post("/from-pdf", response_model=QuizResponse)
def create_quiz_from_pdf(
    file: UploadFile,
    num_questions: int = 5,
    language: str = "English (en-US)",
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = Path(tmp.name)

    try:
        docs = load_pdf(str(tmp_path))
        chunks = split_documents(docs)
        store = build_vector_store(chunks)
        selected = select_diverse_chunks(store, k=min(num_questions * 2, len(chunks)))

        questions = generate_questions(
            selected,
            questions_per_batch=1,
            chunks_per_batch=2,
            language=language,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return QuizResponse(questions=questions[:num_questions])
