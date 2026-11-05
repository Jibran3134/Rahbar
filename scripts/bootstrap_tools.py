"""Install checksum-locked tools in the project, never in global system paths."""
import argparse
import hashlib
import io
import json
import os
import platform
import tarfile
import time
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def verified(spec):
    for attempt in range(4):
        try:
            response = httpx.get(spec["url"], follow_redirects=True, timeout=180)
            if response.status_code != 429 and response.status_code < 500:
                response.raise_for_status()
                break
            response.raise_for_status()
        except (httpx.TransportError, httpx.HTTPStatusError) as error:
            transient = (isinstance(error, httpx.TransportError) or
                         error.response.status_code == 429 or error.response.status_code >= 500)
            if not transient or attempt == 3:
                raise
            print("Transient tool download failure; retry", attempt + 1, "of 3", flush=True)
            time.sleep(2 ** (attempt + 1))
    if hashlib.sha256(response.content).hexdigest() != spec["sha256"]:
        raise ValueError("Official download checksum mismatch: " + spec["url"])
    return response.content


def install(names, manifests=False):
    lock = json.loads((ROOT / "scripts/tooling.lock.json").read_text())
    target = ROOT / ".venv/tools/bin"
    target.mkdir(parents=True, exist_ok=True)
    system = "windows" if platform.system() == "Windows" else "linux"
    for name in names:
        filename = name + (".exe" if system == "windows" else "")
        spec = lock[name][system]
        data = verified(spec)
        if spec["url"].endswith(".tar.gz"):
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                member = next(m for m in archive.getmembers() if Path(m.name).name == filename)
                data = archive.extractfile(member).read()
        elif spec["url"].endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                member = next(n for n in archive.namelist() if Path(n).name == filename)
                data = archive.read(member)
        path = target / filename
        path.write_bytes(data)
        path.chmod(0o755)
        print(name, lock[name]["version"], "checksum verified", flush=True)
    if manifests:
        for name, spec in lock["upstream"].items():
            (target / (name + ".yaml")).write_bytes(verified(spec))
    if os.environ.get("GITHUB_PATH"):
        with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as output:
            output.write(str(target) + "\n")
    print("Tool directory:", target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", choices=["kind", "kubeconform", "trivy", "minikube", "actionlint"])
    parser.add_argument("--manifests", action="store_true")
    args = parser.parse_args()
    install(args.names, args.manifests)
