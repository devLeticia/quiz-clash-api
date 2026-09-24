from pathlib import Path

from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError
from quiz_clash.ingestion.docx_loader import load_docx
from quiz_clash.ingestion.pdf_loader import load_pdf
from quiz_clash.ingestion.pptx_loader import load_pptx

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".pptx"}


def _load_txt(file_bytes: bytes, source_name: str) -> list[Document]:
    text = file_bytes.decode("utf-8", errors="ignore").strip()

    if not text:
        raise EmptyDocumentError("The text file is empty.")

    return [Document(page_content=text, metadata={"source": source_name})]


def load_document(
    file_bytes: bytes, filename: str, tmp_path_for_pdf: str | None = None
) -> list[Document]:
    suffix = Path(filename).suffix.lower()

    if suffix == ".docx":
        return load_docx(file_bytes, source_name=filename)
    if suffix == ".pptx":
        return load_pptx(file_bytes, source_name=filename)
    if suffix == ".txt":
        return _load_txt(file_bytes, source_name=filename)
    if suffix == ".pdf":
        if tmp_path_for_pdf is None:
            raise UnsupportedFileTypeError("PDF loading requires a temporary file path.")
        return load_pdf(tmp_path_for_pdf)

    raise UnsupportedFileTypeError(
        f"Unsupported file type: '{suffix}'. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
    )
