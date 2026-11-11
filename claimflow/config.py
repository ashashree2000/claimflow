"""Central configuration. Values can be overridden with environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / ".cache" / "llm"
CHROMA_DIR = ROOT / "chroma_db"
DB_PATH = Path(os.getenv("CLAIMFLOW_DB", ROOT / "claimflow.db"))

# Chosen from client.models.list() on 2026-11-12 (see scripts/models.json).
TEXT_MODEL = os.getenv("CLAIMFLOW_TEXT_MODEL", "gemini-3.5-flash-lite")
EMBED_MODEL = os.getenv("CLAIMFLOW_EMBED_MODEL", "gemini-embedding-2")

RETRIEVAL_MODE = os.getenv("CLAIMFLOW_RETRIEVAL_MODE", "graph")  # "vector" or "graph"
TOP_K = int(os.getenv("CLAIMFLOW_TOP_K", "5"))
GRAPH_HOPS = int(os.getenv("CLAIMFLOW_GRAPH_HOPS", "1"))

# Free-tier throttling (AI Studio, 2026-11-12: 3.5 Flash-Lite 15 RPM / 250K TPM / 500 RPD;
# Embedding 2 100 RPM / 30K TPM / 1K RPD). 4.5 s between calls stays under 15 RPM.
CALL_DELAY_S = float(os.getenv("CLAIMFLOW_CALL_DELAY_S", "4.5"))
MAX_RETRIES = int(os.getenv("CLAIMFLOW_MAX_RETRIES", "5"))


def api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")
