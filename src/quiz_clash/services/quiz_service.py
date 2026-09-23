from quiz_clash.agents.question_generator import generate_questions
from quiz_clash.core.exceptions import InsufficientContentError
from quiz_clash.rag.chunking import split_documents
from quiz_clash.rag.vector_store import build_vector_store, select_diverse_chunks
from quiz_clash.schemas.question import Question

MIN_CONTENT_CHARS = 600


def generate_quiz_from_documents(docs: list, num_questions: int, language: str) -> list[Question]:
    """Validate extracted content and run the full quiz generation pipeline."""
    total_chars = sum(len(doc.page_content) for doc in docs)
    if total_chars < MIN_CONTENT_CHARS:
        raise InsufficientContentError(
            f"Not enough content to generate a quiz "
            f"({total_chars} characters found, minimum is {MIN_CONTENT_CHARS})."
        )

    chunks = split_documents(docs)
    store = build_vector_store(chunks)
    selected = select_diverse_chunks(store, k=min(num_questions * 2, len(chunks)))

    questions = generate_questions(
        selected,
        questions_per_batch=1,
        chunks_per_batch=2,
        language=language,
    )
    return questions[:num_questions]
