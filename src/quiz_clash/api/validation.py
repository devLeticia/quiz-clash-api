import uuid

import puremagic
from fastapi import UploadFile

from quiz_clash.core.exceptions import FileTooLargeError, UnsupportedFileTypeError

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "document": {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
    },
    "image": {"image/jpeg", "image/png", "image/webp"},
    "audio": {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg"},
}

EXTENSION_BY_MIME = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
}


def read_upload_within_limit(file: UploadFile, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """Read an uploaded file's bytes, rejecting it if it exceeds the size limit."""
    contents = file.file.read()
    if len(contents) > max_bytes:
        raise FileTooLargeError(
            f"File '{file.filename}' is too large "
            f"({len(contents) / 1_048_576:.1f} MB). Maximum allowed is "
            f"{max_bytes / 1_048_576:.0f} MB."
        )
    return contents


def _looks_like_plain_text(contents: bytes) -> bool:
    """Heuristic for plain text: must decode as UTF-8 and contain no NUL bytes or
    other binary control characters. Used as a fallback since text has no magic
    bytes signature to match against."""
    if not contents:
        return False
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        return False
    allowed_control = {"\t", "\n", "\r"}
    return not any(ord(ch) < 32 and ch not in allowed_control for ch in decoded)


def validate_content_type(contents: bytes, filename: str | None, category: str) -> str:
    """Inspect the real file signature (magic bytes) and confirm it matches the
    expected category, ignoring whatever the client claimed via filename/content_type."""
    if not contents:
        raise UnsupportedFileTypeError(f"File '{filename}' is empty.")

    try:
        matches = puremagic.magic_string(contents)
        detected_mime = matches[0].mime_type if matches else None
    except ValueError:
        detected_mime = None

    if detected_mime is None and category == "document" and _looks_like_plain_text(contents):
        detected_mime = "text/plain"

    allowed = ALLOWED_MIME_TYPES[category]
    if detected_mime not in allowed:
        raise UnsupportedFileTypeError(
            f"File '{filename}' was detected as '{detected_mime or 'unknown'}', which is not "
            f"an accepted {category} type. Accepted types: {', '.join(sorted(allowed))}."
        )
    return detected_mime


def safe_temp_filename(detected_mime: str) -> str:
    """Generate a collision-safe filename derived from the validated content type,
    never from client-supplied input (avoids path traversal / injection via filename)."""
    extension = EXTENSION_BY_MIME.get(detected_mime, "")
    return f"{uuid.uuid4().hex}{extension}"
