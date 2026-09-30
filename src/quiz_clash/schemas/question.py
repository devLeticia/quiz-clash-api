import random
import uuid
from typing import Literal

from pydantic import BaseModel, Field


class GeneratedQuestion(BaseModel):
    """Raw question shape the LLM fills in — no id, since ids are assigned server-side."""

    question_type: Literal["fact", "understanding"] = Field(
        description="'fact' asks for a single fact; 'understanding' asks why something "
        "happens, how two ideas relate, or what would happen in a given situation"
    )
    question: str = Field(description="The question text")
    misconceptions: list[str] = Field(
        description="3 plausible misconceptions a learner could have about this question. "
        "Each wrong option must be based on one of them.",
        min_length=3,
        max_length=3,
    )
    options: list[str] = Field(
        description="Exactly 4 short possible answers, all from the same category and with a "
        "similar format. Never repeat the subject or words already stated in the question: "
        "write only the part that differs (for 'What happens to trade winds during El Niño?' "
        "use 'They weaken', not 'Trade winds become weaker'). If the answer is a number, "
        "date, or quantity, every option must be a concise range written with digits "
        "(e.g. '300-400 million', 'Every 2-4 years'), with non-overlapping ranges and only "
        "one containing the correct value.",
        min_length=4,
        max_length=4,
    )
    correct_option_index: int = Field(
        description="Index (0-3) of the correct answer in the options list",
        ge=0,
        le=3,
    )
    source_quote: str | None = Field(
        default=None,
        description="Exact sentence from the source text proving the answer, "
        "if the question was generated from a document",
    )


class Question(BaseModel):
    """A single quiz question with 4 options, plus a server-assigned id."""

    id: str
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option_index: int = Field(ge=0, le=3)
    source_quote: str | None = None

    @classmethod
    def from_generated(cls, generated: "GeneratedQuestion") -> "Question":
        """Build a final Question from what the LLM produced, assigning a fresh id."""
        return cls(
            id=uuid.uuid4().hex, **generated.model_dump(exclude={"question_type", "misconceptions"})
        )


class QuestionPublic(BaseModel):
    """Client-facing question — never includes the correct answer."""

    id: str
    question: str
    options: list[str]


class QuestionList(BaseModel):
    """The LLM's raw output: a list of generated questions, no ids yet."""

    questions: list[GeneratedQuestion] = Field(description="The list of generated quiz questions")


def shuffle_answer_positions(questions: list[Question]) -> list[Question]:
    """Return new Question objects with option order randomized, so the correct
    answer doesn't always land in a predictable position across questions."""
    shuffled_questions = []
    for q in questions:
        indices = list(range(len(q.options)))
        random.shuffle(indices)
        new_options = [q.options[i] for i in indices]
        new_correct_index = indices.index(q.correct_option_index)
        shuffled_questions.append(
            q.model_copy(update={"options": new_options, "correct_option_index": new_correct_index})
        )
    return shuffled_questions


def to_public(question: Question) -> QuestionPublic:
    """Strip the correct answer before sending a question to the client."""
    return QuestionPublic(id=question.id, question=question.question, options=question.options)
