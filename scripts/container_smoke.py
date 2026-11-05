"""Run actual restrictive API/UI containers and OCR the real scanned PDF."""
import json
import subprocess
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/platform/P01"
BASE.mkdir(parents=True, exist_ok=True)
steps = []
created = []
flags = ["--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m", "--cap-drop", "ALL",
         "--security-opt", "no-new-privileges:true"]


def run(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    steps.append(dict(command=["docker", *args], exit_code=result.returncode,
                      stdout=result.stdout, stderr=result.stderr))
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


try:
    for component, host_port, port in [("api", 8003, 8000), ("ui", 8083, 8080)]:
        name = "rahbar-p01-" + component + "-" + uuid.uuid4().hex[:8]
        run("run", "--rm", "-d", "--name", name, *flags, "-p", f"127.0.0.1:{host_port}:{port}",
            "-e", "RETRIEVER=stub", "-e", "LLM_PROVIDER=stub", f"rahbar-{component}:platform-p01")
        created.append(name)
        url = f"http://127.0.0.1:{host_port}"
        for _ in range(40):
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.25)
        else:
            raise RuntimeError(component + " failed to start")
        if component == "api":
            assert httpx.get(url + "/readyz").status_code == 200
            response = httpx.post(url + "/api/ask", json={"question": "What does the stub document say?"})
            assert response.status_code == 200 and response.json()["citations"]
            assert "reasoning" not in response.json()
        else:
            assert "New conversation" in httpx.get(url).text
        inspect = json.loads(run("inspect", name))[0]
        assert inspect["Config"]["User"] == "10001:10001"
        assert inspect["HostConfig"]["ReadonlyRootfs"]
        assert "ALL" in inspect["HostConfig"]["CapDrop"]
        (BASE / f"{component}-runtime.log").write_text(run("logs", name), encoding="utf-8")
    scan = ROOT / "corpus/raw/faculty-entrepreneurship-and-technical-start-ups-policy.pdf"
    probe = (
        "import json,os,pytesseract; from pipeline.extract import extract; "
        "d=extract('/corpus/scan.pdf','2022-05-30',False); "
        "assert os.getuid()==10001 and len(d.pages)==8 and sum(len(p.text) for p in d.pages)>2000; "
        "print(json.dumps(dict(uid=os.getuid(),pages=len(d.pages),characters=sum(len(p.text) for p in d.pages),"
        "tesseract=str(pytesseract.get_tesseract_version()))))"
    )
    run("run", "--rm", "--network", "none", *flags, "--mount",
        f"type=bind,source={scan},target=/corpus/scan.pdf,readonly",
        "rahbar-indexer:platform-p01", "python", "-c", probe)
    passed = True
finally:
    for name in created:
        run("stop", name)
    (BASE / "container-smoke.json").write_text(
        json.dumps(dict(passed=locals().get("passed", False), steps=steps), indent=2), encoding="utf-8")
print("PASS: non-root read-only API/UI and real 8-page OCR")
