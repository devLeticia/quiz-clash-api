import io

from dotenv import load_dotenv
from langchain_core.documents import Document
from openai import OpenAI

from quiz_clash.core.exceptions import AudioProcessingError, EmptyDocumentError

load_dotenv()
client = OpenAI()


def load_audio(audio_bytes: bytes, filename: str) -> list[Document]:
    """Transcribe an audio file (e.g. a recorded lecture or explanation) into text."""
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # the SDK infers the format from the filename's extension

    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    except Exception as e:
        raise AudioProcessingError(f"Could not transcribe audio: {e}") from e

    text = transcription.text.strip()

    if not text:
        raise EmptyDocumentError("The audio transcription is empty.")

    return [Document(page_content=text, metadata={"source": filename})]
