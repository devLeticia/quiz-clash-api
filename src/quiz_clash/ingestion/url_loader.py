import trafilatura
from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, URLProcessingError


def load_url(url: str) -> list[Document]:
    """Fetch a web page and extract its main readable text content."""
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
