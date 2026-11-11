"""Print one synthetic claim (email + event log) next to its gold label, for human review.

Usage: python data/show_claim.py C07
"""
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent
cid = sys.argv[1].upper()
claim = json.loads((DATA / "claims" / f"{cid}.json").read_text())
label = next(json.loads(x) for x in (DATA / "labels.jsonl").read_text().splitlines() if f'"{cid}"' in x)
e = claim["email"]
print(f"=== {cid} (SYNTHETIC) ===\nFrom: {e['from_name']}  Sent: {e['sent_at']}\nSubject: {e['subject']}\n"
      f"Attachments: {', '.join(e['attachments']) or '-'}\n\n{e['body']}\n\n--- Event log ---")
for ev in claim["events"]:
    print(f"{ev['event_id']:>4}  {ev['timestamp']}  {ev['step']}")
print("\n--- Gold label ---")
print(json.dumps({k: label[k] for k in ("fields", "documents_missing", "coverage", "cross_reference",
                                        "should_refuse", "process_flaws")}, indent=2))
text = "".join(p.read_text() for p in (DATA / "policies").glob("*.md"))
print("\n--- Text of the gold clauses ---")
for c in label["coverage"]["required_clause_ids"]:
    m = re.search(rf"### {re.escape(c)} (.*?)\n(.*?)(?=\n#|\Z)", text, re.S)
    print(f"{c} {m.group(1)}: {m.group(2).strip()}\n")
