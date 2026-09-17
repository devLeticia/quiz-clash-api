from pydantic import BaseModel, Field


class Question(BaseModel):
    """A single quiz question with 4 options."""

    question: str = Field(description="The question text")
    options: list[str] = Field(
        description="Exactly 4 possible answers",
        min_length=4,
        max_length=4,
    )
    correct_option_index: int = Field(
        description="Index (0-3) of the correct answer in the options list",
        ge=0,
        le=3,
    )
    source_quote: str = Field(
        description="The exact sentence or phrase copied verbatim from the source "
        "text that proves the correct answer"
    )


class QuestionList(BaseModel):
    """A list of quiz questions."""

    questions: list[Question] = Field(description="The list of generated quiz questions")
