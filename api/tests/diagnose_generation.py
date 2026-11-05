"""Explicit source-public diagnosis; no reasoning saved or production log changes."""
import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"api"))
from app.config import Settings  # noqa: E402
from app.providers.llm.ollama import OllamaProvider  # noqa: E402
from app.services.grounding import validate_grounding  # noqa: E402
from app.schemas import Passage  # noqa: E402
rows=json.loads((root/"docs/evidence/app/sprints/S18-real-results.json").read_text(encoding='utf-8'))["rows"]
chunks={c["id"]:c for c in (json.loads(line) for line in (root/"corpus/raw/_s05-chunks/chunks-400-50.jsonl").read_text(encoding='utf-8').splitlines())}
results=[]
for row in rows:
    if row["id"] not in {"q03","q11"}:
        continue
    passages=[Passage(text=chunks[r["chunk_id"]]["text"],**r) for r in row["response"]["retrieved"]]
    result=OllamaProvider(Settings(ollama_url="http://127.0.0.1:11434")).generate(row["response"].get("question") or next(
        q["question"] for q in __import__('yaml').safe_load((root/"eval/golden.yaml").read_text(encoding='utf-8'))["questions"] if q["id"]==row["id"]),passages)
    try:
        validate_grounding(result,passages)
        valid=True
    except RuntimeError:
        valid=False
    results.append(dict(id=row["id"],valid=valid,output=result.model_dump(exclude={"reasoning"})))
(root/"docs/evidence/app/sprints/S18-format-diagnosis.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps(results,indent=2))
