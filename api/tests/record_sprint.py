"""Record only verified gates; exact commands/results remain in JSON and logs."""
import argparse
import json
import re
import subprocess
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
revision=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
report=(f"# {a.sprint} — {a.title}\n\nStatus: PASS. 5 November 2026 PKT. "
        f"Working tree parent {revision}; Jibran-owned work. Human/platform integration review pending. "
        "Local main commits are authorized; no push, external message or Alishba-owned file change.\n\n"
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
            "Jibran human review and platform integration remain pending. Local main commits are authorized; no push or external communication.\n")
print(a.sprint,"PASS recorded")
