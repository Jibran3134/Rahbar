"""Render and apply Rahbar overlays without changing source files or kube context."""
import argparse
import ipaddress
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def native(command, *, stdin=None):
    result = subprocess.run(command, input=stdin, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{command[0]} exited {result.returncode}: {result.stderr}")
    return result.stdout


def render(overlay, tag, registry, ollama_url=None, host_cidr=None):
    path = ROOT / ".venv/platform" / overlay
    path.mkdir(parents=True, exist_ok=True)
    images = []
    for part in ["api", "indexer", "ui"]:
        names = ["rahbar-" + part, "docker.io/jibran3134/rahbar-" + part]
        images.extend(dict(name=name, newName=(registry.rstrip("/") + "/" if registry else "") + "rahbar-" + part,
                           newTag=tag) for name in names)
    config = dict(apiVersion="kustomize.config.k8s.io/v1beta1", kind="Kustomization",
                  resources=["../../../k8s/overlays/" + overlay], images=images)
    patches = []
    if ollama_url:
        patches.append(dict(target=dict(kind="ConfigMap", name="rahbar-config"), patch=json.dumps([
            dict(op="replace", path="/data/OLLAMA_URL", value=ollama_url)])))
    if host_cidr:
        network = str(ipaddress.ip_network(host_cidr))
        if ipaddress.ip_network(network).prefixlen != 32:
            raise ValueError("Host-model egress must specify one IPv4 /32")
        for name in ["api", "indexer"]:
            patches.append(dict(target=dict(kind="NetworkPolicy", name="allow-" + name + "-egress"),
                                patch=json.dumps([dict(op="replace", path="/spec/egress/1/to/0/ipBlock/cidr", value=network)])))
    if patches:
        config["patches"] = patches
    (path / "kustomization.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    text = native(["kubectl", "kustomize", str(path)])
    (path / "rendered.yaml").write_text(text, encoding="utf-8")
    return list(yaml.safe_load_all(text))


def apply(documents, context):
    command = ["kubectl", "--context", context]
    def kubectl(*args, data=None):
        output = native([*command, *args], stdin=data)
        print(output, end="", flush=True)
        return output
    namespace = [d for d in documents if d["kind"] == "Namespace"]
    jobs = [d for d in documents if d["kind"] == "Job"]
    foundation = [d for d in documents if d["kind"] not in {"Namespace", "Job"}]
    kubectl("apply", "-f", "-", data=yaml.safe_dump_all(namespace))
    kubectl("apply", "-f", "-", data=yaml.safe_dump_all(foundation))
    for name in ["statefulset/chroma", "deployment/redis"]:
        kubectl("-n", "rahbar", "rollout", "status", name, "--timeout=300s")
    if any(d["kind"] == "Deployment" and d["metadata"]["name"] == "embedding" for d in foundation):
        kubectl("-n", "rahbar", "rollout", "status", "deployment/embedding", "--timeout=600s")
    # Completed Jobs have immutable pod templates. Reindex through the CronJob for later rebuilds.
    existing = native([*command, "-n", "rahbar", "get", "job", "indexer", "--ignore-not-found", "-o", "name"])
    if not existing.strip():
        kubectl("apply", "-f", "-", data=yaml.safe_dump_all(jobs))
    else:
        print("Bootstrap Job already exists; use the reindex CronJob template for a new build.", flush=True)
    kubectl("-n", "rahbar", "wait", "--for=condition=complete", "job/indexer", "--timeout=1800s")
    for name in ["deployment/api", "deployment/ui"]:
        kubectl("-n", "rahbar", "rollout", "status", name, "--timeout=600s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["render", "apply"])
    parser.add_argument("--overlay", choices=["dev", "ci", "prod"], default="dev")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--registry", default="")
    parser.add_argument("--context", default="rahbar")
    parser.add_argument("--ollama-url")
    parser.add_argument("--host-cidr")
    args = parser.parse_args()
    if args.overlay == "prod" and (len(args.tag) != 40 or any(c not in "0123456789abcdef" for c in args.tag)):
        parser.error("Production images require a full lowercase Git commit SHA")
    docs = render(args.overlay, args.tag, args.registry, args.ollama_url, args.host_cidr)
    if args.action == "apply":
        apply(docs, args.context)
    else:
        print(ROOT / ".venv/platform" / args.overlay / "rendered.yaml")
