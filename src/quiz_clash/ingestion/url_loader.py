import httpx
import trafilatura
from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, URLProcessingError
from quiz_clash.core.ssrf_guard import assert_url_is_safe
from quiz_clash.ingestion.youtube_loader import is_youtube_url, load_youtube_transcript

MAX_REDIRECTS = 5

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_safely(url: str) -> str:
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        assert_url_is_safe(current_url)
        try:
            response = httpx.get(
                current_url, follow_redirects=False, timeout=10.0, headers=REQUEST_HEADERS
            )
        except httpx.HTTPError as e:
            raise URLProcessingError(f"Could not fetch the URL: {e}") from e

        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise URLProcessingError("Redirect response missing Location header.")
            current_url = str(httpx.URL(current_url).join(location))
            continue

        return response.text

    raise URLProcessingError("Too many redirects.")


def load_url(url: str, language: str | None = None) -> list[Document]:
    """Fetch a web page (or YouTube video transcript) and extract its text content."""
    if is_youtube_url(url):
        return load_youtube_transcript(url, language=language)

    assert_url_is_safe(url)
    html = _fetch_safely(url)
    text = trafilatura.extract(html)

    if not text or not text.strip():
        raise EmptyDocumentError("No extractable text found on the page.")

    return [Document(page_content=text, metadata={"source": url})]
