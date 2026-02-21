"""RAG pipeline — uses FAISS vector store (Python 3.14 compatible) + Ollama embeddings."""
import zipfile
import tempfile
import pickle
from pathlib import Path
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from backend.ai.llm import llm, embeddings
from config.settings import AI_INITIATIVES_ZIP, VECTORDB_PATH

FAISS_INDEX_PATH = VECTORDB_PATH / "faiss_index"

_retriever = None


def _build_vectorstore() -> FAISS:
    """Load PDFs from zip, chunk, embed, and save FAISS index to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(AI_INITIATIVES_ZIP, "r") as z:
            z.extractall(tmpdir)

        loader = PyPDFDirectoryLoader(path=tmpdir)
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=10)
        chunks = loader.load_and_split(splitter)

    vectorstore = FAISS.from_documents(chunks, embeddings)
    FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_INDEX_PATH))
    return vectorstore


def _load_vectorstore() -> FAISS:
    """Load existing FAISS index from disk."""
    return FAISS.load_local(
        str(FAISS_INDEX_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def get_retriever():
    """Return a singleton retriever, building the FAISS index if needed."""
    global _retriever
    if _retriever is not None:
        return _retriever

    index_file = FAISS_INDEX_PATH / "index.faiss"
    try:
        if index_file.exists():
            vectorstore = _load_vectorstore()
        else:
            vectorstore = _build_vectorstore()
    except Exception:
        vectorstore = _build_vectorstore()

    _retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 8})
    return _retriever


def rag_query(user_message: str) -> str:
    """
    Retrieve relevant document chunks and generate a grounded response via Ollama.
    """
    retriever = get_retriever()
    try:
        docs = retriever.invoke(user_message)
    except Exception:
        return "RAG retriever unavailable."

    context = ". ".join([d.page_content for d in docs])

    prompt = f"""You are an AI financial research assistant for DualLens Analytics.
Use ONLY the provided context to answer the question. If the context does not contain
the answer, say 'Not enough information in the knowledge base.'

Context:
{context}

Question:
{user_message}

Answer:"""

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"LLM error: {e}"
