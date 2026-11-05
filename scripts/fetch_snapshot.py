"""Provision public corpus bytes from the committed manifest without rewriting truth."""
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path

import httpx
import yaml


def provision(sources: Path, manifest: Path, destination: Path) -> None:
    expected = {}
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        columns = [part.strip().strip("`<>") for part in line.split("|")[1:-1]]
        if len(columns) == 7 and len(columns[5]) == 64:
            name, _, _, filename, size, digest, url = columns
            if Path(filename).name != filename or filename.startswith("."):
                raise ValueError("Unsafe corpus filename")
            expected[name] = dict(file=filename, bytes=int(size.replace(",", "")), sha256=digest, url=url)
    documents = yaml.safe_load(sources.read_text(encoding="utf-8-sig"))["documents"]
    if len(expected) != len(documents) or not documents:
        raise ValueError("Manifest and sources must describe the same nonempty snapshot")
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    with httpx.Client(follow_redirects=True, timeout=90,
                      headers={"User-Agent": "RAHBAR-snapshot-fetcher/1.0 (public coursework)"}) as client:
        for doc in documents:
            row = expected[doc["name"]]
            path = destination / row["file"]
            data = path.read_bytes() if path.exists() else b""
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                response = client.get(row["url"])
                response.raise_for_status()
                data = response.content
                if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError(f"Source changed: {row['file']}; review the snapshot, never refresh truth automatically")
                temporary = destination / (row["file"] + "." + uuid.uuid4().hex + ".partial")
                temporary.write_bytes(data)
                temporary.replace(path)
                time.sleep(2)
            entries.append({**row, "name": doc["name"], "doc_version": str(doc["doc_version"]),
                            "superseded": bool(doc.get("superseded", False))})
            print(json.dumps(dict(event="snapshot_verified", file=row["file"], sha256=row["sha256"])), flush=True)
    temporary = destination / ("_index." + uuid.uuid4().hex + ".partial")
    temporary.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    temporary.replace(destination / "_index.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    provision(args.sources, args.manifest, args.out)
