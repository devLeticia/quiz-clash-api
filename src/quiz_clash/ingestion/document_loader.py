from langchain_core.documents import Document

from quiz_clash.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError
from quiz_clash.ingestion.docx_loader import load_docx
from quiz_clash.ingestion.pdf_loader import load_pdf
from quiz_clash.ingestion.pptx_loader import load_pptx

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _load_txt(file_bytes: bytes, source_name: str) -> list[Document]:
    text = file_bytes.decode("utf-8", errors="ignore").strip()

    if not text:
        raise EmptyDocumentError("The text file is empty.")

    return [Document(page_content=text, metadata={"source": source_name})]


def load_document(
    file_bytes: bytes,
    filename: str,
    detected_mime: str,
    tmp_path_for_pdf: str | None = None,
) -> list[Document]:
    """Route to the right parser based on the content type already validated
    from the file's real bytes (never the client-supplied filename)."""
    if detected_mime == DOCX_MIME:
        return load_docx(file_bytes, source_name=filename)
    if detected_mime == PPTX_MIME:
        return load_pptx(file_bytes, source_name=filename)
    if detected_mime == "text/plain":
        return _load_txt(file_bytes, source_name=filename)
    if detected_mime == "application/pdf":
        if tmp_path_for_pdf is None:
            raise UnsupportedFileTypeError("PDF loading requires a temporary file path.")
        return load_pdf(tmp_path_for_pdf)

    raise UnsupportedFileTypeError(f"Unsupported document type: '{detected_mime}'.")
