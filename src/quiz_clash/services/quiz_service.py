import hashlib

from quiz_clash.agents.question_generator import generate_questions
from quiz_clash.core.exceptions import InsufficientContentError
from quiz_clash.core.quiz_store import (
    add_asked_questions,
    get_asked_questions,
    reset_asked_questions,
)
from quiz_clash.rag.chunking import split_documents
from quiz_clash.rag.vector_store import build_vector_store, select_diverse_chunks
from quiz_clash.schemas.question import Question

MIN_CONTENT_CHARS = 600
SHORT_CONTENT_CHARS = 6000
CHUNKS_PER_BATCH = 2


def generate_quiz_from_documents(docs: list, num_questions: int, language: str) -> list[Question]:
    """Validate extracted content and run the full quiz generation pipeline."""
    total_chars = sum(len(doc.page_content) for doc in docs)
    if total_chars < MIN_CONTENT_CHARS:
        raise InsufficientContentError(
            f"Not enough content to generate a quiz "
            f"({total_chars} characters found, minimum is {MIN_CONTENT_CHARS})."
        )

    full_text = "\n\n".join(doc.page_content for doc in docs)
    document_key = hashlib.sha256(full_text.encode()).hexdigest()
    texts = _build_texts(docs, full_text, num_questions)

    asked = get_asked_questions(document_key)
    questions = generate_questions(texts, num_questions, language, asked)
    if len(questions) < num_questions and asked:
        reset_asked_questions(document_key)
        questions = generate_questions(texts, num_questions, language)

    add_asked_questions(document_key, questions)
    return questions


def _build_texts(docs: list, full_text: str, num_questions: int) -> list[str]:
    if len(full_text) <= SHORT_CONTENT_CHARS:
        return [full_text]

    chunks = split_documents(docs)
    store = build_vector_store(chunks)
    selected = select_diverse_chunks(store, k=min(num_questions * 2, len(chunks)))
    return [
        "\n\n".join(chunk.page_content for chunk in selected[i : i + CHUNKS_PER_BATCH])
        for i in range(0, len(selected), CHUNKS_PER_BATCH)
    ]
