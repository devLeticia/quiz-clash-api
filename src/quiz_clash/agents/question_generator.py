import re

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from rapidfuzz import fuzz

from quiz_clash.schemas.question import Question, QuestionList

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
structured_llm = llm.with_structured_output(QuestionList)


def _generate_from_text(text: str, num_questions: int, language: str) -> list[Question]:
    prompt = f"""Based on the following text, create {num_questions} quiz questions IN {language}.
Even if the source text contains words or names in other languages, write the question
and all options in {language}.

Each question must have exactly 4 options and one correct answer.

For each question, include a "source_quote": copy the EXACT sentence or phrase
from the text below that proves the correct answer. Do not paraphrase it -
copy it word for word.

Text:
{text}
"""
    result = structured_llm.invoke(prompt)
    return result.questions


def generate_questions(
    chunks: list[Document],
    questions_per_batch: int = 1,
    chunks_per_batch: int = 3,
    language: str = "Portuguese (pt-BR)",
) -> list[Question]:
    """Generate quiz questions from a pre-selected set of chunks, in small batches."""
    all_questions: list[Question] = []

    for i in range(0, len(chunks), chunks_per_batch):
        batch = chunks[i : i + chunks_per_batch]
        text = "\n\n".join(chunk.page_content for chunk in batch)

        questions = _generate_from_text(text, questions_per_batch, language)
        all_questions.extend(questions)

    return all_questions


def _normalize(text: str) -> str:
    """Normalize whitespace and quote characters for reliable comparison."""
    text = re.sub(r"\s+", " ", text)
    text = text.replace(""", '"').replace(""", '"')
    text = text.replace("'", "'").replace("'", "'")
    return text.strip()


def is_grounded(question: Question, source_text: str, threshold: float = 85.0) -> bool:
    """Check whether the question's source_quote closely matches the source text."""
    normalized_quote = _normalize(question.source_quote)
    normalized_source = _normalize(source_text)

    score = fuzz.partial_ratio(normalized_quote, normalized_source)
    return score >= threshold
