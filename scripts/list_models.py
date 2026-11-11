"""List Gemini models available to this API key and save them to scripts/models.json."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

rows = []
for m in client.models.list():
    rows.append({
        "name": m.name,
        "display_name": getattr(m, "display_name", None),
        "actions": list(getattr(m, "supported_actions", None) or []),
        "input_token_limit": getattr(m, "input_token_limit", None),
    })

out = Path(__file__).parent / "models.json"
out.write_text(json.dumps(rows, indent=2))
for r in rows:
    print(r["name"], r["actions"])
print(f"\nSaved {len(rows)} models to {out}")
