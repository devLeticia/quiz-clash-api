import trafilatura
from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, URLProcessingError
from quiz_clash.ingestion.youtube_loader import is_youtube_url, load_youtube_transcript


def load_url(url: str, language: str | None = None) -> list[Document]:
    """Fetch a web page (or YouTube video transcript) and extract its text content."""
    if is_youtube_url(url):
        return load_youtube_transcript(url, language=language)

    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception as e:
        raise URLProcessingError(f"Could not fetch the URL: {e}") from e

    if downloaded is None:
        raise URLProcessingError(f"Could not fetch the URL: {url}")

    text = trafilatura.extract(downloaded)

    if not text or not text.strip():
        raise EmptyDocumentError("No extractable text found on the page.")

    return [Document(page_content=text, metadata={"source": url})]
