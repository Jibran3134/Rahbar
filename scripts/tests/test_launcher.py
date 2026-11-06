"""Exercise the localhost gateway against an actual HTTP backend, without Kubernetes."""
import importlib.util
import json
from pathlib import Path
import threading
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

spec = importlib.util.spec_from_file_location('run_app', Path(__file__).parents[1] / 'run_app.py')
assert spec and spec.loader
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def gateway():
    seen = []

    class Backend(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append((self.path, self.headers['Host'], self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('X-Cache', 'BYPASS')
            self.send_header('X-Request-ID', 'request-123')
            self.end_headers()
            self.wfile.write(b'{"answer":"not ready"}')

        def log_message(self, *_):
            pass

    backend = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
    proxy = ThreadingHTTPServer(('127.0.0.1', 0), launcher.proxy_handler(backend.server_port))
    threads = []
    for server in [backend, proxy]:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        threads.append(thread)
    try:
        yield f'http://127.0.0.1:{proxy.server_port}', seen
    finally:
        for server, thread in zip([backend, proxy], threads):
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def test_real_ingress_host_body_and_error_headers_are_preserved(gateway):
    url, seen = gateway
    body = json.dumps({'question': 'What is the fee?', 'session_id': 'abc'}).encode()
    response = httpx.post(url + '/api/ask?test=1', content=body, headers={'Content-Type': 'application/json'}, trust_env=False)
    assert seen == [('/api/ask?test=1', 'rahbar.local', body)]
    assert response.status_code == 503
    assert response.json() == {'answer': 'not ready'}
    assert response.headers['X-Cache'] == 'BYPASS'
    assert response.headers['X-Request-ID'] == 'request-123'


def test_oversized_requests_do_not_reach_ingress(gateway):
    url, seen = gateway
    response = httpx.post(url + '/api/ask', content=b'x' * 65537, trust_env=False)
    assert response.status_code == 413
    assert seen == []


def test_occupied_browser_port_does_not_modify_services(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler)
    monkeypatch.setattr(launcher, 'services', lambda: pytest.fail('Do not touch services on port conflict'))
    try:
        with pytest.raises(OSError):
            launcher.launch(port=server.server_port, check_only=True)
    finally:
        server.server_close()


def test_failed_child_command_shows_diagnostics_and_stops(capsys):
    with pytest.raises(subprocess.CalledProcessError) as error:
        launcher.command([sys.executable, '-c', "import sys; print('child failed'); sys.exit(7)"])
    assert error.value.returncode == 7
    assert 'child failed' in capsys.readouterr().out
