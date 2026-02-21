from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).parent.parent

# Data paths
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "investment.db"
VECTORDB_PATH = DATA_DIR / "vectordb"
AI_INITIATIVES_ZIP = DATA_DIR / "Companies-AI-Initiatives.zip"

# Ollama
OLLAMA_MODEL = "phi3:mini"
OLLAMA_BASE_URL = "http://localhost:11434"

# ChromaDB
CHROMA_COLLECTION = "AI_Initiatives"

# Scheduler: refresh at 9 AM and 3 PM local time
REFRESH_HOURS = [9, 15]

# News scraping
NEWS_MAX_ARTICLES = 8
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Scoring thresholds
SCORE_STRONG_BUY = 8.5
SCORE_BUY = 7.0
SCORE_HOLD = 5.5
