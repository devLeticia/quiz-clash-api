from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from quiz_clash.core.exceptions import (
    EmptyDocumentError,
    PDFProcessingError,
    QuestionGenerationError,
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
