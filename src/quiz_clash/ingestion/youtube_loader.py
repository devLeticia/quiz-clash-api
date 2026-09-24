import re

from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi

from quiz_clash.core.exceptions import EmptyDocumentError, URLProcessingError

YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})")
LANGUAGE_CODE_PATTERN = re.compile(r"\(([\w-]+)\)")


def is_youtube_url(url: str) -> bool:
    """Check whether a URL points to a YouTube video."""
    return "youtube.com" in url or "youtu.be" in url


def _extract_video_id(url: str) -> str:
    match = YOUTUBE_ID_PATTERN.search(url)
    if not match:
        raise URLProcessingError(f"Could not extract a video ID from the YouTube URL: {url}")
    return match.group(1)


def _extract_language_code(language: str | None) -> str | None:
    """Pull a short code like 'pt-BR' out of a string like 'Portuguese (pt-BR)'."""
    if not language:
        return None
    match = LANGUAGE_CODE_PATTERN.search(language)
    return match.group(1) if match else None


def _pick_transcript(transcripts: list, preferred_codes: list[str]):
    """Pick the best matching transcript: exact code, then language-family match."""
    for code in preferred_codes:
        for t in transcripts:
            if t.language_code == code:
                return t
        for t in transcripts:
            if t.language_code.split("-")[0] == code.split("-")[0]:
                return t
    return transcripts[0]


def load_youtube_transcript(url: str, language: str | None = None) -> list[Document]:
    """Fetch a YouTube video's transcript, preferring the requested language."""
    video_id = _extract_video_id(url)

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = list(ytt_api.list(video_id))
    except Exception as e:
        raise URLProcessingError(f"Could not fetch transcript for this video: {e}") from e

    if not transcript_list:
        raise EmptyDocumentError("No transcript available for this video.")

    requested_code = _extract_language_code(language)
    preferred_codes = [code for code in (requested_code, "en") if code]

    transcript = _pick_transcript(transcript_list, preferred_codes)
    fetched = transcript.fetch()

    text = " ".join(snippet.text for snippet in fetched)

    if not text.strip():
        raise EmptyDocumentError("The video's transcript is empty.")

    return [Document(page_content=text, metadata={"source": url})]
