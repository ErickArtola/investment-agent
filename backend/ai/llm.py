"""Ollama LLM client — singleton for use across all AI modules."""
from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL

# Shared LLM instance (phi3:mini via Ollama)
llm = Ollama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    num_predict=2048,
)

# Fast local embeddings using sentence-transformers (no Ollama, no chromadb)
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)


def is_ollama_running() -> bool:
    """Check if the Ollama server is reachable."""
    import requests
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
