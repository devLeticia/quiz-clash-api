from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, PDFProcessingError


def load_pdf(file_path: str) -> list[Document]:
    """Load a PDF and return its pages as LangChain Documents."""
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
    except Exception as e:
        raise PDFProcessingError(f"Could not read the PDF file: {e}") from e

    if not docs or not any(doc.page_content.strip() for doc in docs):
        raise EmptyDocumentError("No extractable text found in the PDF. It may be a scanned image.")

    return docs
