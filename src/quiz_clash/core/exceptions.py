from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class QuizClashError(Exception):
    """Base exception for all domain errors in Quiz Clash."""


class PDFProcessingError(QuizClashError):
    """Raised when a PDF file cannot be read or parsed."""


class EmptyDocumentError(QuizClashError):
    """Raised when a document has no extractable text."""


class QuestionGenerationError(QuizClashError):
    """Raised when the LLM fails to generate valid questions."""


class ImageProcessingError(QuizClashError):
    """Raised when an image cannot be read or no text can be extracted from it."""


class DocxProcessingError(QuizClashError):
    """Raised when a DOCX file cannot be read or parsed."""


class UnsupportedFileTypeError(QuizClashError):
    """Raised when the uploaded file type is not supported."""


class URLProcessingError(QuizClashError):
    """Raised when a URL cannot be fetched or its content cannot be extracted."""


class InsufficientContentError(QuizClashError):
    """Raised when there isn't enough extracted text to generate a meaningful quiz."""


class PptxProcessingError(QuizClashError):
    """Raised when a PPTX file cannot be read or parsed."""


class AudioProcessingError(QuizClashError):
    """Raised when an audio file cannot be transcribed."""


class FileTooLargeError(QuizClashError):
    """Raised when an uploaded file exceeds the maximum allowed size."""


class QuestionAlreadyAnsweredError(QuizClashError):
    """Raised when a question in a quiz has already been answered."""


class QuizNotFoundError(QuizClashError):
    """Raised when a quiz_id or question_id doesn't exist in the store."""


class ParticipantLimitReachedError(QuizClashError):
    """Raised when a quiz already has its maximum number of participants."""


async def bad_input_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def conflict_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def generation_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app.

    QuestionGenerationError gets its own handler (502, since it reflects an
    upstream LLM failure, not bad input). Every other QuizClashError subclass
    is caught by the single QuizClashError handler below — new exception
    types added later don't need a new line here, Starlette matches by
    inheritance (MRO).
    """
    app.add_exception_handler(QuestionGenerationError, generation_error_handler)
    app.add_exception_handler(ParticipantLimitReachedError, conflict_handler)
    app.add_exception_handler(QuizClashError, bad_input_handler)
