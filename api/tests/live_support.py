"""Explicit live-check server lifecycle; never starts during unit collection."""
import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[2]


@contextlib.contextmanager
def server(port: int, overrides: dict[str,str], label: str):
    env={**os.environ,"RETRIEVER":"chroma","LLM_PROVIDER":"ollama-host","CHROMA_HOST":"127.0.0.1",
         "CHROMA_PORT":"8001","CHROMA_COLLECTION":"rahbar","OLLAMA_URL":"http://127.0.0.1:11434",
         "REDIS_URL":"redis://127.0.0.1:6379/0","RELEVANCE_FLOOR":"0.75",**overrides}
    path=ROOT/f"docs/evidence/app/sprints/{label}-server.txt"
    with path.open("w",encoding="utf-8") as log:
        process=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1",
                                  "--port",str(port)],cwd=ROOT/"api",env=env,stdout=log,stderr=log)
        url=f"http://127.0.0.1:{port}"
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Live API exited; inspect "+str(path))
                try:
                    if httpx.get(url+"/healthz",timeout=1).status_code==200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError("Live API startup timed out")
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
