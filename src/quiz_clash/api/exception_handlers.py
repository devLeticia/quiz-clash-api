from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from quiz_clash.core.exceptions import (
    AudioProcessingError,
    DocxProcessingError,
    EmptyDocumentError,
    FileTooLargeError,
    ImageProcessingError,
    InsufficientContentError,
    PDFProcessingError,
    PptxProcessingError,
    QuestionAlreadyAnsweredError,
    QuestionGenerationError,
    UnsupportedFileTypeError,
)


async def bad_input_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def generation_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""
    app.add_exception_handler(PDFProcessingError, bad_input_handler)
    app.add_exception_handler(EmptyDocumentError, bad_input_handler)
    app.add_exception_handler(QuestionGenerationError, generation_error_handler)
    app.add_exception_handler(PDFProcessingError, bad_input_handler)
    app.add_exception_handler(ImageProcessingError, bad_input_handler)
    app.add_exception_handler(DocxProcessingError, bad_input_handler)
    app.add_exception_handler(UnsupportedFileTypeError, bad_input_handler)
    app.add_exception_handler(InsufficientContentError, bad_input_handler)
    app.add_exception_handler(PptxProcessingError, bad_input_handler)
    app.add_exception_handler(AudioProcessingError, bad_input_handler)
    app.add_exception_handler(FileTooLargeError, bad_input_handler)
    app.add_exception_handler(QuestionAlreadyAnsweredError, bad_input_handler)
