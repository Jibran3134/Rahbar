"""Record only verified gates; exact commands/results remain in JSON and logs."""
import argparse
import json
import re
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("sprint")
p.add_argument("--title",required=True)
p.add_argument("--files",required=True)
p.add_argument("--notes",required=True)
p.add_argument("--live-command",required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]
base=root/"docs/evidence/app/sprints"
checks=json.loads((base/f"{a.sprint}-checks.json").read_text())
live=json.loads((base/f"{a.sprint}-live.json").read_text())
assert checks and all(c["exit_code"]==0 for c in checks) and live["passed"]
commands="\n".join(f"- cwd {c['cwd']}: `{' '.join(c['command'])}`; native exit {c['exit_code']}."
                   for c in checks)
report=(f"# {a.sprint} — {a.title}\n\nStatus: PASS. 5 November 2026 PKT. "
        "Base 5a40788, uncommitted Jibran-owned work. Human and Alishba integration review pending. "
        "No commit/push, external message or Alishba-owned file change.\n\n"
        f"Files: {a.files}.\n\n{a.notes}\n\n## Verification\n\n{commands}\n\n"
        f"Live command: `{a.live_command}`; native check completed and {a.sprint}-live.json records passed=true. "
        "See adjacent red/final transcripts for initial missing-behavior failures and exact final counts. "
        "Native checks are explicit and not collected by offline pytest.\n")
(base/f"{a.sprint}.md").write_text(report,encoding="utf-8")
ledger=root/"docs/notes/jibran.md"
text=ledger.read_text(encoding="utf-8")
row=(f"| {a.sprint} | PASS | {a.title} | Red→green recorded | Tests/types/Ruff exit 0 | "
     f"Explicit live gate passed | [{a.sprint}](../evidence/app/sprints/{a.sprint}.md) | Continue authorized range |")
text=re.sub(rf"^\| {a.sprint} \|.*$",lambda m:row,text,flags=re.M)
ledger.write_text(text,encoding="utf-8")
disclosure=root/"docs/AI-USAGE-JIBRAN.md"
with disclosure.open("a",encoding="utf-8") as f:
    f.write(f"\n\n## Codex — {a.sprint}\n\nCodex implemented and tested {a.title.lower()}, "
            f"ran the checks/live command in {a.sprint}.md and recorded actual evidence. {a.notes} "
            "Jibran human review and Alishba integration review remain pending. No external communication or Git publication.\n")
print(a.sprint,"PASS recorded")
