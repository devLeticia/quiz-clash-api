import hashlib
import secrets
import threading
import time
import uuid

from quiz_clash.schemas.question import Question

_store: dict[str, dict] = {}
_store_lock = threading.RLock()


def save_quiz(quiz_id: str, questions: list[Question]) -> None:
    with _store_lock:
        _store[quiz_id] = {
            "questions": questions,
            "participants": {},
            "answers": {},
            "created_at": time.time(),
        }


def get_quiz(quiz_id: str) -> list[Question] | None:
    with _store_lock:
        entry = _store.get(quiz_id)
        return entry["questions"] if entry else None


def get_question(quiz_id: str, question_id: str) -> Question | None:
    with _store_lock:
        questions = get_quiz(quiz_id)
        if questions is None:
            return None
        return next((q for q in questions if q.id == question_id), None)


def create_participant(quiz_id: str) -> str | None:
    """Create a quiz-scoped participant and return its one-time bearer token."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with _store_lock:
        entry = _store.get(quiz_id)
        if entry is None:
            return None
        entry["participants"][token_hash] = uuid.uuid4().hex

    return token


def get_participant_id(quiz_id: str, token: str) -> str | None:
    """Resolve a bearer token to its participant id within the specified quiz."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _store_lock:
        entry = _store.get(quiz_id)
        if entry is None:
            return None
        return entry["participants"].get(token_hash)


def record_answer(
    quiz_id: str,
    participant_id: str,
    question_id: str,
    selected_option_index: int,
    is_correct: bool,
) -> bool:
    """Record one answer per participant and question, atomically."""
    with _store_lock:
        entry = _store.get(quiz_id)
        if entry is None or participant_id not in entry["participants"].values():
            return False
        participant_answers = entry["answers"].setdefault(participant_id, {})
        if question_id in participant_answers:
            return False
        participant_answers[question_id] = {
            "selected_option_index": selected_option_index,
            "correct": is_correct,
        }
        return True


def get_answers(quiz_id: str, participant_id: str) -> dict:
    with _store_lock:
        entry = _store.get(quiz_id)
        if entry is None:
            return {}
        return entry["answers"].get(participant_id, {}).copy()
