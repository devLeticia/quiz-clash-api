import contextvars
import hashlib
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

from langsmith import traceable

from quiz_clash.agents.question_generator import generate_questions, generate_questions_from_topic
from quiz_clash.core.exceptions import InsufficientContentError
from quiz_clash.core.quiz_store import (
    add_asked_questions,
    get_asked_questions,
    reset_asked_questions,
)
from quiz_clash.core.tracing import only
from quiz_clash.rag.chunking import split_documents
from quiz_clash.rag.vector_store import build_vector_store, select_diverse_chunks
from quiz_clash.schemas.question import Question

MIN_CONTENT_CHARS = 600
SHORT_CONTENT_CHARS = 6000
CHUNKS_PER_BATCH = 2
MAX_TRACKED_SOURCES = 1000

logger = logging.getLogger("quiz_clash")

Generator = Callable[[], list[Question]]


@dataclass
class QuizSource:
    generate: Generator
    num_questions: int
    upcoming: Future


_sources: dict[str, QuizSource] = {}
_sources_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4)


def prepare_document_quiz(
    docs: list, num_questions: int, language: str, difficulty: str
) -> Generator:
    """Validate extracted content and return a generator of new quiz rounds for it."""
    total_chars = sum(len(doc.page_content) for doc in docs)
    if total_chars < MIN_CONTENT_CHARS:
        raise InsufficientContentError(
            f"Not enough content to generate a quiz "
            f"({total_chars} characters found, minimum is {MIN_CONTENT_CHARS})."
        )

    full_text = "\n\n".join(doc.page_content for doc in docs)
    document_key = hashlib.sha256(full_text.encode()).hexdigest()
    texts = _build_texts(docs, full_text, num_questions)
    return partial(_document_round, texts, document_key, num_questions, language, difficulty)


def prepare_topic_quiz(topic: str, num_questions: int, language: str, difficulty: str) -> Generator:
    topic_key = hashlib.sha256(f"topic:{topic.strip().lower()}:{language}".encode()).hexdigest()
    return partial(_topic_round, topic, topic_key, num_questions, language, difficulty)


def remember_source(quiz_id: str, generate: Generator, num_questions: int) -> None:
    """Keep how a quiz was made and start generating its next round in the background."""
    prefetch = traceable(name="prefetch_next_round")(generate)
    upcoming = _executor.submit(contextvars.copy_context().run, prefetch)
    source = QuizSource(generate, num_questions, upcoming)
    with _sources_lock:
        _sources[quiz_id] = source
        if len(_sources) > MAX_TRACKED_SOURCES:
            _sources.pop(next(iter(_sources)))


def next_round(quiz_id: str) -> tuple[list[Question], QuizSource] | None:
    with _sources_lock:
        source = _sources.pop(quiz_id, None)
    if source is None:
        return None
    prefetch_hit = source.upcoming.done()
    start = time.perf_counter()
    try:
        questions = source.upcoming.result()
    except Exception:
        logger.exception("prefetch_failed")
        questions = source.generate()
    logger.info(
        "next_round",
        extra={
            "prefetch_hit": prefetch_hit,
            "wait_ms": round((time.perf_counter() - start) * 1000),
        },
    )
    return questions, source


@traceable(name="generate_round", process_inputs=only("num_questions", "language", "difficulty"))
def _document_round(
    texts: list[str], document_key: str, num_questions: int, language: str, difficulty: str
) -> list[Question]:
    asked = get_asked_questions(document_key)
    questions = generate_questions(texts, num_questions, language, difficulty, asked)
    if len(questions) < num_questions and asked:
        logger.info(
            "asked_questions_reset",
            extra={"generated": len(questions), "previously_asked": len(asked)},
        )
        reset_asked_questions(document_key)
        questions = generate_questions(texts, num_questions, language, difficulty)

    add_asked_questions(document_key, questions)
    return questions


@traceable(
    name="generate_round", process_inputs=only("topic", "num_questions", "language", "difficulty")
)
def _topic_round(
    topic: str, topic_key: str, num_questions: int, language: str, difficulty: str
) -> list[Question]:
    asked = [q.question for q in get_asked_questions(topic_key)]
    questions = generate_questions_from_topic(topic, num_questions, language, difficulty, asked)
    add_asked_questions(topic_key, questions)
    return questions


@traceable(name="build_texts", process_inputs=only("num_questions"))
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
