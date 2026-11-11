"""Embed all policy clauses and SOP sections with Gemini and store them in Chroma (chroma_db/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claimflow.llm import get_client  # noqa: E402
from claimflow.retrieval.vector import build_index  # noqa: E402

if __name__ == "__main__":
    counts = build_index(get_client())
    print("Indexed:", counts)
