"""Create a fresh Calico kind cluster and gate actual Ingress fixture retrieval."""
import argparse
import json
import os
import subprocess
import sys
import time

import httpx
import yaml

from deploy import ROOT, apply, native, render


def e2e(tag, registry, resume=False):
    directory = ROOT / ".venv/e2e"
    directory.mkdir(parents=True, exist_ok=True)
    kubeconfig = directory / "kubeconfig"
    # Child-process environment only; never switch the user's normal kube context.
    os.environ["KUBECONFIG"] = str(kubeconfig)
    context = "kind-rahbar-ci"
    tools = ROOT / ".venv/tools/bin"
    os.environ["PATH"] = str(tools) + os.pathsep + os.environ["PATH"]
    exists = "rahbar-ci" in native(["kind", "get", "clusters"]).splitlines()
    if exists and not resume:
        raise RuntimeError("An existing rahbar-ci cluster must be reviewed; use --resume only for this task's cluster")
    if not exists:
        print(native(["kind", "create", "cluster", "--name", "rahbar-ci", "--kubeconfig", str(kubeconfig),
                  "--config", str(ROOT / "scripts/kind-config.yaml"), "--image",
                  "kindest/node:v1.35.0@sha256:4613778f3cfcd10e615029370f5786704559103cf27bef934597ba562b269661"]), flush=True)
    command = ["kubectl", "--context", context]
    try:
        print(native([*command, "apply", "-f", str(tools / "calico.yaml")]), flush=True)
        print(native([*command, "wait", "--for=condition=Ready", "nodes", "--all", "--timeout=300s"]), flush=True)
        metrics = list(yaml.safe_load_all((tools / "metrics-server.yaml").read_text(encoding="utf-8")))
        for obj in metrics:
            if obj["kind"] == "Deployment":
                # kind uses self-signed kubelet certificates; confined to this ephemeral test cluster.
                obj["spec"]["template"]["spec"]["containers"][0]["args"].append("--kubelet-insecure-tls")
        print(native([*command, "apply", "-f", "-"], stdin=yaml.safe_dump_all(metrics)), flush=True)
        print(native([*command, "apply", "-f", str(tools / "ingress.yaml")]), flush=True)
        print(native([*command, "-n", "ingress-nginx", "rollout", "status", "deployment/ingress-nginx-controller", "--timeout=300s"]), flush=True)
        for part in ["api", "indexer", "ui"]:
            image = (registry.rstrip("/") + "/" if registry else "") + "rahbar-" + part + ":" + tag
            print(native(["kind", "load", "docker-image", "--name", "rahbar-ci", image]), flush=True)
        apply(render("ci", tag, registry), context)
        print(native([*command, "-n", "rahbar", "wait", "--for=condition=ScalingActive", "hpa/api", "--timeout=180s"]), flush=True)
        url = "http://127.0.0.1:18080"
        with httpx.Client(headers={"Host": "rahbar.local"}, timeout=10) as client:
            for _ in range(30):
                try:
                    if client.get(url + "/api/info").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("Ingress smoke did not become ready")
            assert "RAHBAR" in client.get(url).text
        process = subprocess.run([sys.executable, str(ROOT / "eval/run_eval.py"), "--api", url,
            "--host", "rahbar.local", "--golden", str(ROOT / "eval/fixtures/golden.fixture.yaml"),
            "--baseline", str(ROOT / "eval/fixtures/baseline.json"), "--out",
            str(directory / "fixture-results.json"), "--bypass-cache"], cwd=ROOT)
        if process.returncode:
            raise RuntimeError("Actual fixture evaluation gate failed")
        (directory / "acceptance.json").write_text(json.dumps(dict(passed=True, tag=tag, registry=registry,
            retrieval="real Chroma and nomic embeddings", generation="stub", ingress=url), indent=2), encoding="utf-8")
    finally:
        diagnostics = subprocess.run([*command, "-n", "rahbar", "get", "pods,svc,ingress,pvc,hpa", "-o", "wide"],
                                     capture_output=True, text=True, encoding="utf-8")
        (directory / "objects.txt").write_text(diagnostics.stdout + diagnostics.stderr, encoding="utf-8")
        for name in ["deployment/api", "deployment/embedding", "job/indexer"]:
            result = subprocess.run([*command, "-n", "rahbar", "logs", name, "--all-containers", "--tail=150"],
                                    capture_output=True, text=True, encoding="utf-8")
            (directory / (name.replace("/", "-") + ".txt")).write_text(result.stdout + result.stderr, encoding="utf-8")
    # Retain local clusters for review. Hosted workflow runners destroy their ephemeral VM.


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--registry", default="")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    e2e(arguments.tag, arguments.registry, arguments.resume)
