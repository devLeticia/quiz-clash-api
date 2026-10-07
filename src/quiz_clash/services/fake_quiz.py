import itertools
import os
import uuid

from dotenv import load_dotenv

from quiz_clash.schemas.question import Question

load_dotenv()

FAKE_QUIZ = os.getenv("FAKE_QUIZ", "false").lower() == "true"

FAKE_QUESTIONS = [
    (
        "Which organelle is known as the powerhouse of the cell?",
        ["Mitochondria", "Ribosome", "Nucleus", "Golgi body"],
        0,
    ),
    ("In which year did the Berlin Wall fall?", ["1991", "1989", "1985", "1993"], 1),
    ("What is the derivative of sin(x)?", ["-cos(x)", "-sin(x)", "cos(x)", "tan(x)"], 2),
    (
        "Which process do plants use to convert light into sugar?",
        ["Respiration", "Fermentation", "Osmosis", "Photosynthesis"],
        3,
    ),
    (
        "Which molecule carries genetic instructions in most organisms?",
        ["DNA", "ATP", "RNA polymerase", "Lipid"],
        0,
    ),
    ("What is the SI unit of electric current?", ["Volt", "Ampere", "Ohm", "Watt"], 1),
    ("Which planet is closest to the Sun?", ["Venus", "Mars", "Mercury", "Earth"], 2),
    ("What is the chemical symbol for gold?", ["Ag", "Gd", "Go", "Au"], 3),
    (
        "Who wrote 'Dom Casmurro'?",
        ["Machado de Assis", "Jorge Amado", "José de Alencar", "Clarice Lispector"],
        0,
    ),
    ("How many sides does a hexagon have?", ["Five", "Six", "Seven", "Eight"], 1),
]


def fake_questions(num_questions: int) -> list[Question]:
    """Return canned questions so the app can be tested without calling the LLM."""
    return [
        Question(id=uuid.uuid4().hex, question=q, options=options, correct_option_index=correct)
        for q, options, correct in itertools.islice(itertools.cycle(FAKE_QUESTIONS), num_questions)
    ]
