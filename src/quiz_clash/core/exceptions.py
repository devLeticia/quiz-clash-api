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
