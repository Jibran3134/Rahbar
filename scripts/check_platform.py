"""Check security invariants and exact source/config snapshot agreement."""
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
snapshot = yaml.safe_load((ROOT / "k8s/base/snapshot-config.yaml").read_text(encoding="utf-8"))["data"]
for key, path in {"fetch_snapshot.py": "scripts/fetch_snapshot.py", "sources.yaml": "corpus/sources.yaml",
                  "MANIFEST.md": "corpus/MANIFEST.md"}.items():
    assert snapshot[key] == (ROOT / path).read_text(encoding="utf-8"), f"Snapshot drift: {key}"
fixture = yaml.safe_load((ROOT / "k8s/overlays/ci/fixtures.yaml").read_text(encoding="utf-8"))["data"]
for key, value in fixture.items():
    assert value == (ROOT / "eval/fixtures" / key).read_text(encoding="utf-8"), f"Fixture drift: {key}"
for overlay in ["dev", "prod", "ci"]:
    result = subprocess.run(["kubectl", "kustomize", str(ROOT / "k8s/overlays" / overlay)],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    documents = list(yaml.safe_load_all(result.stdout))
    assert len(documents) >= 31
    for obj in documents:
        if obj["kind"] == "Namespace":
            continue
        assert obj["metadata"]["namespace"] == "rahbar"
        if obj["kind"] == "Secret":
            raise AssertionError("Real Secret must never be applied by Kustomize")
        if obj["kind"] not in {"Deployment", "StatefulSet", "Job", "CronJob"}:
            continue
        spec = obj["spec"]
        if obj["kind"] == "CronJob":
            spec = spec["jobTemplate"]["spec"]
        pod = spec["template"]["spec"]
        assert pod["automountServiceAccountToken"] is False and pod["serviceAccountName"]
        assert pod["securityContext"]["runAsNonRoot"] is True
        for container in pod["containers"] + pod.get("initContainers", []):
            security = container["securityContext"]
            assert security["readOnlyRootFilesystem"] is True
            assert security["allowPrivilegeEscalation"] is False
            assert security["capabilities"]["drop"] == ["ALL"]
            for bound in ["requests", "limits"]:
                assert all(container["resources"][bound][key] for key in ["cpu", "memory"])
    print(json.dumps(dict(overlay=overlay, resources=len(documents), security="PASS", drift="none")))
