import base64

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from quiz_clash.core.exceptions import EmptyDocumentError, ImageProcessingError

vision_llm = ChatOpenAI(model="gpt-4o-mini")


def load_image(
    image_bytes: bytes, content_type: str, source_name: str = "uploaded_image"
) -> list[Document]:
    """Extract text from an image (e.g. a photo of a notebook or book page).

    Args:
        image_bytes: raw image content, read directly from the upload.
        content_type: MIME type of the image (e.g. "image/jpeg", "image/png").
        source_name: label used in the resulting Document's metadata.
    """
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        raise ImageProcessingError(f"Could not encode the image: {e}") from e

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Transcribe all readable text from this image exactly as written. "
                    "This may be handwritten notes or a printed page. "
                    "Return only the transcribed text, with no extra commentary."
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{content_type};base64,{encoded}"},
            },
        ]
    )

    try:
        response = vision_llm.invoke([message])
    except Exception as e:
        raise ImageProcessingError(f"Failed to process image with vision model: {e}") from e

    text = response.content.strip()
    print(f"aqui esta o texto: {text}")

    if not text:
        raise EmptyDocumentError("No readable text found in the image.")

    return [Document(page_content=text, metadata={"source": source_name})]
