from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def build_vector_store(chunks: list[Document]) -> Chroma:
    """Create a Chroma vector store from document chunks."""
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
    )


def select_diverse_chunks(vector_store: Chroma, k: int = 10) -> list:
    """Select a diverse, representative sample of chunks using MMR."""
    return vector_store.max_marginal_relevance_search(
        query="main topics and key information in the document",
        k=k,
        fetch_k=max(k * 4, 20),
        lambda_mult=0.5,
    )
